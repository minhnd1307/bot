import math
from abc import ABC, abstractmethod
from config import PROFIT_MARGIN

class BaseSupplier(ABC):
    """Lớp cơ sở trừu tượng cho tất cả các nhà cung cấp sản phẩm"""

    @abstractmethod
    async def fetch_products(self) -> list[dict]:
        """
        Lấy danh sách sản phẩm từ nhà cung cấp.
        Mỗi item phải có:
        - id: str
        - supplier_id: str
        - name: str
        - category: str
        - description: str
        - cost_price_vnd: int (giá gốc bên nguồn)
        - sell_price_vnd: int (giá bán = giá gốc + 20%)
        - profit_vnd: int (tiền lãi = giá bán - giá gốc)
        - in_stock: bool
        """
        pass

    @abstractmethod
    async def buy_product(self, product_id: str, custom_data: dict = None) -> dict:
        """
        Gọi API sang nhà cung cấp để mua tự động.
        Trả về dict:
        {
            "success": True/False,
            "delivered_data": "Nội dung tài khoản bàn giao cho khách",
            "cost_price_vnd": 150000,
            "error": "Thông báo lỗi nếu có"
        }
        """
        pass

    async def get_balance(self) -> dict:
        """Kiểm tra số dư ví trên nhà cung cấp (mặc định trả về N/A nếu sàn không hỗ trợ)"""
        return {"success": True, "balance": 0.0, "balanceText": "N/A", "walletCurrency": "USD"}

    @staticmethod
    def calculate_price_and_profit(cost_price_vnd: int) -> tuple[int, int]:
        """
        Tính giá bán cộng 20% lợi nhuận và làm tròn lên hàng nghìn (1.000đ).
        Ví dụ: Giá gốc 155.000đ -> +20% = 186.000đ
        """
        raw_sell_price = cost_price_vnd * (1.0 + PROFIT_MARGIN)
        # Làm tròn lên bội số của 1.000 VNĐ
        sell_price_vnd = int(math.ceil(raw_sell_price / 1000.0) * 1000)
        profit_vnd = sell_price_vnd - cost_price_vnd
        return sell_price_vnd, profit_vnd
