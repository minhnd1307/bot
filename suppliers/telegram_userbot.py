import asyncio
import logging
import re
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import (
    USERBOT_API_ID,
    USERBOT_API_HASH,
    USERBOT_SESSION_STRING,
    TARGET_BOT_USERNAME,
    USD_TO_VND_RATE,
)
from suppliers.base import BaseSupplier

logger = logging.getLogger(__name__)

class TelegramUserbotSupplier(BaseSupplier):
    """
    Tự động hóa hoàn toàn với Bot Telegram nguồn (@SupremeLeaderShopBot):
    1. Tự động đồng bộ (crawl) 100% danh sách sản phẩm, giá USD và tồn kho từ bot nguồn.
    2. Tự động quy đổi USD -> VND và cộng 20% lợi nhuận làm tròn tới nghìn đồng.
    3. Tự động tương tác, bấm nút mua và bóc tách tài khoản giao cho khách.
    """

    def __init__(self):
        self.target_bot = TARGET_BOT_USERNAME.lstrip("@")
        self.client = None
        if USERBOT_API_ID and USERBOT_API_HASH and USERBOT_SESSION_STRING:
            self.client = TelegramClient(
                StringSession(USERBOT_SESSION_STRING),
                USERBOT_API_ID,
                USERBOT_API_HASH
            )

    async def _ensure_connected(self):
        """Khởi động kết nối Telethon nếu chưa kết nối"""
        if not self.client:
            raise ValueError("Chưa cấu hình USERBOT_API_ID, USERBOT_API_HASH hoặc USERBOT_SESSION_STRING trong .env")
        if not self.client.is_connected():
            await self.client.connect()

    @staticmethod
    def _clean_id(text: str) -> str:
        s = re.sub(r'[^a-zA-Z0-9]+', '_', text.strip().lower()).strip('_')
        return f"ub_{s[:32]}"

    @staticmethod
    def _categorize(name: str) -> str:
        n = name.lower()
        if any(k in n for k in ["gmail", "hotmail", "mail", "voice", "telegram", "ip"]):
            return "📧 Tài Khoản & Tiện Ích"
        elif any(k in n for k in ["gpt", "gemini", "claude", "grok", "cursor", "ai", "token", "muse"]):
            return "🤖 Trí Tuệ Nhân Tạo (AI)"
        elif any(k in n for k in ["netflix", "youtube", "music", "spotify", "tv", "film"]):
            return "🎬 Giải Trí (Phim & Nhạc)"
        elif any(k in n for k in ["canva", "capcut", "adobe", "duolingo", "design"]):
            return "🎨 Thiết Kế & Học Tập"
        return "✨ Dịch Vụ Khác"

    async def fetch_products(self) -> list[dict]:
        """
        Đồng bộ trực tiếp danh sách sản phẩm từ @SupremeLeaderShopBot theo thời gian thực.
        """
        try:
            await self._ensure_connected()
        except Exception as e:
            logger.warning(f"Không thể kết nối Userbot ({e}), sử dụng danh mục dự phòng.")
            return self._fallback_products()

        logger.info(f"Đang cào danh sách sản phẩm trực tiếp từ @{self.target_bot}...")
        crawled_products = []

        try:
            async with self.client.conversation(f"@{self.target_bot}", timeout=30) as conv:
                await conv.send_message("/start")
                await asyncio.sleep(2)

                # Tìm nút Shop trong menu chính
                messages = await self.client.get_messages(f"@{self.target_bot}", limit=3)
                menu_msg = None
                for m in messages:
                    if m.buttons:
                        for row in m.buttons:
                            for b in row:
                                if getattr(b, "data", b"") == b"user_dashboard_shop":
                                    menu_msg = m
                                    break
                        if menu_msg:
                            break

                if not menu_msg:
                    logger.warning("Không tìm thấy nút Shop trên bot nguồn, dùng danh mục dự phòng.")
                    return self._fallback_products()

                # Bấm nút Shop
                await menu_msg.click(data=b"user_dashboard_shop")
                await asyncio.sleep(2)

                # Duyệt qua các trang sản phẩm
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

                                # Nút Next phân trang
                                if data.startswith(b"shop_page_") and "next" in text.lower():
                                    next_btn = data

                                # Bóc tách sản phẩm: Name - $Price | Stock
                                # Ví dụ: ChatGPT Plus 1 Month - $7.00 | 📦 5 Pcs
                                match = re.search(r"^(.*?)\s*-\s*\$([0-9.]+)\s*\|\s*(.*)$", text)
                                if match:
                                    raw_name = match.group(1).strip()
                                    price_usd = float(match.group(2))
                                    stock_str = match.group(3).strip()

                                    cost_price_vnd = int(price_usd * USD_TO_VND_RATE)
                                    sell_price_vnd, profit_vnd = self.calculate_price_and_profit(cost_price_vnd)
                                    in_stock = ("📦" in stock_str) and ("notify" not in stock_str.lower())

                                    crawled_products.append({
                                        "id": self._clean_id(raw_name),
                                        "supplier_id": data_str,
                                        "name": raw_name,
                                        "category": self._categorize(raw_name),
                                        "description": (
                                            f"Gói dịch vụ chính hãng từ bot nguồn @{self.target_bot}.\n"
                                            f"• Giá gốc: ${price_usd:.2f} (~{cost_price_vnd:,}đ)\n"
                                            f"• Trạng thái kho: {stock_str}\n"
                                            f"• Giao tự động: 1-3 giây sau khi thanh toán."
                                        ),
                                        "cost_price_vnd": cost_price_vnd,
                                        "sell_price_vnd": sell_price_vnd,
                                        "profit_vnd": profit_vnd,
                                        "in_stock": in_stock,
                                        "callback_data": data_str
                                    })

                    if next_btn:
                        await sm.click(data=next_btn)
                        await asyncio.sleep(2)
                        curr_page += 1
                    else:
                        break

            if crawled_products:
                logger.info(f"Đã cào thành công {len(crawled_products)} sản phẩm thực tế từ @{self.target_bot}!")
                return crawled_products

        except Exception as e:
            logger.error(f"Lỗi trong quá trình cào sản phẩm từ @{self.target_bot}: {e}")

        return self._fallback_products()

    def _fallback_products(self) -> list[dict]:
        """Danh mục dự phòng khi bot nguồn tạm ngưng hoặc mất kết nối"""
        catalog = [
            {
                "id": "ub_chatgpt_plus_1_month",
                "supplier_id": "shop_buy_p1",
                "name": "ChatGPT Plus 1 Month",
                "category": "🤖 Trí Tuệ Nhân Tạo (AI)",
                "description": "Tài khoản ChatGPT Plus 1 tháng tự động mua qua @SupremeLeaderShopBot.",
                "cost_price_vnd": 178000,
            },
            {
                "id": "ub_gemini_ai_pro_3m",
                "supplier_id": "api_shop_view_c772ff7e52465a1c2dbad4a8b1bad0ea",
                "name": "Gemini AI Pro 3M",
                "category": "🤖 Trí Tuệ Nhân Tạo (AI)",
                "description": "Nâng cấp Gemini AI Pro 3 tháng từ bot nguồn @SupremeLeaderShopBot.",
                "cost_price_vnd": 23000,
            },
            {
                "id": "ub_netflix_4k_premium_1_month",
                "supplier_id": "api_shop_view_e2cbbc598510676e9ad755d3da566904",
                "name": "Netflix 4K Premium 1 month",
                "category": "🎬 Giải Trí (Phim & Nhạc)",
                "description": "Gói Netflix Premium 4K từ bot nguồn @SupremeLeaderShopBot.",
                "cost_price_vnd": 127000,
            },
            {
                "id": "ub_capcut_pro_1_month",
                "supplier_id": "api_shop_view_356b0c3398af3787fbc1017f1af6572e",
                "name": "CapCut Pro 1 month",
                "category": "🎨 Thiết Kế & Học Tập",
                "description": "Tài khoản CapCut Pro 1 tháng chính chủ.",
                "cost_price_vnd": 52000,
            },
            {
                "id": "ub_canva_pro_1_year",
                "supplier_id": "api_shop_view_1d2c56e3d4a479df5184f73058d378a3",
                "name": "Canva Pro 1 Year",
                "category": "🎨 Thiết Kế & Học Tập",
                "description": "Tài khoản Canva Pro 1 năm tự động từ bot nguồn.",
                "cost_price_vnd": 153000,
            }
        ]

        products = []
        for item in catalog:
            sell_price, profit = self.calculate_price_and_profit(item["cost_price_vnd"])
            products.append({
                "id": item["id"],
                "supplier_id": item["supplier_id"],
                "name": item["name"],
                "category": item["category"],
                "description": item["description"],
                "cost_price_vnd": item["cost_price_vnd"],
                "sell_price_vnd": sell_price,
                "profit_vnd": profit,
                "in_stock": True,
                "callback_data": item["supplier_id"]
            })
        return products

    async def buy_product(self, product_id: str, custom_data: dict = None) -> dict:
        """
        Quy trình Userbot mua hàng tự động trên @SupremeLeaderShopBot:
        1. Gửi /start tới bot nguồn
        2. Mở Shop (user_dashboard_shop)
        3. Tìm và click nút sản phẩm (khớp callback_data hoặc product_id)
        4. Bấm nút Mua ngay ('Buy 1x' hoặc 'Buy Now')
        5. Xác nhận đơn và bóc tách dữ liệu tài khoản trả về
        """
        try:
            await self._ensure_connected()
        except Exception as e:
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": f"Lỗi khởi động Userbot: {str(e)}"
            }

        logger.info(f"Userbot đang tiến hành mua '{product_id}' từ @{self.target_bot}...")

        try:
            async with self.client.conversation(f"@{self.target_bot}", timeout=35) as conv:
                await conv.send_message("/start")
                await asyncio.sleep(2)

                # 1. Tìm nút Shop
                messages = await self.client.get_messages(f"@{self.target_bot}", limit=3)
                menu_msg = None
                for m in messages:
                    if m.buttons:
                        for row in m.buttons:
                            for b in row:
                                if getattr(b, "data", b"") == b"user_dashboard_shop":
                                    menu_msg = m
                                    break
                        if menu_msg:
                            break

                if not menu_msg:
                    return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": "Không tìm thấy nút Shop trên bot nguồn."}

                await menu_msg.click(data=b"user_dashboard_shop")
                await asyncio.sleep(2)

                # 2. Tìm nút sản phẩm trong các trang của Shop
                target_btn = None
                target_msg = None

                # Duyệt các trang
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
                            b_text = btn.text.lower()

                            # Kiểm tra nếu nút này khớp với product_id hoặc supplier_id
                            clean_name_id = self._clean_id(btn.text.split("-")[0].strip())
                            if b_data_str == product_id or clean_name_id == product_id or product_id in b_data_str:
                                target_btn = b_data
                                target_msg = sm
                                break

                            if b_data.startswith(b"shop_page_") and "next" in b_text:
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
                    return {
                        "success": False,
                        "delivered_data": "",
                        "cost_price_vnd": 0,
                        "error": f"Không tìm thấy nút mua sản phẩm '{product_id}' trên @{self.target_bot}."
                    }

                # 3. Click vào sản phẩm để mở màn hình chi tiết
                await target_msg.click(data=target_btn)
                await asyncio.sleep(2)

                # 4. Tìm nút Mua (Buy 1x / Buy Now)
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
                    return {"success": False, "delivered_data": "", "cost_price_vnd": 0, "error": "Không tìm thấy nút 'Buy 1x' hoặc 'Buy Now'."}

                logger.info(f"Bấm nút mua: {buy_action_btn}")
                await dm.click(data=buy_action_btn)
                await asyncio.sleep(2.5)

                # 5. Kiểm tra kết quả trả về
                result_msgs = await self.client.get_messages(f"@{self.target_bot}", limit=2)
                latest_text = ""
                for rm in reversed(result_msgs):
                    if rm.text:
                        latest_text += rm.text + "\n"

                # Kiểm tra lỗi thiếu số dư trên bot nguồn
                insufficient_keywords = ["not enough", "insufficient", "balance", "top up", "wallet"]
                if any(w in latest_text.lower() for w in insufficient_keywords) and "success" not in latest_text.lower():
                    logger.error(f"Bot nguồn báo lỗi số dư: {latest_text}")
                    return {
                        "success": False,
                        "delivered_data": "",
                        "cost_price_vnd": 0,
                        "error": f"⚠️ Ví Userbot trên @{self.target_bot} không đủ số dư để mua hàng. Vui lòng nạp thêm tiền vào bot nguồn!"
                    }

                # Kiểm tra nút xác nhận mua nếu có
                for rm in result_msgs:
                    if rm.buttons:
                        for row in rm.buttons:
                            for b in row:
                                if any(w in b.text.lower() for w in ["confirm", "xác nhận", "yes"]):
                                    await rm.click(data=getattr(b, "data", None))
                                    await asyncio.sleep(2)
                                    break

                # Lấy tin nhắn bàn giao sản phẩm cuối cùng
                final_msgs = await self.client.get_messages(f"@{self.target_bot}", limit=1)
                final_text = final_msgs[0].text if final_msgs else latest_text

                logger.info(f"Đã nhận nội dung bàn giao từ @{self.target_bot} thành công!")
                return {
                    "success": True,
                    "delivered_data": (
                        f"✅ **TÀI KHOẢN TỰ ĐỘNG (NGUỒN @{self.target_bot})**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"{final_text}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📌 Vui lòng kiểm tra và đổi mật khẩu sau khi nhận."
                    ),
                    "cost_price_vnd": 0,
                    "error": None
                }

        except asyncio.TimeoutError:
            logger.error(f"Quá thời gian chờ phản hồi từ @{self.target_bot}")
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": f"Bot nguồn @{self.target_bot} phản hồi quá chậm."
            }
        except Exception as e:
            logger.error(f"Lỗi khi Userbot mua hàng: {e}")
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": f"Lỗi Userbot: {str(e)}"
            }
