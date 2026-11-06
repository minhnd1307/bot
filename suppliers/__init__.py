from config import SUPPLIER_TYPE
from suppliers.base import BaseSupplier
from suppliers.mock_supplier import MockSupplier
from suppliers.lzt_market import LztMarketSupplier
from suppliers.plati_market import PlatiMarketSupplier
from suppliers.taphoammo import TaphoammoSupplier
from suppliers.telegram_userbot import TelegramUserbotSupplier

def get_supplier() -> BaseSupplier:
    """Trả về nhà cung cấp sản phẩm tương ứng với cấu hình trong .env"""
    supplier_key = SUPPLIER_TYPE.lower()
    if supplier_key == "lzt":
        return LztMarketSupplier()
    elif supplier_key == "plati":
        return PlatiMarketSupplier()
    elif supplier_key == "taphoammo":
        return TaphoammoSupplier()
    elif supplier_key == "userbot":
        return TelegramUserbotSupplier()
    else:
        return MockSupplier()
