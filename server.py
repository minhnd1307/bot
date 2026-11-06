import json
import re
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import database
from fulfillment import fulfill_order

logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram Bot Shop Webhook Server")

# Global reference to Telegram Bot instance (gắn vào khi khởi động)
telegram_bot_instance = None

def set_bot_instance(bot):
    global telegram_bot_instance
    telegram_bot_instance = bot

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Telegram Shop Webhook"}

@app.post("/api/sepay/webhook")
async def sepay_webhook(request: Request):
    """
    Endpoint tiếp nhận thông báo biến động số dư từ SePay (Ngân hàng Việt Nam).
    Khi khách hàng quét mã QR và chuyển khoản thành công, SePay bắn dữ liệu vào đây.
    """
    try:
        data = await request.json()
        logger.info(f"Nhận webhook SePay: {data}")
    except Exception as e:
        logger.error(f"Không thể parse JSON từ SePay webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Lấy các trường thông tin linh hoạt theo chuẩn SePay
    amount_in = float(data.get("transferAmount") or data.get("amountIn") or 0.0)
    content = str(data.get("content") or data.get("transactionContent") or "")
    gateway = str(data.get("gateway") or "Bank")

    # Tìm mã đơn hàng có dạng DHxxxxxx (Ví dụ: DH849201)
    match = re.search(r"DH\d{6}", content.upper())
    if not match:
        logger.warning(f"Không tìm thấy mã đơn hàng DH trong nội dung: '{content}'")
        return JSONResponse(status_code=200, content={"status": "ignored", "reason": "No order code found in content"})

    order_code = match.group(0)
    logger.info(f"Phát hiện thanh toán cho đơn hàng {order_code} với số tiền {amount_in} VNĐ")

    # Kiểm tra đơn hàng trong DB
    order = await database.get_order(order_code)
    if not order:
        logger.warning(f"Đơn hàng {order_code} không tồn tại trong hệ thống.")
        return JSONResponse(status_code=200, content={"status": "ignored", "reason": "Order not in database"})

    # Lưu log giao dịch vào DB
    await database.record_transaction(
        order_code=order_code,
        gateway=gateway,
        amount=int(amount_in),
        content=content,
        raw_payload=json.dumps(data, ensure_ascii=False)
    )

    # Kiểm tra số tiền chuyển có đủ không
    if amount_in < order["sell_price_vnd"]:
        logger.warning(f"Đơn {order_code} thiếu tiền: Khách chuyển {amount_in}, cần {order['sell_price_vnd']}")
        return JSONResponse(status_code=200, content={"status": "underpaid", "message": "Amount is less than required"})

    # Xử lý tự động giao hàng
    result = await fulfill_order(order_code, bot=telegram_bot_instance)

    return JSONResponse(status_code=200, content={"status": "success", "result": result})

@app.get("/api/test-pay/{order_code}")
async def test_pay_endpoint(order_code: str):
    """
    Endpoint hỗ trợ test tự động: Cho phép bạn giả lập thanh toán thành công 1 đơn hàng
    bằng cách mở link trình duyệt: http://localhost:8000/api/test-pay/DHxxxxxx
    rất tiện lợi khi test chưa cần chuyển khoản tiền thật!
    """
    order = await database.get_order(order_code.upper())
    if not order:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn hàng {order_code}")

    logger.info(f"[TEST MODE] Kích hoạt thanh toán giả lập cho đơn {order_code}")
    result = await fulfill_order(order_code.upper(), bot=telegram_bot_instance)
    return {"status": "success", "test_order": order_code, "fulfillment_result": result}
