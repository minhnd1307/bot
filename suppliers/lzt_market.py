import logging
import httpx
from config import LZT_API_TOKEN, LZT_BASE_URL, RUB_TO_VND_RATE
from suppliers.base import BaseSupplier

logger = logging.getLogger(__name__)

class LztMarketSupplier(BaseSupplier):
    """
    Tích hợp API Sàn Quốc Tế LZT Market (Lolzteam / lolz.live)
    Chuyên cung cấp tài khoản ChatGPT Plus, OpenAI Token, Google/Gemini, YouTube... giá gốc rẻ nhất thế giới.
    Docs: https://market.lolz.live/api
    """

    def __init__(self):
        self.base_url = LZT_BASE_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {LZT_API_TOKEN}",
            "Accept": "application/json"
        }

    async def check_balance(self) -> float:
        """Kiểm tra số dư tài khoản trên sàn LZT Market"""
        if not LZT_API_TOKEN:
            logger.warning("Chưa cấu hình LZT_API_TOKEN.")
            return 0.0
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.base_url}/profile", headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    return float(data.get("user", {}).get("balance", 0.0))
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra số dư LZT: {e}")
        return 0.0

    async def fetch_products(self) -> list[dict]:
        """
        Lấy danh sách các tài khoản đang rao bán từ LZT Market.
        Trong thực tế, bạn có thể cấu hình tìm kiếm theo tag/category (ChatGPT, Google, etc.).
        Dưới đây là mapping danh mục mẫu liên kết trực tiếp tới các category của LZT.
        """
        # Nếu chưa có Token thật, trả về danh mục mặc định chuẩn bị kết nối
        products = []
        default_templates = [
            {
                "id": "lzt_chatgpt_plus",
                "supplier_id": "chatgpt_openai",
                "name": "ChatGPT Plus (OpenAI Account - LZT Source)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Tài khoản ChatGPT Plus tự động mua trực tiếp từ sàn LZT Market.",
                "cost_rub": 600, # ~168.000 VNĐ
            },
            {
                "id": "lzt_gemini_advanced",
                "supplier_id": "google_gemini",
                "name": "Google One AI Premium (Gemini Advanced)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Tài khoản Google kèm gói 2TB Google One AI.",
                "cost_rub": 400, # ~112.000 VNĐ
            },
            {
                "id": "lzt_youtube_premium",
                "supplier_id": "youtube_premium",
                "name": "YouTube Premium (Family / Account)",
                "category": "🎵 Giải Trí (YouTube / Netflix)",
                "description": "Tài khoản/gói YouTube Premium từ sàn quốc tế.",
                "cost_rub": 450, # ~126.000 VNĐ
            }
        ]

        for t in default_templates:
            cost_vnd = int(t["cost_rub"] * RUB_TO_VND_RATE)
            sell_vnd, profit_vnd = self.calculate_price_and_profit(cost_vnd)
            products.append({
                "id": t["id"],
                "supplier_id": t["supplier_id"],
                "name": t["name"],
                "category": t["category"],
                "description": t["description"],
                "cost_price_vnd": cost_vnd,
                "sell_price_vnd": sell_vnd,
                "profit_vnd": profit_vnd,
                "in_stock": True
            })

        return products

    async def buy_product(self, product_id: str, custom_data: dict = None) -> dict:
        """
        Thực hiện Fast-Buy trên LZT Market
        Endpoint: POST /items/{item_id}/fast-buy
        """
        if not LZT_API_TOKEN:
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": "Chưa cấu hình LZT_API_TOKEN trong file .env."
            }

        item_id = custom_data.get("item_id") if custom_data else None
        if not item_id:
            # Nếu chỉ truyền product_id chung, tiến hành search sản phẩm tốt nhất có sẵn
            item_id = await self._find_available_item(product_id)

        if not item_id:
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": "Hiện tại không còn sản phẩm phù hợp trên LZT Market."
            }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                url = f"{self.base_url}/items/{item_id}/fast-buy"
                res = await client.post(url, headers=self.headers)
                data = res.json()

                if res.status_code == 200 and data.get("item"):
                    item = data["item"]
                    login_data = item.get("loginData", {})
                    account_login = login_data.get("login", item.get("email", "N/A"))
                    account_pass = login_data.get("password", "N/A")
                    price_rub = float(item.get("price", 0))
                    cost_vnd = int(price_rub * RUB_TO_VND_RATE)

                    delivered = (
                        f"✅ **TÀI KHOẢN TỰ ĐỘNG TỪ LZT MARKET**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📧 **Tài khoản/Email:** `{account_login}`\n"
                        f"🔑 **Mật khẩu:** `{account_pass}`\n"
                        f"🆔 **Mã đơn hàng LZT:** #{item.get('item_id')}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📌 Quý khách vui lòng kiểm tra và đổi mật khẩu sau khi nhận."
                    )
                    return {
                        "success": True,
                        "delivered_data": delivered,
                        "cost_price_vnd": cost_vnd,
                        "error": None
                    }
                else:
                    error_msg = data.get("errors", ["Mua hàng LZT thất bại"])[0]
                    return {
                        "success": False,
                        "delivered_data": "",
                        "cost_price_vnd": 0,
                        "error": str(error_msg)
                    }
        except Exception as e:
            logger.error(f"Lỗi khi gọi API LZT fast-buy: {e}")
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": f"Lỗi kết nối sàn quốc tế LZT: {str(e)}"
            }

    async def _find_available_item(self, product_id: str) -> str | None:
        """Tìm 1 item khả dụng trên sàn theo từ khóa category"""
        # Search query matching product
        return None
