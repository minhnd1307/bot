import asyncio
import random
import uuid
from suppliers.base import BaseSupplier

class MockSupplier(BaseSupplier):
    """
    Nhà cung cấp Giả Lập (Sandbox).
    Dùng để kiểm thử toàn bộ quy trình: chọn hàng -> tạo QR -> thanh toán -> tự động nhận hàng
    ngay lập tức mà không cần nạp tiền thật vào sàn nguồn.
    """

    def __init__(self):
        self.catalog = [
            {
                "id": "chatgpt_plus_1m",
                "supplier_id": "mock_gpt_01",
                "name": "ChatGPT Plus (1 Tháng - Tài khoản riêng)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Tài khoản OpenAI có sẵn gói ChatGPT Plus (GPT-4o, Canvas, DALL-E). Bảo hành 30 ngày 1 đổi 1.",
                "cost_price_vnd": 150000,
            },
            {
                "id": "chatgpt_team_1m",
                "supplier_id": "mock_gpt_02",
                "name": "ChatGPT Team Workspace (1 Tháng)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Slot tham gia Workspace ChatGPT Team, không giới hạn GPT-4o, bảo mật dữ liệu không bị đem đi train.",
                "cost_price_vnd": 80000,
            },
            {
                "id": "gemini_advanced_1m",
                "supplier_id": "mock_gem_01",
                "name": "Google Gemini Advanced (1 Tháng - Kèm 2TB Google One)",
                "category": "🤖 AI (ChatGPT / Gemini)",
                "description": "Tài khoản Google mới có sẵn gói Google One AI Premium 2TB + Gemini 1.5 Pro Ultra. Bảo hành trọn tháng.",
                "cost_price_vnd": 95000,
            },
            {
                "id": "youtube_prem_6m",
                "supplier_id": "mock_yt_01",
                "name": "YouTube Premium (6 Tháng - Mời Gia Đình)",
                "category": "🎵 Giải Trí (YouTube / Netflix)",
                "description": "Nâng cấp chính chủ email của bạn qua Google Family. Xem không quảng cáo, nghe nhạc tắt màn hình.",
                "cost_price_vnd": 110000,
            },
            {
                "id": "youtube_prem_12m",
                "supplier_id": "mock_yt_02",
                "name": "YouTube Premium (12 Tháng - 1 Năm)",
                "category": "🎵 Giải Trí (YouTube / Netflix)",
                "description": "Gói 1 năm xem video không quảng cáo, YouTube Music bản quyền. Bảo hành suốt 365 ngày.",
                "cost_price_vnd": 210000,
            },
            {
                "id": "netflix_extra_1m",
                "supplier_id": "mock_net_01",
                "name": "Netflix Premium 4K UltraHD (1 Tháng)",
                "category": "🎵 Giải Trí (YouTube / Netflix)",
                "description": "Profile riêng biệt, có mã PIN, xem mượt mà trên TV, điện thoại, máy tính.",
                "cost_price_vnd": 65000,
            }
        ]

    async def fetch_products(self) -> list[dict]:
        products = []
        for item in self.catalog:
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
        """Giả lập gọi API mua hàng và trả thông tin tài khoản sau 1 giây"""
        await asyncio.sleep(1.0) # Giả lập độ trễ mạng API

        matching = next((p for p in self.catalog if p["id"] == product_id), None)
        if not matching:
            return {
                "success": False,
                "delivered_data": "",
                "cost_price_vnd": 0,
                "error": f"Không tìm thấy sản phẩm có mã {product_id} trên kho nguồn."
            }

        rand_id = random.randint(1000, 9999)
        temp_pass = f"Pass@{uuid.uuid4().hex[:8].capitalize()}!"

        if "chatgpt" in product_id:
            delivered_info = (
                f"✅ **TÀI KHOẢN CHATGPT PLUS BÀN GIAO TỰ ĐỘNG**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📧 **Email:** `buyer_ai_{rand_id}@proton.me`\n"
                f"🔑 **Mật khẩu:** `{temp_pass}`\n"
                f"🔐 **Mail khôi phục (nếu có):** `recovery_{rand_id}@mail.tm`\n"
                f"🌐 **Đăng nhập tại:** https://chatgpt.com\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 **Lưu ý sử dụng:**\n"
                f"- Vui lòng đăng nhập và kiểm tra gói Plus ngay sau khi nhận.\n"
                f"- Khuyến nghị đổi mật khẩu mail sau khi nhận tài khoản.\n"
                f"- Bảo hành 1 đổi 1 trong suốt thời gian sử dụng nếu có lỗi từ hệ thống."
            )
        elif "gemini" in product_id:
            delivered_info = (
                f"✅ **TÀI KHOẢN GEMINI ADVANCED BÀN GIAO TỰ ĐỘNG**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📧 **Tài khoản Google:** `gemini_user_{rand_id}@gmail.com`\n"
                f"🔑 **Mật khẩu:** `{temp_pass}`\n"
                f"🌐 **Truy cập:** https://gemini.google.com\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 **Lưu ý sử dụng:**\n"
                f"- Tài khoản có sẵn 2TB lưu trữ Google One.\n"
                f"- Không vi phạm chính sách nội dung của Google."
            )
        elif "youtube" in product_id:
            invite_code = uuid.uuid4().hex[:12]
            delivered_info = (
                f"✅ **GÓI YOUTUBE PREMIUM BÀN GIAO TỰ ĐỘNG**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔗 **Link mời tham gia nhóm gia đình Google:**\n"
                f"https://families.google.com/join/{invite_code}\n\n"
                f"📌 **Hướng dẫn kích hoạt:**\n"
                f"1. Nhấp vào đường link trên bằng tài khoản Google bạn muốn nâng cấp.\n"
                f"2. Bấm 'Tham gia gia đình'.\n"
                f"3. Mở YouTube kiểm tra logo 'Premium' ở góc trên cùng bên trái."
            )
        else:
            delivered_info = (
                f"✅ **THÔNG TIN TÀI KHOẢN BÀN GIAO**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📧 **Username/Email:** `service_user_{rand_id}@domain.com`\n"
                f"🔑 **Password:** `{temp_pass}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 **Bảo hành:** Vui lòng giữ thông tin này để được hỗ trợ khi cần."
            )

        return {
            "success": True,
            "delivered_data": delivered_info,
            "cost_price_vnd": matching["cost_price_vnd"],
            "error": None
        }
