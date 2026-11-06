#!/bin/bash
set -e

echo "=== [CI/CD] Bắt đầu triển khai code mới ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "1. Đang kéo mã nguồn mới nhất từ Git..."
git pull origin main

echo "2. Cài đặt / cập nhật các thư viện..."
pip3 install --user --break-system-packages -r requirements.txt

echo "3. Dừng tiến trình cũ..."
pkill -9 -f run.py || true
sleep 1

echo "4. Khởi chạy bot phiên bản mới..."
nohup python3 run.py > bot.log 2>&1 &

sleep 2
if pgrep -f "run.py" > /dev/null; then
    echo "========================================="
    echo "✅ DEPLOY THÀNH CÔNG! Bot đang chạy 24/7!"
    echo "========================================="
else
    echo "❌ Có lỗi xảy ra, xem lại bot.log:"
    tail -n 25 bot.log
    exit 1
fi
