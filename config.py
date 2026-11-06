import os
from dotenv import load_dotenv

load_dotenv()

# ================================
# TELEGRAM BOT CONFIG
# ================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))

# ================================
# BUSINESS CONFIG
# ================================
# Tỷ lệ lãi (0.20 = 20%)
PROFIT_MARGIN = float(os.getenv("PROFIT_MARGIN", "0.20"))

# Tỷ giá USD -> VND (dùng khi sàn quốc tế báo giá USD)
USD_TO_VND_RATE = float(os.getenv("USD_TO_VND_RATE", "25400"))

# Tỷ giá RUB -> VND (dùng cho sàn Nga như LZT/Plati nếu tính bằng Rúp)
RUB_TO_VND_RATE = float(os.getenv("RUB_TO_VND_RATE", "280"))

# Nhà cung cấp mặc định: 'mock' (để test), 'lzt', 'plati', 'taphoammo'
SUPPLIER_TYPE = os.getenv("SUPPLIER_TYPE", "mock").lower()

# ================================
# VIETQR & SEPAY CONFIG
# ================================
BANK_ID = os.getenv("BANK_ID", "MBBank")            # Ví dụ: MBBank, VCB, ACB, TPBank, VPBank...
BANK_ACCOUNT_NO = os.getenv("BANK_ACCOUNT_NO", "0987654321")
BANK_ACCOUNT_NAME = os.getenv("BANK_ACCOUNT_NAME", "CHU TAI KHOAN")

SEPAY_API_KEY = os.getenv("SEPAY_API_KEY", "")
SEPAY_WEBHOOK_SECRET = os.getenv("SEPAY_WEBHOOK_SECRET", "")

# Port chạy Webhook nhận thông báo tiền về từ SePay
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# ================================
# SUPPLIERS CREDENTIALS
# ================================
# LZT Market (Lolzteam)
LZT_API_TOKEN = os.getenv("LZT_API_TOKEN", "")
LZT_BASE_URL = os.getenv("LZT_BASE_URL", "https://api.lzt.market")

# Plati.market / Digiseller
DIGISELLER_SELLER_ID = os.getenv("DIGISELLER_SELLER_ID", "")
DIGISELLER_API_KEY = os.getenv("DIGISELLER_API_KEY", "")

# Tạp Hóa MMO
TAPHOAMMO_API_KEY = os.getenv("TAPHOAMMO_API_KEY", "")

# ================================
# USERBOT & SUPREMELEADER API CONFIG
# ================================
USERBOT_API_ID = int(os.getenv("USERBOT_API_ID", "0"))
USERBOT_API_HASH = os.getenv("USERBOT_API_HASH", "")
USERBOT_SESSION_STRING = os.getenv("USERBOT_SESSION_STRING", "")
TARGET_BOT_USERNAME = os.getenv("TARGET_BOT_USERNAME", "SupremeLeaderShopBot")
SUPREME_API_KEY = os.getenv("SUPREME_API_KEY", "api_BvV3Go0Ns8BywwdwUiko5HLGxEDPZAMEQDgLm1XAxxc")
SUPREME_BASE_URL = os.getenv("SUPREME_BASE_URL", "https://telegram-shop-bot-production-48fa.up.railway.app")

# ================================
# DATABASE
# ================================
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_store.db")
