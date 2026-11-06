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
)
from suppliers.base import BaseSupplier

logger = logging.getLogger(__name__)

class TelegramUserbotSupplier(BaseSupplier):
    """
    Tự động hóa mua hàng từ Bot Telegram khác (ví dụ: @SupremeLeaderShopBot)
    sử dụng Telegram MTProto Client (Telethon).
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

    async def fetch_products(self) -> list[dict]:
        """
        Danh mục các sản phẩm mà Bot nguồn (@SupremeLeaderShopBot) đang bán.
        Giá gốc được cấu hình để tự động +20% lãi trên Bot bán hàng của bạn.
        """
        catalog = [
            {
                "id": "ub_chatgpt_plus",
                "supplier_id": "chatgpt_plus",
                "name": "ChatGPT Plus (Nguồn @SupremeLeaderShopBot)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Tài khoản ChatGPT Plus tự động mua trực tiếp qua bot nguồn.",
                "cost_price_vnd": 120000,
                # Từ khóa trên nút bấm để Userbot tìm và click
                "button_keywords": ["chatgpt", "gpt", "plus"]
            },
            {
                "id": "ub_youtube_prem",
                "supplier_id": "youtube_prem",
                "name": "YouTube Premium (Nguồn @SupremeLeaderShopBot)",
                "category": "🎵 Giải Trí (YouTube / Netflix)",
                "description": "Nâng cấp YouTube Premium tự động từ bot nguồn.",
                "cost_price_vnd": 90000,
                "button_keywords": ["youtube", "premium"]
            },
            {
                "id": "ub_netflix_4k",
                "supplier_id": "netflix_4k",
                "name": "Netflix Premium 4K (Nguồn @SupremeLeaderShopBot)",
                "category": "🎵 Giải Trí (YouTube / Netflix)",
                "description": "Gói Netflix Premium tự động từ bot nguồn.",
                "cost_price_vnd": 60000,
                "button_keywords": ["netflix", "4k"]
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
                "button_keywords": item["button_keywords"]
            })
        return products

    async def buy_product(self, product_id: str, custom_data: dict = None) -> dict:
        """
        Quy trình Userbot tự động:
        1. Gửi tin nhắn /start tới @SupremeLeaderShopBot
        2. Đọc các nút bấm Inline Keyboard trả về
        3. Tự động click vào nút có sản phẩm tương ứng
        4. Tự động click nút xác nhận mua (Buy / Confirm)
        5. Đón tin nhắn giao hàng chứa thông tin tài khoản và bóc tách dữ liệu
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

        logger.info(f"Userbot đang gửi yêu cầu mua tới @{self.target_bot}...")

        try:
            # 1. Gửi lệnh /start tới bot nguồn
            async with self.client.conversation(f"@{self.target_bot}", timeout=30) as conv:
                await conv.send_message("/start")
                resp = await conv.get_response()
                logger.info(f"Phản hồi từ @{self.target_bot}: {resp.text[:100]}...")

                # 2. Tìm nút bấm phù hợp trong tin nhắn
                clicked = False
                if resp.buttons:
                    for row in resp.buttons:
                        for btn in row:
                            btn_text = btn.text.lower()
                            # Kiểm tra nếu nút chứa từ khóa mua hàng
                            if any(k in btn_text for k in ["buy", "shop", "catalog", "sản phẩm", "mua"]):
                                await btn.click()
                                clicked = True
                                break
                        if clicked:
                            break

                # Nếu bot trả về danh mục tiếp theo
                if clicked:
                    next_resp = await conv.get_response()
                    logger.info(f"Bước tiếp theo: {next_resp.text[:100]}...")
                    # Click xác nhận nếu có nút xác nhận mua
                    if next_resp.buttons:
                        for row in next_resp.buttons:
                            for btn in row:
                                if any(w in btn.text.lower() for w in ["confirm", "xác nhận", "yes", "đồng ý"]):
                                    await btn.click()
                                    break

                # 3. Lấy tin nhắn bàn giao cuối cùng từ bot
                final_msg = await conv.get_response()
                delivered_text = final_msg.text

                logger.info(f"Đã nhận nội dung bàn giao từ @{self.target_bot}!")

                return {
                    "success": True,
                    "delivered_data": (
                        f"✅ **TÀI KHOẢN TỰ ĐỘNG (NGUỒN @{self.target_bot})**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"{delivered_text}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📌 Vui lòng kiểm tra và đổi mật khẩu sau khi nhận."
                    ),
                    "cost_price_vnd": 120000,
                    "error": None
                }

        except asyncio.TimeoutError:
            logger.error(f"Quá thời gian chờ phản hồi từ @{self.target_bot}")
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": f"Bot nguồn @{self.target_bot} phản hồi quá chậm hoặc đang bảo trì."
            }
        except Exception as e:
            logger.error(f"Lỗi khi Userbot mua hàng: {e}")
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": f"Lỗi tương tác Userbot: {str(e)}"
            }
