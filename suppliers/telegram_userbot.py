import asyncio
import logging
import re
import httpx
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import (
    USERBOT_API_ID,
    USERBOT_API_HASH,
    USERBOT_SESSION_STRING,
    TARGET_BOT_USERNAME,
    USD_TO_VND_RATE,
    SUPREME_API_KEY,
    SUPREME_BASE_URL,
)
from suppliers.base import BaseSupplier

logger = logging.getLogger(__name__)

class TelegramUserbotSupplier(BaseSupplier):
    """
    Tự động hóa hoàn toàn với Bot Telegram nguồn (@SupremeLeaderShopBot):
    1. Kết nối trực tiếp REST API chính thức của bot nguồn để lấy 100% (30 sản phẩm thực tế).
    2. Tự động quy đổi USD -> VND và cộng 20% lợi nhuận làm tròn tới nghìn đồng.
    3. Tự động gọi API mua hàng và bàn giao tài khoản ngay khi có khách thanh toán.
    4. Tích hợp sẵn cơ chế dự phòng qua Telethon Userbot nếu API gián đoạn.
    """

    def __init__(self):
        self.target_bot = TARGET_BOT_USERNAME.lstrip("@")
        self.api_key = SUPREME_API_KEY
        self.base_url = SUPREME_BASE_URL.rstrip("/")
        self.client = None
        if USERBOT_API_ID and USERBOT_API_HASH and USERBOT_SESSION_STRING:
            self.client = TelegramClient(
                StringSession(USERBOT_SESSION_STRING),
                USERBOT_API_ID,
                USERBOT_API_HASH
            )

    async def _ensure_connected(self):
        """Khởi động kết nối Telethon nếu chưa kết nối"""
        if self.client and not self.client.is_connected():
            await self.client.connect()

    @staticmethod
    def _clean_id(text: str) -> str:
        s = re.sub(r'[^a-zA-Z0-9]+', '_', text.strip().lower()).strip('_')
        return f"ub_{s[:32]}"

    @staticmethod
    def _categorize(name: str) -> str:
        n = name.lower()
        if any(k in n for k in ["gmail", "hotmail", "mail", "voice", "telegram", "ip"]):
            return "📧 Tài Khoản & Email"
        elif any(k in n for k in ["gpt", "gemini", "claude", "grok", "cursor", "ai", "token", "muse", "codex"]):
            return "🤖 Trí Tuệ Nhân Tạo (AI)"
        elif any(k in n for k in ["netflix", "youtube", "music", "spotify", "tv", "film"]):
            return "🎬 Giải Trí (Phim & Nhạc)"
        elif any(k in n for k in ["canva", "capcut", "adobe", "duolingo", "design"]):
            return "🎨 Thiết Kế & Học Tập"
        return "✨ Dịch Vụ Khác"

    async def fetch_products(self) -> list[dict]:
        """
        Đồng bộ trực tiếp 100% danh mục sản phẩm từ SupremeLeaderShop.
        Ưu tiên qua REST API chính thức, dự phòng qua Telethon crawler.
        """
        # 1. Thử lấy qua REST API chính thức (cực nhanh, đủ 30 sản phẩm)
        if self.api_key:
            try:
                logger.info(f"Đang đồng bộ sản phẩm từ REST API SupremeLeaderShop ({self.base_url})...")
                async with httpx.AsyncClient(timeout=15.0) as http_client:
                    resp = await http_client.get(
                        f"{self.base_url}/api/telegram-buyer/products",
                        params={"key": self.api_key}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_products = data.get("products", [])
                        if raw_products:
                            products = []
                            for p in raw_products:
                                p_id = p.get("_id")
                                p_name = p.get("product_name", "Unknown")
                                price_usd = float(p.get("walletPricing") or p.get("usdPricing") or 0.0)
                                stock = int(p.get("stats", {}).get("available", 0))
                                in_stock = stock > 0
                                desc = p.get("description", "").strip()

                                cost_price_vnd = int(price_usd * USD_TO_VND_RATE)
                                sell_price_vnd, profit_vnd = self.calculate_price_and_profit(cost_price_vnd)

                                formatted_desc = (
                                    f"📦 Gói: {p_name}\n"
                                    f"• Giá gốc: ${price_usd:.2f} (~{cost_price_vnd:,} VNĐ)\n"
                                    f"• Tồn kho thực tế: {stock} tài khoản sẵn có\n"
                                    f"• Bảo hành: Tự động đổi mới 1-1\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"{desc[:300]}..." if len(desc) > 300 else desc
                                )

                                products.append({
                                    "id": p_id,
                                    "supplier_id": p_id,
                                    "name": p_name,
                                    "category": self._categorize(p_name),
                                    "description": formatted_desc,
                                    "cost_price_vnd": cost_price_vnd,
                                    "sell_price_vnd": sell_price_vnd,
                                    "profit_vnd": profit_vnd,
                                    "in_stock": in_stock,
                                    "stock_count": stock,
                                })

                            logger.info(f"✅ Đã đồng bộ thành công {len(products)} sản phẩm từ API SupremeLeaderShop!")
                            return products
            except Exception as e:
                logger.warning(f"Lỗi khi gọi API SupremeLeaderShop ({e}), chuyển sang cào bằng Userbot...")

        # 2. Dự phòng: Quét qua Telethon Userbot
        return await self._crawl_via_telethon()

    async def _crawl_via_telethon(self) -> list[dict]:
        """Cào sản phẩm trực tiếp từ giao diện chat bot Telegram"""
        try:
            await self._ensure_connected()
        except Exception as e:
            logger.warning(f"Không thể kết nối Userbot ({e}), dùng danh mục dự phòng.")
            return self._fallback_products()

        logger.info(f"Đang cào sản phẩm qua Telethon từ @{self.target_bot}...")
        crawled = []
        try:
            async with self.client.conversation(f"@{self.target_bot}", timeout=30) as conv:
                await conv.send_message("/start")
                await asyncio.sleep(2)

                messages = await self.client.get_messages(f"@{self.target_bot}", limit=3)
                menu_msg = None
                for m in messages:
                    if m.buttons:
                        for row in m.buttons:
                            for b in row:
                                if getattr(b, "data", b"") == b"user_dashboard_shop":
                                    menu_msg = m
                                    break

                if not menu_msg:
                    return self._fallback_products()

                await menu_msg.click(data=b"user_dashboard_shop")
                await asyncio.sleep(2)

                visited_pages = set()
                curr_page = 0
                while curr_page not in visited_pages:
                    visited_pages.add(curr_page)
                    shop_msgs = await self.client.get_messages(f"@{self.target_bot}", limit=1)
                    if not shop_msgs:
                        break
                    sm = shop_msgs[0]
                    next_btn = None

                    if sm.buttons:
                        for row in sm.buttons:
                            for btn in row:
                                text = btn.text.strip()
                                data = getattr(btn, "data", b"")
                                data_str = data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else str(data)

                                if data.startswith(b"shop_page_") and "next" in text.lower():
                                    next_btn = data

                                match = re.search(r"^(.*?)\s*-\s*\$([0-9.]+)\s*\|\s*(.*)$", text)
                                if match:
                                    raw_name = match.group(1).strip()
                                    price_usd = float(match.group(2))
                                    stock_str = match.group(3).strip()

                                    cost_price_vnd = int(price_usd * USD_TO_VND_RATE)
                                    sell_price_vnd, profit_vnd = self.calculate_price_and_profit(cost_price_vnd)
                                    in_stock = ("📦" in stock_str) and ("notify" not in stock_str.lower())

                                    crawled.append({
                                        "id": self._clean_id(raw_name),
                                        "supplier_id": data_str,
                                        "name": raw_name,
                                        "category": self._categorize(raw_name),
                                        "description": f"Gói dịch vụ chính hãng từ bot nguồn @{self.target_bot}. Trạng thái: {stock_str}.",
                                        "cost_price_vnd": cost_price_vnd,
                                        "sell_price_vnd": sell_price_vnd,
                                        "profit_vnd": profit_vnd,
                                        "in_stock": in_stock,
                                    })

                    if next_btn:
                        await sm.click(data=next_btn)
                        await asyncio.sleep(2)
                        curr_page += 1
                    else:
                        break

            if crawled:
                return crawled
        except Exception as e:
            logger.error(f"Lỗi cào qua Telethon: {e}")

        return self._fallback_products()

    def _fallback_products(self) -> list[dict]:
        """Danh mục dự phòng"""
        catalog = [
            {"id": "local_p1", "name": "ChatGPT Plus", "category": "🤖 Trí Tuệ Nhân Tạo (AI)", "cost_price_vnd": 178000},
            {"id": "mapped_b5c0f53b65616f69dc620cce", "name": "Gemini AI Pro 3M", "category": "🤖 Trí Tuệ Nhân Tạo (AI)", "cost_price_vnd": 23000},
            {"id": "mapped_f6124ef88f79557c60e9533c", "name": "Netflix 4K Premium 1 month", "category": "🎬 Giải Trí (Phim & Nhạc)", "cost_price_vnd": 127000},
            {"id": "mapped_a1fb4f8b6836d91092c4d711", "name": "CapCut Pro 1 month", "category": "🎨 Thiết Kế & Học Tập", "cost_price_vnd": 52000},
            {"id": "mapped_fef6d11a52c9d4ff89204e13", "name": "Canva Pro 1 Year", "category": "🎨 Thiết Kế & Học Tập", "cost_price_vnd": 153000},
        ]
        res = []
        for item in catalog:
            sell_price, profit = self.calculate_price_and_profit(item["cost_price_vnd"])
            res.append({
                "id": item["id"],
                "supplier_id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "description": f"Gói dịch vụ {item['name']} tự động từ bot nguồn @{self.target_bot}.",
                "cost_price_vnd": item["cost_price_vnd"],
                "sell_price_vnd": sell_price,
                "profit_vnd": profit,
                "in_stock": True,
            })
        return res

    async def buy_product(self, product_id: str, custom_data: dict = None) -> dict:
        """
        Quy trình mua hàng tự động:
        1. Gọi REST API chính thức của bot nguồn để mua hàng ngay lập tức.
        2. Nếu API báo thiếu số dư ví (402), thông báo rõ ràng cho Admin.
        3. Nếu API gặp sự cố, tự động dùng Userbot Telethon bấm nút mua.
        """
        # 1. Thử mua qua REST API
        if self.api_key:
            qty = int((custom_data or {}).get("quantity", 1))
            try:
                logger.info(f"Đang gửi yêu cầu mua sản phẩm '{product_id}' (Số lượng: {qty}) qua REST API...")
                async with httpx.AsyncClient(timeout=25.0) as http_client:
                    resp = await http_client.post(
                        f"{self.base_url}/api/telegram-buyer/purchase",
                        json={
                            "key": self.api_key,
                            "product_id": product_id,
                            "quantity": qty,
                            "lang": "en"
                        }
                    )
                    res_json = resp.json() if resp.status_code in [200, 400, 402] else {}

                    if resp.status_code == 200 and res_json.get("success"):
                        delivered = res_json.get("data") or res_json.get("delivered_data") or res_json.get("message") or str(res_json)
                        if isinstance(delivered, list):
                            delivered = "\n\n".join(str(item) for item in delivered)
                        return {
                            "success": True,
                            "delivered_data": (
                                f"✅ **TÀI KHOẢN TỰ ĐỘNG (NGUỒN @{self.target_bot})**\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"{delivered}\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"📌 Vui lòng kiểm tra và đổi mật khẩu sau khi nhận."
                            ),
                            "cost_price_vnd": 0,
                            "error": None
                        }
                    elif resp.status_code == 402 or res_json.get("error") == "insufficient_balance":
                        return {
                            "success": False,
                            "delivered_data": "",
                            "cost_price_vnd": 0,
                            "error": f"⚠️ Ví của bạn trên @{self.target_bot} không đủ số dư USDT để mua {qty} tài khoản. Vui lòng nạp thêm tiền vào bot nguồn!"
                        }
                    else:
                        err_msg = res_json.get("error") or resp.text
                        logger.warning(f"API purchase trả về lỗi: {err_msg}, chuyển sang Telethon...")
            except Exception as e:
                logger.warning(f"Lỗi khi mua qua API ({e}), chuyển sang Telethon...")

        # 2. Dự phòng mua qua Telethon Userbot
        return await self._buy_via_telethon(product_id)

    async def _buy_via_telethon(self, product_id: str) -> dict:
        """Dự phòng: Mua bằng cách click nút qua Telethon"""
        try:
            await self._ensure_connected()
        except Exception as e:
            return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": f"Lỗi Userbot: {str(e)}"}

        try:
            async with self.client.conversation(f"@{self.target_bot}", timeout=35) as conv:
                await conv.send_message("/start")
                await asyncio.sleep(2)

                messages = await self.client.get_messages(f"@{self.target_bot}", limit=3)
                menu_msg = None
                for m in messages:
                    if m.buttons:
                        for row in m.buttons:
                            for b in row:
                                if getattr(b, "data", b"") == b"user_dashboard_shop":
                                    menu_msg = m
                                    break
                if not menu_msg:
                    return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": "Không tìm thấy nút Shop."}

                await menu_msg.click(data=b"user_dashboard_shop")
                await asyncio.sleep(2)

                target_btn = None
                target_msg = None
                for page_idx in range(4):
                    shop_msgs = await self.client.get_messages(f"@{self.target_bot}", limit=1)
                    if not shop_msgs or not shop_msgs[0].buttons:
                        break
                    sm = shop_msgs[0]
                    next_btn = None

                    for row in sm.buttons:
                        for btn in row:
                            b_data = getattr(btn, "data", b"")
                            b_data_str = b_data.decode("utf-8", errors="ignore") if isinstance(b_data, bytes) else str(b_data)
                            if b_data_str == product_id or product_id in b_data_str:
                                target_btn = b_data
                                target_msg = sm
                                break
                            if b_data.startswith(b"shop_page_") and "next" in btn.text.lower():
                                next_btn = b_data
                        if target_btn:
                            break
                    if target_btn:
                        break
                    if next_btn:
                        await sm.click(data=next_btn)
                        await asyncio.sleep(2)
                    else:
                        break

                if not target_btn:
                    return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": f"Không tìm thấy nút mua cho sản phẩm {product_id}."}

                await target_msg.click(data=target_btn)
                await asyncio.sleep(2)

                detail_msgs = await self.client.get_messages(f"@{self.target_bot}", limit=1)
                if not detail_msgs or not detail_msgs[0].buttons:
                    return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": "Không mở được chi tiết sản phẩm."}

                dm = detail_msgs[0]
                buy_action_btn = None
                for row in dm.buttons:
                    for b in row:
                        b_text = b.text.lower()
                        b_data = getattr(b, "data", b"")
                        if "buy 1x" in b_text or "buy now" in b_text or b_data.startswith(b"buy_qty_") or b_data.startswith(b"api_shop_buy_"):
                            buy_action_btn = b_data
                            break
                    if buy_action_btn:
                        break

                if not buy_action_btn:
                    return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": "Không tìm thấy nút Mua."}

                await dm.click(data=buy_action_btn)
                await asyncio.sleep(2.5)

                result_msgs = await self.client.get_messages(f"@{self.target_bot}", limit=2)
                latest_text = "\n".join(rm.text for rm in reversed(result_msgs) if rm.text)

                if any(w in latest_text.lower() for w in ["not enough", "insufficient", "balance"]):
                    return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": f"⚠️ Ví của bạn trên @{self.target_bot} đang có số dư 0.00 USDT. Vui lòng nạp tiền vào bot nguồn!"}

                return {
                    "success": True,
                    "delivered_data": f"✅ **TÀI KHOẢN TỰ ĐỘNG (NGUỒN @{self.target_bot})**\n━━━━━━━━━━━━━━━━━━\n{latest_text}\n━━━━━━━━━━━━━━━━━━",
                    "cost_price_vnd": 0,
                    "error": None
                }
        except Exception as e:
            return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": f"Lỗi Userbot: {str(e)}"}

    async def get_balance(self) -> dict:
        """
        Kiểm tra số dư ví USDT hiện tại trên SupremeLeaderShop thông qua REST API.
        """
        if self.api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    resp = await http_client.get(
                        f"{self.base_url}/api/telegram-buyer/balance",
                        params={"key": self.api_key}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        balance = float(data.get("balance", 0.0))
                        currency = data.get("walletCurrency", "USDT")
                        text = data.get("balanceText") or f"{balance:.2f} {currency}"
                        return {
                            "success": True,
                            "balance": balance,
                            "balanceText": text,
                            "walletCurrency": currency
                        }
            except Exception as e:
                logger.warning(f"Lỗi khi kiểm tra số dư ví SupremeLeader: {e}")

        return {"success": False, "balance": 0.0, "balanceText": "0.00 USDT", "walletCurrency": "USDT"}

