import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from config import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_TELEGRAM_ID,
    BANK_ID,
    BANK_ACCOUNT_NO,
    BANK_ACCOUNT_NAME,
)
import database
from suppliers import get_supplier
from payments.vietqr import get_vietqr_image_url
from fulfillment import fulfill_order

logger = logging.getLogger(__name__)

# ================================
# BÀN PHÍM ĐIỀU HƯỚNG CHÍNH
# ================================
def get_main_menu_keyboard(user_id: int):
    buttons = [
        [InlineKeyboardButton("🛒 Mua Tài Khoản (ChatGPT, YouTube...)", callback_data="menu_categories")],
        [
            InlineKeyboardButton("📦 Đơn Hàng Của Tôi", callback_data="menu_my_orders"),
            InlineKeyboardButton("ℹ️ Bảo Hành & Lưu Ý", callback_data="menu_policy")
        ],
        [InlineKeyboardButton("📞 Hỗ Trợ Kỹ Thuật", callback_data="menu_support")]
    ]
    if user_id == ADMIN_TELEGRAM_ID:
        buttons.append([InlineKeyboardButton("📊 Thống Kê Doanh Thu (Admin)", callback_data="admin_stats")])
    return InlineKeyboardMarkup(buttons)

# ================================
# HANDLERS
# ================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await database.register_user(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "Khách hàng"
    )

    welcome_text = (
        f"👋 **Chào mừng {user.first_name} đến với Shop Tài Khoản Tự Động!**\n\n"
        f"⚡ Hệ thống bán tài khoản số và nâng cấp dịch vụ tự động 24/7:\n"
        f"• **AI:** ChatGPT Plus, Gemini Advanced 2TB...\n"
        f"• **Giải Trí:** YouTube Premium không quảng cáo, Netflix 4K...\n\n"
        f"💎 **Cam kết:**\n"
        f"- Nhận hàng tự động sau **1-3 giây** qua chuyển khoản VietQR.\n"
        f"- Bảo hành 1 đổi 1 suốt thời gian sử dụng.\n\n"
        f"Vui lòng chọn mục bên dưới để bắt đầu:"
    )

    if update.message:
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_menu_keyboard(user.id),
            parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            welcome_text,
            reply_markup=get_main_menu_keyboard(user.id),
            parse_mode="Markdown"
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # 1. Quay về trang chủ
    if data == "menu_home":
        await start_command(update, context)

    # 2. Xem danh mục sản phẩm
    elif data == "menu_categories":
        categories = await database.get_categories()
        if not categories:
            await query.message.edit_text(
                "⚠️ Kho hàng đang được cập nhật, vui lòng thử lại sau giây lát!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Trang chủ", callback_data="menu_home")]])
            )
            return

        buttons = []
        for cat in categories:
            buttons.append([InlineKeyboardButton(f"{cat}", callback_data=f"cat_{cat}")])
        buttons.append([InlineKeyboardButton("🔙 Quay lại Trang Chủ", callback_data="menu_home")])

        await query.message.edit_text(
            "📂 **DANH MỤC DỊCH VỤ SẴN HÀNG:**\n\nVui lòng chọn loại dịch vụ bạn muốn mua:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    # 3. Chọn 1 danh mục -> Xem các sản phẩm
    elif data.startswith("cat_"):
        cat_name = data.replace("cat_", "")
        products = await database.get_products_by_category(cat_name)

        buttons = []
        for p in products:
            btn_text = f"{p['name']} — {p['sell_price_vnd']:,}đ"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"prod_{p['id']}")])
        buttons.append([InlineKeyboardButton("🔙 Quay lại Danh mục", callback_data="menu_categories")])

        await query.message.edit_text(
            f"🛒 **CÁC GÓI SẢN PHẨM TRONG [{cat_name}]:**\n\nBấm vào gói bạn muốn xem chi tiết và mua:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    # 4. Xem chi tiết sản phẩm
    elif data.startswith("prod_"):
        prod_id = data.replace("prod_", "")
        product = await database.get_product(prod_id)
        if not product:
            await query.message.edit_text("❌ Không tìm thấy sản phẩm này!")
            return

        detail_text = (
            f"📦 **{product['name']}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 **Mô tả:** {product['description']}\n\n"
            f"💰 **Giá bán:** `{product['sell_price_vnd']:,} VNĐ`\n"
            f"🛡️ **Bảo hành:** 1 đổi 1 tự động\n"
            f"⚡ **Giao nhận:** Tự động qua tin nhắn ngay sau khi thanh toán\n"
            f"━━━━━━━━━━━━━━━━━━"
        )

        buttons = [
            [InlineKeyboardButton("⚡ MUA NGAY (Tạo mã VietQR)", callback_data=f"buy_{product['id']}")],
            [InlineKeyboardButton("🔙 Quay lại", callback_data=f"cat_{product['category']}")]
        ]
        await query.message.edit_text(detail_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # 5. Bấm MUA NGAY -> Tạo đơn hàng & xuất mã VietQR
    elif data.startswith("buy_"):
        prod_id = data.replace("buy_", "")
        product = await database.get_product(prod_id)
        if not product:
            await query.message.edit_text("❌ Không tìm thấy sản phẩm!")
            return

        # Tạo mã đơn ngẫu nhiên 6 chữ số: DH123456
        order_code = f"DH{random.randint(100000, 999999)}"

        await database.create_order(
            order_code=order_code,
            user_id=user_id,
            product_id=product["id"],
            product_name=product["name"],
            cost_price=product["cost_price_vnd"],
            sell_price=product["sell_price_vnd"],
            profit=product["profit_vnd"]
        )

        # Tạo link ảnh VietQR
        qr_url = get_vietqr_image_url(amount=product["sell_price_vnd"], order_code=order_code)

        invoice_text = (
            f"🧾 **HÓA ĐƠN ĐẶT HÀNG #{order_code}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 Sản phẩm: **{product['name']}**\n"
            f"💰 Số tiền cần thanh toán: `{product['sell_price_vnd']:,} VNĐ`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏦 **THÔNG TIN CHUYỂN KHOẢN (VIETQR TỰ ĐỘNG):**\n"
            f"• Ngân hàng: **{BANK_ID}**\n"
            f"• Số tài khoản: `{BANK_ACCOUNT_NO}`\n"
            f"• Tên chủ tài khoản: **{BANK_ACCOUNT_NAME}**\n"
            f"• Số tiền: `{product['sell_price_vnd']:,}` VNĐ\n"
            f"• Nội dung chuyển khoản: `{order_code}`  *(BẮT BUỘC)*\n\n"
            f"⚠️ **LƯU Ý QUAN TRỌNG:**\n"
            f"1. Vui lòng chuyển **ĐÚNG SỐ TIỀN** và **ĐÚNG NỘI DUNG** `{order_code}`.\n"
            f"2. Quét mã QR để không bị sai thông tin.\n"
            f"3. Hệ thống sẽ tự động giao tài khoản sau 1-3 giây ngay khi ngân hàng nhận tiền!"
        )

        buttons = [
            [InlineKeyboardButton("🔄 Tôi Đã Chuyển Tiền (Kiểm Tra)", callback_data=f"check_{order_code}")],
            [InlineKeyboardButton("❌ Hủy Đơn Hàng", callback_data=f"cancel_{order_code}")]
        ]

        # Xóa tin nhắn cũ và gửi tin mới kèm ảnh QR
        try:
            await query.message.delete()
        except Exception:
            pass

        try:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=qr_url,
                caption=invoice_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Không gửi được ảnh VietQR trực tiếp, gửi tin nhắn text: {e}")
            await context.bot.send_message(
                chat_id=user_id,
                text=invoice_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )

    # 6. Khách bấm kiểm tra thanh toán
    elif data.startswith("check_"):
        order_code = data.replace("check_", "")
        order = await database.get_order(order_code)
        if not order:
            await query.answer("❌ Đơn hàng không tồn tại!", show_alert=True)
            return

        if order["status"] == "COMPLETED":
            await query.answer("✅ Đơn hàng đã hoàn tất!", show_alert=True)
            await query.message.reply_text(
                f"🎉 **ĐƠN HÀNG {order_code} ĐÃ HOÀN TẤT**\n\n{order['delivered_data']}",
                parse_mode="Markdown"
            )
        elif order["status"] == "PAID":
            await query.answer("⏳ Đang bàn giao tài khoản từ kho, vui lòng đợi 3 giây...", show_alert=True)
            await fulfill_order(order_code, bot=context.bot)
        else:
            await query.answer(
                "⏳ Hệ thống chưa nhận được thông báo biến động số dư từ ngân hàng.\n"
                "Nếu bạn vừa chuyển tiền, vui lòng đợi 10-30 giây rồi bấm lại nhé!",
                show_alert=True
            )

    # 7. Khách hủy đơn
    elif data.startswith("cancel_"):
        order_code = data.replace("cancel_", "")
        await database.update_order_status(order_code, "CANCELLED")
        await query.message.delete()
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Đã hủy đơn hàng #{order_code}.",
            reply_markup=get_main_menu_keyboard(user_id)
        )

    # 8. Xem các đơn hàng đã mua
    elif data == "menu_my_orders":
        orders = await database.get_user_orders(user_id, limit=5)
        if not orders:
            await query.message.edit_text(
                "📦 Bạn chưa có đơn hàng nào trong hệ thống.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Mua ngay", callback_data="menu_categories")]])
            )
            return

        msg = "📦 **LỊCH SỬ 5 ĐƠN HÀNG GẦN NHẤT CỦA BẠN:**\n\n"
        for o in orders:
            status_icon = "✅" if o["status"] == "COMPLETED" else "⏳" if o["status"] == "PENDING" else "❌"
            msg += (
                f"{status_icon} **Đơn #{o['order_code']}** — {o['product_name']}\n"
                f"• Trạng thái: `{o['status']}`\n"
                f"• Giá tiền: `{o['sell_price_vnd']:,} đ`\n"
                f"• Thời gian: `{o['created_at']}`\n"
            )
            if o["status"] == "COMPLETED" and o["delivered_data"]:
                msg += f"• Dữ liệu: Đã bàn giao trong tin nhắn.\n"
            msg += "━━━━━━━━━━━━━━━━━━\n"

        buttons = [[InlineKeyboardButton("🔙 Trang chủ", callback_data="menu_home")]]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # 9. Chính sách & Bảo hành
    elif data == "menu_policy":
        policy_text = (
            "ℹ️ **CHÍNH SÁCH BÁN HÀNG & BẢO HÀNH**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "1. **Tài khoản ChatGPT Plus:**\n"
            "   - Bảo hành 1 đổi 1 trong 30 ngày.\n"
            "   - Không bảo hành nếu vi phạm chính sách của OpenAI dẫn tới khoá acc.\n\n"
            "2. **Tài khoản Google Gemini Advanced:**\n"
            "   - Bảo hành trọn gói chu kỳ 1 tháng, hỗ trợ đổi acc nếu mất gói 2TB.\n\n"
            "3. **YouTube Premium:**\n"
            "   - Mời nhóm gia đình chính chủ hoặc cấp tài khoản có sẵn.\n"
            "   - Bảo hành suốt thời gian mua (6 tháng hoặc 12 tháng)."
        )
        buttons = [[InlineKeyboardButton("🔙 Trang chủ", callback_data="menu_home")]]
        await query.message.edit_text(policy_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # 10. Hỗ trợ kỹ thuật
    elif data == "menu_support":
        support_text = (
            "📞 **HỖ TRỢ KHÁCH HÀNG 24/7**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Nếu bạn gặp sự cố chuyển khoản nhầm nội dung hoặc cần bảo hành tài khoản:\n\n"
            "👉 **Admin Telegram:** @your_telegram_username\n"
            "⏰ Thời gian phản hồi: 5 - 15 phút."
        )
        buttons = [[InlineKeyboardButton("🔙 Trang chủ", callback_data="menu_home")]]
        await query.message.edit_text(support_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # 11. Báo cáo doanh thu & Lợi nhuận (Chỉ Admin)
    elif data == "admin_stats" and user_id == ADMIN_TELEGRAM_ID:
        stats = await database.get_statistics()
        admin_text = (
            "📊 **BÁO CÁO KINH DOANH SHOP TỰ ĐỘNG**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👥 Tổng số khách hàng: `{stats['total_users']}`\n"
            f"✅ Tổng đơn thành công: `{stats['completed_orders']}`\n"
            f"💵 Tổng doanh thu: `{stats['total_revenue']:,} VNĐ`\n"
            f"📈 **Tổng tiền lời ròng (+20%): `+{stats['total_profit']:,} VNĐ`**\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        buttons = [[InlineKeyboardButton("🔙 Trang chủ", callback_data="menu_home")]]
        await query.message.edit_text(admin_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def sync_supplier_catalog():
    """Hàm tải sản phẩm từ nhà cung cấp và nạp vào DB"""
    supplier = get_supplier()
    logger.info(f"Đang đồng bộ sản phẩm từ nhà cung cấp {supplier.__class__.__name__}...")
    products = await supplier.fetch_products()
    await database.sync_products(products)
    logger.info(f"Đã đồng bộ {len(products)} sản phẩm vào cơ sở dữ liệu.")

def build_application() -> Application:
    """Tạo Application của python-telegram-bot"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN chưa được cung cấp trong cấu hình!")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    return app
