import logging
import httpx
from config import TAPHOAMMO_API_KEY
from suppliers.base import BaseSupplier

logger = logging.getLogger(__name__)

class TaphoammoSupplier(BaseSupplier):
    """
    Tích hợp API Tạp Hóa MMO (Taphoammo.net)
    Sàn thương mại điện tử sản phẩm số lớn nhất Việt Nam.
    Có sẵn API tạo đơn hàng tự động lấy kho hàng tài khoản ChatGPT, Gemini, YouTube...
    """

    def __init__(self):
        self.base_url = "https://taphoammo.net/api"
        self.api_key = TAPHOAMMO_API_KEY

    async def fetch_products(self) -> list[dict]:
        default_items = [
            {
                "id": "thmo_chatgpt_plus",
                "supplier_id": "thmo_kiosk_gpt",
                "name": "ChatGPT Plus 1 Tháng (Tạp Hóa MMO)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Tài khoản ChatGPT Plus đăng ký thẻ ngoại, không khoá, bảo hành 30 ngày.",
                "cost_price_vnd": 140000,
            },
            {
                "id": "thmo_gemini_advanced",
                "supplier_id": "thmo_kiosk_gemini",
                "name": "Google Gemini Advanced 2TB (Tạp Hóa MMO)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Tài khoản Google One AI Premium 2TB chính chủ.",
                "cost_price_vnd": 90000,
            },
            {
                "id": "thmo_youtube_family",
                "supplier_id": "thmo_kiosk_yt",
                "name": "YouTube Premium Slot Gia Đình 6 Tháng (Tạp Hóa MMO)",
                "category": "🎵 Giải Trí (YouTube / Netflix)",
                "description": "Thêm vào nhóm gia đình không mất lịch sử xem, không quảng cáo.",
                "cost_price_vnd": 100000,
            }
        ]

        products = []
        for item in default_items:
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
                "in_stock": True
            })
        return products

    async def buy_product(self, product_id: str, custom_data: dict = None) -> dict:
        if not self.api_key:
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": "Chưa cấu hình TAPHOAMMO_API_KEY trong file .env"
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {
                    "api_key": self.api_key,
                    "kiosk_id": custom_data.get("kiosk_id", ""),
                    "quantity": 1
                }
                res = await client.post(f"{self.base_url}/orders/create", json=payload)
                data = res.json()
                if data.get("status") == 1:
                    account_data = data.get("data", "")
                    return {
                        "success": True,
                        "delivered_data": f"✅ **THÔNG TIN TÀI KHOẢN TẠP HÓA MMO**\n\n`{account_data}`",
                        "cost_price_vnd": int(data.get("amount", 0)),
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "delivered_data": "",
                        "cost_price_vnd": 0,
                        "error": data.get("message", "Mua hàng Tạp Hóa MMO thất bại.")
                    }
        except Exception as e:
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": f"Lỗi gọi API Tạp Hóa MMO: {str(e)}"
            }
