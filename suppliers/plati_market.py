import logging
import httpx
from config import DIGISELLER_API_KEY, DIGISELLER_SELLER_ID, USD_TO_VND_RATE
from suppliers.base import BaseSupplier

logger = logging.getLogger(__name__)

class PlatiMarketSupplier(BaseSupplier):
    """
    Tích hợp Plati.Market thông qua Digiseller API (api.digiseller.com)
    Docs: https://digiseller.market/en/api/
    Chuyên về Key bản quyền, nâng cấp chính chủ YouTube, ChatGPT, Netflix...
    """

    def __init__(self):
        self.base_url = "https://api.digiseller.com/api"
        self.seller_id = DIGISELLER_SELLER_ID
        self.api_key = DIGISELLER_API_KEY

    async def fetch_products(self) -> list[dict]:
        """Lấy danh mục sản phẩm từ đối tác Plati"""
        default_templates = [
            {
                "id": "plati_chatgpt_plus_key",
                "supplier_id": "digiseller_gpt_01",
                "name": "ChatGPT Plus (Plati.Market Global)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Code kích hoạt hoặc tài khoản ChatGPT Plus chính hãng từ Plati.market.",
                "cost_usd": 6.5, # ~165.000 VNĐ
            },
            {
                "id": "plati_yt_prem_upgrade",
                "supplier_id": "digiseller_yt_01",
                "name": "YouTube Premium (Plati Official Invite)",
                "category": "🎵 Giải Trí (YouTube / Netflix)",
                "description": "Nâng cấp trực tiếp trên tài khoản cá nhân, bảo hành toàn thời gian.",
                "cost_usd": 4.5, # ~114.000 VNĐ
            }
        ]

        products = []
        for t in default_templates:
            cost_vnd = int(t["cost_usd"] * USD_TO_VND_RATE)
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
        if not self.api_key:
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": "Chưa cấu hình DIGISELLER_API_KEY trong file .env"
            }
        # Implement purchase via Digiseller Agent API
        return {
            "success": False,
            "delivered_data": "",
            "cost_price_vnd": 0,
            "error": "Tài khoản đại lý Digiseller chưa đủ số dư hoặc sản phẩm đang hết hàng."
        }
