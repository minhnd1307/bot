import os
import re
import subprocess
import sys

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

def update_env():
    print("=" * 55)
    print("🤖 CÔNG CỤ CẬP NHẬT CẤU HÌNH USERBOT VÀO .ENV")
    print("=" * 55)

    api_id = input("1. Nhập USERBOT_API_ID: ").strip()
    api_hash = input("2. Nhập USERBOT_API_HASH: ").strip()
    session = input("3. Nhập USERBOT_SESSION_STRING: ").strip()
    target_bot = input("4. Nhập tên bot nguồn (Enter để mặc định SupremeLeaderShopBot): ").strip()
    if not target_bot:
        target_bot = "SupremeLeaderShopBot"

    if not api_id or not api_hash or not session:
        print("\n❌ Lỗi: Bạn chưa nhập đủ thông tin. Vui lòng chạy lại!")
        sys.exit(1)

    # Đọc nội dung file .env hiện tại
    content = ""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            content = f.read()

    # Bảng các giá trị cần ghi đè hoặc bổ sung
    updates = {
        "SUPPLIER_TYPE": "userbot",
        "USERBOT_API_ID": api_id,
        "USERBOT_API_HASH": api_hash,
        "USERBOT_SESSION_STRING": session,
        "TARGET_BOT_USERNAME": target_bot
    }

    for key, value in updates.items():
        pattern = rf"^{key}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, content, flags=re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content += f"\n{replacement}"

    # Ghi lại vào file .env
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

    print("\n✅ Đã lưu cấu hình Userbot vào file .env thành công!")
    print("🔄 Đang khởi động lại Bot trên Google Cloud...")

    # Khởi động lại tiến trình
    try:
        subprocess.run(["pkill", "-9", "-f", "run.py"], stderr=subprocess.DEVNULL)
    except Exception:
        pass

    try:
        subprocess.Popen(
            ["nohup", "python3", "run.py"],
            stdout=open("bot.log", "a"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setpgrp if hasattr(os, "setpgrp") else None
        )
        print("🚀 Bot đã khởi động lại với nhà cung cấp Userbot!")
        print("👉 Bạn có thể gõ: tail -n 25 bot.log để xem trạng thái hoạt động.\n")
    except Exception as e:
        print(f"⚠️ Vui lòng chạy lệnh sau để bật bot: nohup python3 run.py > bot.log 2>&1 &")

if __name__ == "__main__":
    update_env()
