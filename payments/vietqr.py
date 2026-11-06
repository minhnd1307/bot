import io
import urllib.parse
import qrcode
from config import BANK_ID, BANK_ACCOUNT_NO, BANK_ACCOUNT_NAME

def get_vietqr_image_url(amount: int, order_code: str) -> str:
    """
    Tạo link ảnh VietQR chuẩn theo định dạng ngân hàng Việt Nam.
    Tự động điền số tài khoản, tên ngân hàng, số tiền và nội dung chuyển khoản.
    """
    encoded_name = urllib.parse.quote(BANK_ACCOUNT_NAME)
    encoded_info = urllib.parse.quote(order_code)
    # Dùng template compact2 đẹp và gọn gàng của VietQR
    return f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT_NO}-compact2.png?amount={amount}&addInfo={encoded_info}&accountName={encoded_name}"

def generate_local_qr_bytes(amount: int, order_code: str) -> bytes:
    """Tạo ảnh QR dạng bytes dự phòng nếu không dùng được link ngoài"""
    qr_data = f"2|99|{BANK_ACCOUNT_NO}|{BANK_ACCOUNT_NAME}||0|0|{amount}|{order_code}|transfer"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()
