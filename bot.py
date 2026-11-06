import math
import logging
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
    MenuButtonCommands,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from config import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_TELEGRAM_ID,
    SUPPORT_EMAIL,
    SUPPORT_TELEGRAM,
    BANK_ID,
    BANK_ACCOUNT_NO,
    BANK_ACCOUNT_NAME,
)
import database
from suppliers import get_supplier
from payments.vietqr import get_vietqr_image_url, get_vietqr_image_bytes
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
        buttons.append([
            InlineKeyboardButton("👑 Quản Trị Shop (Admin)", callback_data="admin_dashboard")
        ])
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Doanh Thu & Lợi Nhuận", callback_data="admin_stats"),
            InlineKeyboardButton("📦 Lịch Sử Đơn Hàng", callback_data="admin_orders_0")
        ],
        [
            InlineKeyboardButton("💰 Số Dư Ví Bot Nguồn", callback_data="admin_balance"),
            InlineKeyboardButton("🔄 Đồng Bộ Nguồn Hàng", callback_data="admin_sync")
        ],
        [
            InlineKeyboardButton("🔍 Hướng Dẫn Tra Cứu Đơn", callback_data="admin_search_guide"),
            InlineKeyboardButton("🔙 Về Menu Khách", callback_data="menu_home")
        ]
    ])

