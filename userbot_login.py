import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

# Nhập API ID và API HASH từ my.telegram.org
API_ID = int(input("Nhập API_ID từ my.telegram.org: "))
API_HASH = input("Nhập API_HASH từ my.telegram.org: ").strip()

async def main():
    # Sử dụng StringSession để tạo ra một chuỗi text lưu trữ đăng nhập vĩnh viễn
    # không sợ bị mất file khi chuyển server
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()

    session_string = client.session.save()
    print("\n" + "="*50)
    print("✅ ĐĂNG NHẬP THÀNH CÔNG!")
    print("Dưới đây là USERBOT_SESSION_STRING của bạn:")
    print("="*50)
    print(session_string)
    print("="*50)
    print("👉 Hãy copy chuỗi trên dán vào biến USERBOT_SESSION_STRING trong file .env\n")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
