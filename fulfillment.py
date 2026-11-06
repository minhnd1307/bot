import logging
from config import ADMIN_TELEGRAM_ID
import database
from suppliers import get_supplier

logger = logging.getLogger(__name__)

async def fulfill_order(order_code: str, bot=None) -> dict:
    """
    Xử lý tự động hoàn toàn:
    1. Kiểm tra đơn hàng trong DB
    2. Gọi API nhà cung cấp để mua hàng
    3. Trả kết quả tài khoản cho khách qua Telegram
    4. Báo cáo lợi nhuận (+20%) cho Admin
    """
    order = await database.get_order(order_code)
    if not order:
        logger.error(f"Không tìm thấy đơn hàng {order_code} để xử lý.")
        return {"success": False, "error": "Order not found"}

    if order["status"] == "COMPLETED":
        logger.info(f"Đơn hàng {order_code} đã được giao trước đó.")
        return {"success": True, "delivered_data": order["delivered_data"]}

    # Cập nhật đơn hàng đã thanh toán
    await database.update_order_status(order_code, "PAID")

    # Gọi API nhà cung cấp
    supplier = get_supplier()
    qty = order.get("quantity") or 1
    logger.info(f"Đang gọi nhà cung cấp ({supplier.__class__.__name__}) cho đơn {order_code} (Số lượng: {qty})...")

    purchase_result = await supplier.buy_product(
        product_id=order["product_id"],
        custom_data={"order_code": order_code, "quantity": qty}
    )

    if purchase_result.get("success"):
        delivered_data = purchase_result.get("delivered_data", "")
        await database.update_order_status(order_code, "COMPLETED", delivered_data=delivered_data)

        # Gửi tin nhắn trả hàng cho khách hàng qua Telegram
        if bot:
            try:
                user_msg = (
                    f"🎉 **ĐƠN HÀNG THÀNH CÔNG!**\n"
                    f"Mã đơn hàng: `{order_code}`\n"
                    f"Sản phẩm: **{order['product_name']}**\n"
                    f"Số lượng: `{qty}` tài khoản\n\n"
                    f"{delivered_data}\n\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🙏 Cảm ơn bạn đã ủng hộ shop!\n"
                    f"Nếu cần hỗ trợ bảo hành, vui lòng liên hệ Admin qua nút hỗ trợ trong menu."
                )
                await bot.send_message(
                    chat_id=order["user_id"],
                    text=user_msg,
                    parse_mode="Markdown"
                )
                logger.info(f"Đã gửi thông tin đơn hàng {order_code} cho khách {order['user_id']}.")
            except Exception as e:
                logger.error(f"Lỗi khi gửi tin nhắn cho khách: {e}")

            # Gửi thông báo lợi nhuận cho Admin
            if ADMIN_TELEGRAM_ID:
                try:
                    admin_msg = (
                        f"💰 **ĐƠN HÀNG MỚI THÀNH CÔNG!**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"🆔 Mã đơn: `{order_code}`\n"
                        f"👤 Khách hàng ID: `{order['user_id']}`\n"
                        f"📦 Sản phẩm: **{order['product_name']}** (x{qty})\n"
                        f"💵 Khách trả: `{order['sell_price_vnd']:,} VNĐ`\n"
                        f"🏷️ Giá vốn nguồn: `{order['cost_price_vnd']:,} VNĐ`\n"
                        f"📈 **Lợi nhuận ròng (+20%): `+{order['profit_vnd']:,} VNĐ`**\n"
                        f"━━━━━━━━━━━━━━━━━━"
                    )
                    await bot.send_message(
                        chat_id=ADMIN_TELEGRAM_ID,
                        text=admin_msg,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Lỗi khi gửi tin nhắn báo admin: {e}")

        return {"success": True, "delivered_data": delivered_data}

    else:
        # Nếu kho nguồn bị lỗi/hết hàng
        error_msg = purchase_result.get("error", "Lỗi không xác định từ kho nguồn")
        await database.update_order_status(order_code, "FAILED_SUPPLIER", error_message=error_msg)
        logger.error(f"Đơn hàng {order_code} thất bại từ kho nguồn: {error_msg}")

        if bot:
            try:
                # Báo cho khách
                await bot.send_message(
                    chat_id=order["user_id"],
                    text=(
                        f"⚠️ **Thông báo đơn hàng #{order_code}**\n\n"
                        f"Hệ thống đã nhận được chuyển khoản của bạn cho sản phẩm **{order['product_name']}**.\n"
                        f"Tuy nhiên kho nguồn hiện đang tạm hết hàng hoặc gặp sự cố kết nối.\n\n"
                        f"👉 **Đừng lo lắng!** Admin đã nhận được thông báo và sẽ xử lý hoàn tiền 100% hoặc giao bù tài khoản thủ công cho bạn ngay."
                    ),
                    parse_mode="Markdown"
                )
                # Báo động khẩn cho Admin
                if ADMIN_TELEGRAM_ID:
                    await bot.send_message(
                        chat_id=ADMIN_TELEGRAM_ID,
                        text=(
                            f"🚨 **CẢNH BÁO: LỖI KHO NGUỒN CẦN XỬ LÝ!**\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"Mã đơn: `{order_code}`\n"
                            f"Sản phẩm: {order['product_name']}\n"
                            f"Tiền khách đã trả: `{order['sell_price_vnd']:,} VNĐ`\n"
                            f"Chi tiết lỗi từ sàn: `{error_msg}`\n"
                            f"Vui lòng kiểm tra tài khoản nguồn hoặc hoàn tiền cho khách ID `{order['user_id']}`!"
                        ),
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Lỗi gửi tin nhắn cảnh báo: {e}")

        return {"success": False, "error": error_msg}
