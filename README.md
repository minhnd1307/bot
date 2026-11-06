# 🤖 TELEGRAM BOT DROPSHIPPING & ARBITRAGE TỰ ĐỘNG 100%

Hệ thống Telegram Bot bán tài khoản số (**ChatGPT Plus, Google Gemini Advanced 2TB, YouTube Premium, Netflix 4K...**) tự động mua hàng từ nguồn sỉ khi có khách đặt và tự động ăn chênh lệch **20% lợi nhuận**.

---

## 📌 1. BẢNG TỔNG HỢP NGUỒN HÀNG CÓ API UY TÍN NHẤT HIỆN NAY

| Tên Sàn / Nguồn | Loại API | Sản Phẩm Mạnh Nhất | Ưu Điểm | Nhược Điểm |
| :--- | :--- | :--- | :--- | :--- |
| **LZT Market (Lolzteam)**<br>`lzt.market` / `lolz.live` | REST API<br>(Fast-Buy Endpoint) | **ChatGPT Plus, OpenAI Token, Google, Mail, Steam** | Giá sỉ rẻ nhất thế giới. Trả thông tin tài khoản qua API chỉ sau 1 giây. | Nạp tiền bằng Crypto (USDT, TON) hoặc thẻ quốc tế. |
| **Plati.Market (Digiseller)**<br>`plati.market` | REST API (Digiseller) | **YouTube Premium gia hạn, Netflix, Key phần mềm** | Nguồn bản quyền uy tín lâu năm, bảo hành tốt. | Giá cao hơn LZT một chút, cần tạo tài khoản đại lý. |
| **Tạp Hóa MMO**<br>`taphoammo.net` | REST API | **ChatGPT, Gemini, YouTube, Canva, Proxy** | Nguồn Việt Nam, thanh toán trực tiếp bằng VNĐ, hỗ trợ tiếng Việt. | Đôi khi các gian hàng bị hết hàng đột ngột. |
| **AccsMarket**<br>`accsmarket.com` | REST API | **Tài khoản AI, Gmail cổ, Social** | Kho Gmail và Social khổng lồ để tự reg tài khoản AI. | Giá niêm yết theo USD. |
| **Bot Telegram Bán Lẻ Khác** | *Không có REST API* | Đa dạng | Đơn giản nếu bạn đã quen mua từ một bot cụ thể. | Phải dùng **Userbot (Pyrogram)** để tự động bấm nút, dễ bị chặn spam nếu thao tác quá nhanh. |

---

## ⚡ 2. LUỒNG HOẠT ĐỘNG TỰ ĐỘNG 100%

```
[Khách Hàng] 
      │ (1) Mở Bot Telegram -> Chọn sản phẩm (VD: ChatGPT Plus 180.000đ)
      ▼
[Telegram Bot] 
      │ (2) Tạo mã đơn DH849201 -> Sinh ảnh VietQR có sẵn số tiền & nội dung
      ▼
[Khách Hàng Chuyển Khoản VietQR]
      │ (3) Quét mã QR chuyển 180.000đ vào tài khoản ngân hàng của bạn
      ▼
[Cổng SePay] 
      │ (4) Ngân hàng báo biến động số dư -> SePay bắn Webhook về Server Bot
      ▼
[Hệ Thống Tự Động Xử Lý (Fulfillment)]
      │ (5) Kiểm tra đúng tiền & mã đơn -> Gọi API sàn nguồn (LZT/Plati/Taphoammo)
      │     -> Mua tài khoản với giá vốn (150.000đ)
      ▼
[Bàn Giao Tự Động]
      │ (6) Bot tự động gửi Email & Password cho Khách Hàng trong Telegram
      │ (7) Bot gửi tin nhắn báo doanh thu cho Admin: "+30.000đ LÃI RÒNG (+20%)"
```

---

## 🚀 3. HƯỚNG DẪN CÀI ĐẶT & CHẠY

### Bước 1: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 2: Cấu hình thông tin vào file `.env`
Mở file `.env` và điền:
1. `TELEGRAM_BOT_TOKEN`: Lấy từ `@BotFather` trên Telegram.
2. `ADMIN_TELEGRAM_ID`: Lấy ID của bạn từ bot `@userinfobot` để nhận thông báo tiền về.
3. `BANK_ID`: Tên ngân hàng (ví dụ: `MBBank`, `VCB`, `ACB`, `TPBank`...).
4. `BANK_ACCOUNT_NO`: Số tài khoản ngân hàng của bạn.
5. `BANK_ACCOUNT_NAME`: Tên chủ tài khoản (viết hoa không dấu).
6. `SUPPLIER_TYPE`:
   - `mock`: Chế độ giả lập thử nghiệm (tự sinh tài khoản để test toàn bộ luồng mà không tốn tiền).
   - `lzt`: Chế độ kết nối sàn quốc tế LZT Market.
   - `taphoammo`: Chế độ kết nối sàn Tạp Hóa MMO.

### Bước 3: Khởi chạy bot
```bash
python run.py
```

---

## 🧪 4. CÁCH TEST THỬ NGHIỆM MIỄN PHÍ KHÔNG CẦN CHUYỂN TIỀN THẬT

Hệ thống có sẵn cổng test nội bộ cực kỳ tiện lợi:
1. Bật bot lên và chat `/start`.
2. Bấm **🛒 Mua Tài Khoản** -> Chọn **ChatGPT Plus** -> Bấm **⚡ MUA NGAY**.
3. Bot sẽ xuất ra mã đơn hàng, ví dụ: `#DH123456`.
4. Mở trình duyệt web và truy cập vào link test:
   ```
   http://localhost:8000/api/test-pay/DH123456
   ```
5. Ngay lập tức:
   - Server kích hoạt thanh toán thành công.
   - Bot lập tức gửi tài khoản ChatGPT Plus vào Telegram của bạn.
   - Bot báo tin nhắn thông báo cho Admin về lợi nhuận +20%!

---

## 🌐 5. CẤU HÌNH NHẬN TIỀN THẬT QUA SEPAY (VIETQR TỰ ĐỘNG)

1. Đăng ký tài khoản miễn phí tại [sepay.vn](https://sepay.vn).
2. Kết nối tài khoản ngân hàng của bạn (MBBank, Vietcombank, ACB...).
3. Dùng công cụ đưa port localhost ra ngoài Internet như **Cloudflare Tunnel** hoặc **ngrok**:
   ```bash
   # Nếu dùng ngrok:
   ngrok http 8000
   ```
4. Lấy link Forwarding (ví dụ: `https://xxxx.ngrok-free.app`) dán vào mục **Webhooks** trên SePay:
   - URL Webhook: `https://xxxx.ngrok-free.app/api/sepay/webhook`
5. Khi khách hàng chuyển khoản tiền thật, tiền về trực tiếp tài khoản ngân hàng của bạn, và bot sẽ tự động giao tài khoản trong 1-3 giây!
# bot