def get_support_text_and_markup():
    lines = [
        "📞 **HỖ TRỢ KHÁCH HÀNG 24/7**",
        "━━━━━━━━━━━━━━━━━━",
        "Nếu bạn gặp sự cố chuyển khoản nhầm nội dung hoặc cần bảo hành tài khoản:\n"
    ]
    if SUPPORT_EMAIL:
        lines.append(f"✉️ **Email hỗ trợ:** `{SUPPORT_EMAIL}`")
    if SUPPORT_TELEGRAM:
        tg_clean = SUPPORT_TELEGRAM if SUPPORT_TELEGRAM.startswith("@") else f"@{SUPPORT_TELEGRAM}"
        lines.append(f"👉 **Admin Telegram:** {tg_clean}")
    elif not SUPPORT_EMAIL:
        lines.append("👉 **Admin Telegram:** @your_telegram_username")

    lines.append("\n⏰ **Thời gian phản hồi:** 5 - 15 phút.")
    text = "\n".join(lines)

    buttons = []
    contact_row = []
    if SUPPORT_TELEGRAM:
        tg_username = SUPPORT_TELEGRAM.lstrip("@")
        contact_row.append(InlineKeyboardButton("💬 Nhắn Tin Telegram", url=f"https://t.me/{tg_username}"))
    if contact_row:
        buttons.append(contact_row)

    buttons.append([InlineKeyboardButton("🔙 Trang chủ", callback_data="menu_home")])
    return text, InlineKeyboardMarkup(buttons)

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

        # Sinh ảnh QR VietQR chuẩn PNG dạng bytes (SePay online hoặc EMVCo offline)
        qr_bytes = await get_vietqr_image_bytes(amount=product["sell_price_vnd"], order_code=order_code)

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
                photo=qr_bytes,
                filename=f"vietqr_{order_code}.png",
                caption=invoice_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Không gửi được ảnh VietQR trực tiếp: {e}")
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
        support_text, keyboard = get_support_text_and_markup()
        await query.message.edit_text(support_text, reply_markup=keyboard, parse_mode="Markdown")

    # Nút không phản hồi (chỉ hiển thị)
    elif data == "noop":
        await query.answer()
        return

    # Guard bảo mật chung cho tất cả chức năng Quản Trị Shop
    elif data.startswith("admin_") and user_id != ADMIN_TELEGRAM_ID:
        await query.answer("⛔ Bạn không có quyền truy cập bảng quản trị!", show_alert=True)
        return

    # 11. Bảng điều khiển quản trị chính (Admin Dashboard)
    elif data == "admin_dashboard":
        text = (
            "👑 **TRUNG TÂM QUẢN TRỊ SHOP (ADMIN DASHBOARD)**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Chào Admin! Hệ thống Dropship & VietQR đang hoạt động tự động 24/7.\n\n"
            "Chọn một tác vụ quản lý bên dưới:"
        )
        await query.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

    # 12. Báo cáo doanh thu & Lợi nhuận chi tiết
    elif data == "admin_stats":
        stats = await database.get_admin_detailed_stats()
        all_time = stats["all_time"]
        today = stats["today"]
        last_7 = stats["last_7_days"]
        top_prods = stats["top_products"]

        total_orders = all_time["total_orders"]
        success_rate = (all_time["completed"] / total_orders * 100) if total_orders > 0 else 0

        admin_text = (
            "📊 **BÁO CÁO DOANH THU & HIỆU SUẤT KINH DOANH**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📅 **HÔM NAY:**\n"
            f"• Đơn hoàn tất: `{today['completed']}/{today['total']}` đơn\n"
            f"• Doanh thu: `{today['revenue']:,} VNĐ`\n"
            f"• Lợi nhuận ròng (+20%): `+{today['profit']:,} VNĐ`\n\n"
            "🗓 **7 NGÀY GẦN NHẤT:**\n"
            f"• Đơn hoàn tất: `{last_7['completed']}/{last_7['total']}` đơn\n"
            f"• Doanh thu: `{last_7['revenue']:,} VNĐ`\n"
            f"• Lợi nhuận ròng (+20%): `+{last_7['profit']:,} VNĐ`\n\n"
            "🏆 **TOÀN THỜI GIAN (ALL-TIME):**\n"
            f"• Tổng đơn hàng: `{total_orders}` đơn\n"
            f"  ↳ ✅ Hoàn tất: `{all_time['completed']}` | ⏳ Đang chờ: `{all_time['pending']}` | ❌ Lỗi: `{all_time['failed']}`\n"
            f"• Tỷ lệ giao thành công: `{success_rate:.1f}%`\n"
            f"• Tổng doanh thu: `{all_time['revenue']:,} VNĐ`\n"
            f"• 💰 **TỔNG LỢI NHUẬN RÒNG: `+{all_time['profit']:,} VNĐ`**\n\n"
            "👥 **KHÁCH HÀNG:**\n"
            f"• Tổng tài khoản đã truy cập bot: `{stats['total_users']}` người\n"
            f"• Khách hàng đã phát sinh mua: `{stats['active_buyers']}` người\n"
        )
        if top_prods:
            admin_text += "\n🔥 **TOP SẢN PHẨM BÁN CHẠY NHẤT:**\n"
            for idx, tp in enumerate(top_prods, 1):
                admin_text += f"{idx}. {tp['product_name']}: `{tp['count']}` đơn (Lãi: `+{tp['sum_profit']:,}đ`)\n"
        admin_text += "━━━━━━━━━━━━━━━━━━"

        buttons = [
            [
                InlineKeyboardButton("🔄 Làm Mới", callback_data="admin_stats"),
                InlineKeyboardButton("📦 Xem Danh Sách Đơn", callback_data="admin_orders_0")
            ],
            [InlineKeyboardButton("🔙 Về Bảng Quản Trị", callback_data="admin_dashboard")]
        ]
        await query.message.edit_text(admin_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # 13. Lịch sử đơn hàng toàn shop (có phân trang)
    elif data.startswith("admin_orders_"):
        offset = int(data.split("_")[2])
        limit = 5
        total_orders = await database.count_all_orders()
        orders = await database.get_all_orders_admin(limit=limit, offset=offset)

        total_pages = max(1, math.ceil(total_orders / limit))
        curr_page = (offset // limit) + 1

        if not orders:
            await query.message.edit_text(
                "📦 Hiện tại chưa có đơn hàng nào trong hệ thống.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Về Bảng Quản Trị", callback_data="admin_dashboard")]])
            )
            return

        msg = f"📦 **LỊCH SỬ ĐƠN HÀNG TOÀN SHOP** (Trang {curr_page}/{total_pages})\n"
        msg += f"Tổng cộng: `{total_orders}` đơn hàng\n"
        msg += "━━━━━━━━━━━━━━━━━━\n"

        action_buttons = []
        for o in orders:
            status_icon = "✅" if o["status"] == "COMPLETED" else "⏳" if o["status"] == "PENDING" else "❌"
            user_label = f"@{o['username']}" if o.get("username") else (o.get("full_name") or f"ID:{o['user_id']}")
            msg += (
                f"{status_icon} **#{o['order_code']}** — {o['product_name'][:28]}\n"
                f"• Khách: {user_label} (ID: `{o['user_id']}`)\n"
                f"• Tiền thu: `{o['sell_price_vnd']:,}đ` | Lãi: `+{o['profit_vnd']:,}đ`\n"
                f"• Giờ tạo: `{o['created_at']}` | TT: `{o['status']}`\n"
                f"──────────────────\n"
            )
            action_buttons.append([InlineKeyboardButton(f"🔍 Xem #{o['order_code']} ({o['status']})", callback_data=f"admin_view_{o['order_code']}")])

        # Hàng nút điều hướng trang
        nav_buttons = []
        if offset > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Trước", callback_data=f"admin_orders_{max(0, offset - limit)}"))
        nav_buttons.append(InlineKeyboardButton(f"📄 {curr_page}/{total_pages}", callback_data="noop"))
        if offset + limit < total_orders:
            nav_buttons.append(InlineKeyboardButton("Sau ➡️", callback_data=f"admin_orders_{offset + limit}"))

        keyboard = action_buttons + [nav_buttons, [InlineKeyboardButton("🔙 Về Bảng Quản Trị", callback_data="admin_dashboard")]]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # 14. Chi tiết một đơn hàng cụ thể
    elif data.startswith("admin_view_"):
        order_code = data.replace("admin_view_", "")
        order = await database.get_order_detail_full(order_code)
        if not order:
            await query.answer("Không tìm thấy đơn hàng này!", show_alert=True)
            return

        status_emoji = "✅" if order["status"] == "COMPLETED" else "⏳" if order["status"] == "PENDING" else "❌"
        user_label = f"@{order['username']}" if order.get("username") else (order.get("full_name") or "Khách hàng")

        detail_text = (
            f"📦 **CHI TIẾT ĐƠN HÀNG #{order['order_code']}**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"• Trạng thái: {status_emoji} `{order['status']}`\n"
            f"• Sản phẩm: **{order['product_name']}**\n"
            f"• Mã SP nguồn: `{order['product_id']}`\n"
            f"• Khách mua: {user_label} (ID: `{order['user_id']}`)\n"
            f"• Giá vốn nhập: `{order['cost_price_vnd']:,} VNĐ`\n"
            f"• Giá bán cho khách: `{order['sell_price_vnd']:,} VNĐ`\n"
            f"• Lợi nhuận ròng: `+{order['profit_vnd']:,} VNĐ`\n"
            f"• Ngày đặt hàng: `{order['created_at']}`\n"
        )
        if order.get("paid_at"):
            detail_text += f"• Thanh toán lúc: `{order['paid_at']}`\n"
        if order.get("bank_content"):
            detail_text += f"• Ngân hàng & Nội dung: `{order.get('gateway', 'SePay')}` - `{order.get('bank_content')}`\n"
        if order.get("delivered_data"):
            detail_text += f"\n🔑 **DỮ LIỆU TÀI KHOẢN ĐÃ GIAO:**\n```\n{order['delivered_data']}\n```\n"
        if order.get("error_message"):
            detail_text += f"\n⚠️ **GHI CHÚ / BÁO LỖI:**\n`{order['error_message']}`\n"
        detail_text += "━━━━━━━━━━━━━━━━━━"

        buttons = [
            [InlineKeyboardButton("🔙 Quay Lại Danh Sách Đơn", callback_data="admin_orders_0")],
            [InlineKeyboardButton("👑 Về Bảng Quản Trị", callback_data="admin_dashboard")]
        ]
        await query.message.edit_text(detail_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # 15. Kiểm tra số dư ví bot nguồn (@SupremeLeaderShopBot)
    elif data == "admin_balance":
        supplier = get_supplier()
        bal_info = await supplier.get_balance()
        balance_val = bal_info.get("balance", 0.0)
        balance_text = bal_info.get("balanceText", f"{balance_val:.2f} USDT")

        if balance_val >= 5.0:
            status_note = "🟢 **Số dư dồi dào!** Hệ thống hoàn toàn sẵn sàng tự động mua và giao tài khoản ngay khi có khách thanh toán."
        elif balance_val > 0.0:
            status_note = "🟡 **Số dư còn ít!** Bạn nên nạp thêm USDT vào bot nguồn để tránh bị gián đoạn đơn hàng."
        else:
            status_note = "🔴 **Số dư ví đang là 0.00 USDT!**\nKhi khách chuyển tiền, bot vẫn lưu đơn nhưng sẽ tạm dừng xuất hàng tự động cho đến khi bạn nạp thêm USDT."

        msg = (
            "💰 **SỐ DƯ VÍ NGUỒN (@SupremeLeaderShopBot)**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"💵 Số dư ví hiện tại: `{balance_text}`\n\n"
            f"{status_note}\n\n"
            "📌 **Hướng dẫn nạp USDT vào kho nguồn:**\n"
            "1. Mở bot @SupremeLeaderShopBot\n"
            "2. Bấm vào nút `💼 Wallet` hoặc `Deposit`.\n"
            "3. Chọn nạp qua USDT (TRC20 / TON / BEP20) với số tiền mong muốn (ví dụ 10$ - 20$).\n"
            "4. Bot nguồn sẽ tự động trừ dần tiền trong ví mỗi khi có khách mua trên bot của bạn!\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
            [InlineKeyboardButton("🔄 Kiểm Tra Lại", callback_data="admin_balance")],
            [InlineKeyboardButton("🔙 Về Bảng Quản Trị", callback_data="admin_dashboard")]
        ]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # 16. Hướng dẫn tra cứu đơn hàng nhanh
    elif data == "admin_search_guide":
        msg = (
            "🔍 **HƯỚNG DẪN TRA CỨU ĐƠN HÀNG NHANH**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Bạn có thể tra cứu thông tin bất kỳ đơn hàng nào bằng cách gửi lệnh vào tin nhắn chat:\n\n"
            "👉 `/order <mã_đơn>`\n\n"
            "**Ví dụ:**\n"
            "• `/order DH123456`\n"
            "• `/order 123456`\n\n"
            "Hệ thống sẽ lập tức hiển thị thông tin chi tiết: khách mua, giá vốn, giá bán, tiền lời và dữ liệu tài khoản đã giao!"
        )
        buttons = [[InlineKeyboardButton("🔙 Về Bảng Quản Trị", callback_data="admin_dashboard")]]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # 17. Admin bấm Đồng bộ nguồn hàng
    elif data == "admin_sync":
        await query.message.edit_text("⏳ Đang kết nối API và cào toàn bộ sản phẩm thực tế từ bot nguồn...")
        try:
            supplier = get_supplier()
            products = await supplier.fetch_products()
            await database.sync_products(products)
            await query.message.edit_text(
                f"✅ **ĐỒNG BỘ THÀNH CÔNG!**\n\n"
                f"• Đã nạp `{len(products)}` sản phẩm trực tiếp từ bot nguồn vào cơ sở dữ liệu.\n"
                f"• Giá bán tự động cộng +20% lãi ròng.\n"
                f"• Tồn kho thực tế đã được cập nhật.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Về Bảng Quản Trị", callback_data="admin_dashboard")]]),
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.message.edit_text(
                f"❌ Lỗi khi đồng bộ: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Về Bảng Quản Trị", callback_data="admin_dashboard")]])
            )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /admin dành cho chủ shop mở Bảng Quản Trị"""
    user = update.effective_user
    if user.id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Lệnh này chỉ dành cho Admin của shop!")
        return

    text = (
        "👑 **TRUNG TÂM QUẢN TRỊ SHOP (ADMIN DASHBOARD)**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Chào Admin! Hệ thống Dropship & VietQR đang hoạt động tự động 24/7.\n\n"
        "Chọn một tác vụ quản lý bên dưới:"
    )
    await update.message.reply_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /order <mã_đơn> để tra cứu thông tin đơn hàng nhanh"""
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text(
            "📌 **Hướng dẫn tra cứu đơn hàng:**\n"
            "Vui lòng gửi kèm mã đơn hàng. Ví dụ:\n"
            "`/order DH123456`",
            parse_mode="Markdown"
        )
        return

    code = args[0].strip().upper()
    order = await database.get_order_detail_full(code)
    if not order:
        matches = await database.search_orders_admin(code, limit=1)
        if matches:
            order = await database.get_order_detail_full(matches[0]["order_code"])

    if not order:
        await update.message.reply_text(f"❌ Không tìm thấy đơn hàng nào khớp với mã `{code}`.", parse_mode="Markdown")
        return

    # Khách thường chỉ được tra cứu đơn của chính họ
    if user.id != ADMIN_TELEGRAM_ID and order["user_id"] != user.id:
        await update.message.reply_text("⛔ Bạn không có quyền xem đơn hàng này.")
        return

    status_emoji = "✅" if order["status"] == "COMPLETED" else "⏳" if order["status"] == "PENDING" else "❌"
    msg = (
        f"📦 **THÔNG TIN ĐƠN HÀNG #{order['order_code']}**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"• Trạng thái: {status_emoji} `{order['status']}`\n"
        f"• Sản phẩm: **{order['product_name']}**\n"
        f"• Số tiền thanh toán: `{order['sell_price_vnd']:,} VNĐ`\n"
        f"• Thời gian đặt: `{order['created_at']}`\n"
    )
    if user.id == ADMIN_TELEGRAM_ID:
        user_label = f"@{order['username']}" if order.get("username") else (order.get("full_name") or f"ID:{order['user_id']}")
        msg += (
            f"• Khách mua: {user_label} (ID: `{order['user_id']}`)\n"
            f"• Giá vốn nhập: `{order['cost_price_vnd']:,} VNĐ`\n"
            f"• Tiền lời ròng: `+{order['profit_vnd']:,} VNĐ`\n"
        )
    if order.get("paid_at"):
        msg += f"• Thanh toán lúc: `{order['paid_at']}`\n"
    if order.get("delivered_data"):
        msg += f"\n🔑 **DỮ LIỆU TÀI KHOẢN:**\n```\n{order['delivered_data']}\n```\n"
    if order.get("error_message") and user.id == ADMIN_TELEGRAM_ID:
        msg += f"\n⚠️ **Ghi chú lỗi:** `{order['error_message']}`\n"
    msg += "━━━━━━━━━━━━━━━━━━"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /orders xem danh sách đơn hàng (khách xem đơn của mình, admin xem toàn shop)"""
    user = update.effective_user
    if user.id == ADMIN_TELEGRAM_ID:
        total_orders = await database.count_all_orders()
        orders = await database.get_all_orders_admin(limit=5, offset=0)
        total_pages = max(1, math.ceil(total_orders / 5))

        if not orders:
            await update.message.reply_text("📦 Hiện tại chưa có đơn hàng nào trong hệ thống.")
            return

        msg = f"📦 **LỊCH SỬ ĐƠN HÀNG TOÀN SHOP** (Trang 1/{total_pages})\n"
        msg += f"Tổng cộng: `{total_orders}` đơn hàng\n━━━━━━━━━━━━━━━━━━\n"

        action_buttons = []
        for o in orders:
            status_icon = "✅" if o["status"] == "COMPLETED" else "⏳" if o["status"] == "PENDING" else "❌"
            user_label = f"@{o['username']}" if o.get("username") else (o.get("full_name") or f"ID:{o['user_id']}")
            msg += (
                f"{status_icon} **#{o['order_code']}** — {o['product_name'][:28]}\n"
                f"• Khách: {user_label} (ID: `{o['user_id']}`)\n"
                f"• Tiền thu: `{o['sell_price_vnd']:,}đ` | Lãi: `+{o['profit_vnd']:,}đ`\n"
                f"• Giờ tạo: `{o['created_at']}` | TT: `{o['status']}`\n"
                f"──────────────────\n"
            )
            action_buttons.append([InlineKeyboardButton(f"🔍 Xem #{o['order_code']} ({o['status']})", callback_data=f"admin_view_{o['order_code']}")])

        nav_buttons = [InlineKeyboardButton(f"📄 1/{total_pages}", callback_data="noop")]
        if total_orders > 5:
            nav_buttons.append(InlineKeyboardButton("Sau ➡️", callback_data="admin_orders_5"))

        keyboard = action_buttons + [nav_buttons, [InlineKeyboardButton("👑 Bảng Quản Trị", callback_data="admin_dashboard")]]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        orders = await database.get_user_orders(user.id, limit=5)
        if not orders:
            await update.message.reply_text(
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
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /stats xem báo cáo thống kê doanh thu (chỉ Admin)"""
    user = update.effective_user
    if user.id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Lệnh này chỉ dành cho Admin của shop!")
        return

    stats = await database.get_admin_detailed_stats()
    all_time = stats["all_time"]
    today = stats["today"]
    last_7 = stats["last_7_days"]
    top_prods = stats["top_products"]

    total_orders = all_time["total_orders"]
    success_rate = (all_time["completed"] / total_orders * 100) if total_orders > 0 else 0

    admin_text = (
        "📊 **BÁO CÁO DOANH THU & HIỆU SUẤT KINH DOANH**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📅 **HÔM NAY:**\n"
        f"• Đơn hoàn tất: `{today['completed']}/{today['total']}` đơn\n"
        f"• Doanh thu: `{today['revenue']:,} VNĐ`\n"
        f"• Lợi nhuận ròng (+20%): `+{today['profit']:,} VNĐ`\n\n"
        "🗓 **7 NGÀY GẦN NHẤT:**\n"
        f"• Đơn hoàn tất: `{last_7['completed']}/{last_7['total']}` đơn\n"
        f"• Doanh thu: `{last_7['revenue']:,} VNĐ`\n"
        f"• Lợi nhuận ròng (+20%): `+{last_7['profit']:,} VNĐ`\n\n"
        "🏆 **TOÀN THỜI GIAN (ALL-TIME):**\n"
        f"• Tổng đơn hàng: `{total_orders}` đơn\n"
        f"  ↳ ✅ Hoàn tất: `{all_time['completed']}` | ⏳ Đang chờ: `{all_time['pending']}` | ❌ Lỗi: `{all_time['failed']}`\n"
        f"• Tỷ lệ giao thành công: `{success_rate:.1f}%`\n"
        f"• Tổng doanh thu: `{all_time['revenue']:,} VNĐ`\n"
        f"• 💰 **TỔNG LỢI NHUẬN RÒNG: `+{all_time['profit']:,} VNĐ`**\n\n"
        "👥 **KHÁCH HÀNG:**\n"
        f"• Tổng tài khoản đã truy cập bot: `{stats['total_users']}` người\n"
        f"• Khách hàng đã phát sinh mua: `{stats['active_buyers']}` người\n"
    )
    if top_prods:
        admin_text += "\n🔥 **TOP SẢN PHẨM BÁN CHẠY NHẤT:**\n"
        for idx, tp in enumerate(top_prods, 1):
            admin_text += f"{idx}. {tp['product_name']}: `{tp['count']}` đơn (Lãi: `+{tp['sum_profit']:,}đ`)\n"
    admin_text += "━━━━━━━━━━━━━━━━━━"

    buttons = [
        [
            InlineKeyboardButton("🔄 Làm Mới", callback_data="admin_stats"),
            InlineKeyboardButton("📦 Xem Danh Sách Đơn", callback_data="admin_orders_0")
        ],
        [InlineKeyboardButton("👑 Về Bảng Quản Trị", callback_data="admin_dashboard")]
    ]
    await update.message.reply_text(admin_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /balance kiểm tra số dư ví USDT bot nguồn (chỉ Admin)"""
    user = update.effective_user
    if user.id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Lệnh này chỉ dành cho Admin của shop!")
        return

    supplier = get_supplier()
    bal_info = await supplier.get_balance()
    balance_val = bal_info.get("balance", 0.0)
    balance_text = bal_info.get("balanceText", f"{balance_val:.2f} USDT")

    if balance_val >= 5.0:
        status_note = "🟢 **Số dư dồi dào!** Hệ thống hoàn toàn sẵn sàng tự động mua và giao tài khoản ngay khi có khách thanh toán."
    elif balance_val > 0.0:
        status_note = "🟡 **Số dư còn ít!** Bạn nên nạp thêm USDT vào bot nguồn để tránh bị gián đoạn đơn hàng."
    else:
        status_note = "🔴 **Số dư ví đang là 0.00 USDT!**\nKhi khách chuyển tiền, bot vẫn lưu đơn nhưng sẽ tạm dừng xuất hàng tự động cho đến khi bạn nạp thêm USDT."

    msg = (
        "💰 **SỐ DƯ VÍ NGUỒN (@SupremeLeaderShopBot)**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💵 Số dư ví hiện tại: `{balance_text}`\n\n"
        f"{status_note}\n\n"
        "📌 **Hướng dẫn nạp USDT vào kho nguồn:**\n"
        "1. Mở bot @SupremeLeaderShopBot\n"
        "2. Bấm vào nút `💼 Wallet` hoặc `Deposit`.\n"
        "3. Chọn nạp qua USDT (TRC20 / TON / BEP20) với số tiền mong muốn (ví dụ 10$ - 20$).\n"
        "4. Bot nguồn sẽ tự động trừ dần tiền trong ví mỗi khi có khách mua trên bot của bạn!\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    buttons = [
        [InlineKeyboardButton("🔄 Kiểm Tra Lại", callback_data="admin_balance")],
        [InlineKeyboardButton("👑 Về Bảng Quản Trị", callback_data="admin_dashboard")]
    ]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def policy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /policy xem chính sách bán hàng & bảo hành"""
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
    await update.message.reply_text(policy_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /support xem hỗ trợ kỹ thuật"""
    support_text, keyboard = get_support_text_and_markup()
    await update.message.reply_text(support_text, reply_markup=keyboard, parse_mode="Markdown")

async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /sync dành cho Admin để quét lại sản phẩm từ bot nguồn bất kỳ lúc nào"""
    user = update.effective_user
    if user.id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Lệnh này chỉ dành cho Admin!")
        return

    msg = await update.message.reply_text("⏳ Đang cào toàn bộ sản phẩm thực tế từ bot nguồn...")
    try:
        supplier = get_supplier()
        products = await supplier.fetch_products()
        await database.sync_products(products)
        await msg.edit_text(
            f"✅ **ĐỒNG BỘ THÀNH CÔNG!**\n\n"
            f"• Đã nạp `{len(products)}` sản phẩm trực tiếp từ bot nguồn vào cơ sở dữ liệu.\n"
            f"• Giá bán tự động cộng +20% lãi ròng.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Lỗi khi đồng bộ: {str(e)}")

async def sync_supplier_catalog():
    """Hàm tải sản phẩm từ nhà cung cấp và nạp vào DB"""
    supplier = get_supplier()
    logger.info(f"Đang đồng bộ sản phẩm từ nhà cung cấp {supplier.__class__.__name__}...")
    products = await supplier.fetch_products()
    await database.sync_products(products)
    logger.info(f"Đã đồng bộ {len(products)} sản phẩm vào cơ sở dữ liệu.")

async def setup_bot_commands(bot):
    """Thiết lập menu lệnh gợi ý nhanh (Bot Commands Menu) trên giao diện chat Telegram"""
    try:
        # Danh sách lệnh cho khách hàng thông thường
        user_commands = [
            BotCommand("start", "🛒 Mở menu mua tài khoản & dịch vụ"),
            BotCommand("orders", "📦 Lịch sử đơn hàng của tôi"),
            BotCommand("order", "🔍 Tra cứu đơn hàng (/order mã_đơn)"),
            BotCommand("policy", "ℹ️ Chính sách bảo hành & lưu ý"),
            BotCommand("support", "📞 Hỗ trợ kỹ thuật 24/7"),
        ]
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

        # Danh sách lệnh nâng cao dành riêng cho Admin
        if ADMIN_TELEGRAM_ID:
            admin_commands = [
                BotCommand("admin", "👑 Bảng điều khiển quản trị shop"),
                BotCommand("stats", "📊 Báo cáo doanh thu & lợi nhuận"),
                BotCommand("orders", "📦 Lịch sử đơn hàng toàn shop"),
                BotCommand("balance", "💰 Kiểm tra số dư ví bot nguồn"),
                BotCommand("sync", "🔄 Quét & đồng bộ kho hàng mới"),
                BotCommand("order", "🔍 Tra cứu đơn hàng (/order mã_đơn)"),
                BotCommand("start", "🛒 Mở menu mua hàng"),
            ]
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=ADMIN_TELEGRAM_ID)
            )

        # Kích hoạt nút Menu lệnh cạnh khung chat
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("✅ Đã thiết lập danh sách lệnh nhanh (Bot Commands Menu) thành công.")
    except Exception as e:
        logger.warning(f"Lỗi khi thiết lập Bot Commands Menu: {e}")

async def post_init(application: Application):
    await setup_bot_commands(application.bot)

def build_application() -> Application:
    """Tạo Application của python-telegram-bot"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN chưa được cung cấp trong cấu hình!")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Đăng ký các Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("orders", orders_command))
    app.add_handler(CommandHandler("order", order_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("policy", policy_command))
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("sync", sync_command))

    # Đăng ký Callback Query Handler
    app.add_handler(CallbackQueryHandler(handle_callback))
    return app
