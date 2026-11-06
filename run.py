import sys
import asyncio
import logging
import uvicorn

# Thiết lập UTF-8 cho console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import SERVER_HOST, SERVER_PORT, TELEGRAM_BOT_TOKEN, AUTO_SYNC_INTERVAL_MINUTES
import database
from bot import build_application, sync_supplier_catalog
from server import app as fastapi_app, set_bot_instance

# Cấu hình logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AppRunner")

async def periodic_product_sync(interval_minutes: int):
    """Tiến trình ngầm tự động gọi API đồng bộ giá và tồn kho từ bot nguồn theo chu kỳ"""
    interval_seconds = max(interval_minutes, 1) * 60
    logger.info(f"⏰ [Auto-Sync] Đã kích hoạt tự động gọi API cập nhật sản phẩm & tồn kho mỗi {interval_minutes} phút.")
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            logger.info("🔄 [Auto-Sync] Đang tự động gọi API lấy danh sách sản phẩm & tồn kho mới nhất...")
            await sync_supplier_catalog()
            logger.info("✅ [Auto-Sync] Tự động đồng bộ hoàn tất.")
        except asyncio.CancelledError:
            logger.info("🛑 [Auto-Sync] Tiến trình tự động đồng bộ đã dừng.")
            break
        except Exception as e:
            logger.error(f"❌ [Auto-Sync] Lỗi trong quá trình tự động đồng bộ: {e}")

async def main():
    logger.info("=== ĐANG KHỞI ĐỘNG HỆ THỐNG TELEGRAM BOT DROPSHIPPING ===")

    # 1. Khởi tạo DB SQLite
    await database.init_db()

    # 2. Đồng bộ sản phẩm và giá (+20% lãi)
    await sync_supplier_catalog()

    # Kiểm tra Token Telegram Bot
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.warning(
            "⚠️ CHƯA CÓ TELEGRAM_BOT_TOKEN! Vui lòng cấu hình token trong file .env trước khi chạy bot.\n"
            "Chế độ Webhook Server vẫn sẽ chạy để bạn test API."
        )
        # Chỉ chạy server
        config = uvicorn.Config(fastapi_app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
        return

    # 3. Khởi tạo Telegram Bot
    telegram_app = build_application()

    # Gắn bot instance vào server để Webhook có thể gửi tin nhắn cho khách
    set_bot_instance(telegram_app.bot)

    # 4. Khởi chạy Uvicorn Webhook Server
    config = uvicorn.Config(fastapi_app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")
    server = uvicorn.Server(config)

    # 5. Chạy cả Telegram Bot Poller và Webhook Server đồng thời
    async with telegram_app:
        await telegram_app.start()
        await telegram_app.updater.start_polling(drop_pending_updates=True)
        logger.info(f"🚀 Telegram Bot đang lắng nghe tin nhắn...")
        logger.info(f"🌐 Webhook Server đang lắng nghe tại http://{SERVER_HOST}:{SERVER_PORT}")
        logger.info(f"👉 SePay Webhook Endpoint: http://<IP_HOẶC_DOMAIN>:{SERVER_PORT}/api/sepay/webhook")

        # Khởi chạy luồng tự động đồng bộ định kỳ trong nền
        sync_task = asyncio.create_task(periodic_product_sync(AUTO_SYNC_INTERVAL_MINUTES))

        try:
            await server.serve()
        finally:
            logger.info("Đang dừng các dịch vụ...")
            sync_task.cancel()
            await telegram_app.updater.stop()
            await telegram_app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Hệ thống đã dừng.")
