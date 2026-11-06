import io
import logging
import urllib.parse
import httpx
import qrcode
from config import BANK_ID, BANK_ACCOUNT_NO, BANK_ACCOUNT_NAME

logger = logging.getLogger(__name__)

# Bảng mã BIN Napas của các ngân hàng phổ biến tại Việt Nam
BANK_BIN_MAP = {
    "MBBANK": "970422", "MB": "970422",
    "VIETCOMBANK": "970436", "VCB": "970436",
    "TECHCOMBANK": "970407", "TCB": "970407",
    "ACB": "970416",
    "TPBANK": "970423", "TPB": "970423",
    "VPBANK": "970432", "VPB": "970432",
    "VIETINBANK": "970415", "CTG": "970415",
    "BIDV": "970418",
    "AGRIBANK": "970405", "VBA": "970405",
    "VIB": "970441",
    "SACOMBANK": "970403", "STB": "970403",
    "HDBANK": "970437", "HDB": "970437",
    "SHB": "970443",
    "MSB": "970426",
    "OCB": "970448",
    "SEABANK": "970440",
    "NAMABANK": "970428",
    "TIMO": "963388",
    "BVBANK": "970454",
}

def crc16_ccitt(data: str) -> str:
    """Tính checksum CRC16 chuẩn EMVCo của VietQR"""
    crc = 0xFFFF
    for ch in data.encode("utf-8"):
        crc = ((crc >> 8) | (crc << 8)) & 0xFFFF
        crc ^= ch
        crc ^= ((crc & 0xFF) >> 4)
        crc ^= ((crc << 12) & 0xFFFF)
        crc ^= (((crc & 0xFF) << 5) & 0xFFFF)
    return f"{crc:04X}"

def build_vietqr_emvco_payload(bank_bin: str, account_no: str, amount: int, order_code: str) -> str:
    """
    Sinh chuỗi dữ liệu chuẩn EMVCo của VietQR (Napas 247).
    Mọi App ngân hàng tại VN đều quét và tự động điền đúng STK, số tiền, nội dung.
    """
    res = "000201010212"
    sub01 = f"0006{bank_bin}01{len(account_no):02d}{account_no}"
    sub38 = f"0010A00000072701{len(sub01):02d}{sub01}0208QRIBFTTA"
    res += f"38{len(sub38):02d}{sub38}"
    res += "5303704" # Tiền tệ VND
    amt_str = str(amount)
    res += f"54{len(amt_str):02d}{amt_str}"
    res += "5802VN"
    sub62 = f"08{len(order_code):02d}{order_code}"
    res += f"62{len(sub62):02d}{sub62}"
    payload = res + "6304"
    crc = crc16_ccitt(payload)
    return payload + crc

def generate_local_qr_bytes(amount: int, order_code: str) -> bytes:
    """
    Tự động sinh ảnh QR PNG trực tiếp trên máy bằng chuẩn VietQR EMVCo.
    Không phụ thuộc bất kỳ API bên thứ ba nào, hoạt động 100% kể cả khi mất mạng ngoài.
    """
    bank_key = BANK_ID.upper().replace(" ", "").replace("_", "")
    bank_bin = BANK_BIN_MAP.get(bank_key, "970422")
    emv_payload = build_vietqr_emvco_payload(bank_bin, BANK_ACCOUNT_NO, amount, order_code)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(emv_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#101828", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

async def get_vietqr_image_bytes(amount: int, order_code: str) -> bytes:
    """
    Lấy dữ liệu ảnh PNG VietQR để gửi trực tiếp vào tin nhắn Telegram:
    1. Ưu tiên lấy ảnh có khung đẹp từ SePay QR Endpoint (định dạng PNG chuẩn)
    2. Nếu mạng ngoài chậm hoặc lỗi, tự động chuyển sang bộ sinh mã VietQR nội bộ
    """
    # 1. Thử lấy từ SePay QR Endpoint
    try:
        encoded_bank = urllib.parse.quote(BANK_ID)
        sepay_url = (
            f"https://qr.sepay.vn/img?"
            f"acc={BANK_ACCOUNT_NO}&bank={encoded_bank}&amount={amount}&des={order_code}&template=compact"
        )
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(sepay_url)
            if resp.status_code == 200 and resp.content[:8] == b"\x89PNG\r\n\x1a\n":
                return resp.content
    except Exception as e:
        logger.warning(f"Không lấy được ảnh SePay QR online ({e}), chuyển sang tạo offline...")

    # 2. Dự phòng: Sinh trực tiếp ảnh QR chuẩn VietQR trên máy
    return generate_local_qr_bytes(amount, order_code)

def get_vietqr_image_url(amount: int, order_code: str) -> str:
    """URL ảnh dự phòng theo định dạng SePay QR PNG trực tiếp"""
    encoded_bank = urllib.parse.quote(BANK_ID)
    return (
        f"https://qr.sepay.vn/img?"
        f"acc={BANK_ACCOUNT_NO}&bank={encoded_bank}&amount={amount}&des={order_code}&template=compact"
    )
