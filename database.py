import aiosqlite
import logging
from datetime import datetime
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

async def init_db():
    """Khởi tạo các bảng cơ sở dữ liệu nếu chưa tồn tại"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                supplier_id TEXT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                cost_price_vnd INTEGER NOT NULL,
                sell_price_vnd INTEGER NOT NULL,
                profit_vnd INTEGER NOT NULL,
                in_stock INTEGER DEFAULT 1,
                stock_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_code TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                cost_price_vnd INTEGER NOT NULL,
                sell_price_vnd INTEGER NOT NULL,
                profit_vnd INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                status TEXT DEFAULT 'PENDING',
                delivered_data TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code TEXT,
                gateway TEXT,
                amount INTEGER,
                content TEXT,
                raw_payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tự động cập nhật cấu trúc bảng nếu database đã tồn tại từ trước (Migration)
        try:
            await db.execute("ALTER TABLE products ADD COLUMN stock_count INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE orders ADD COLUMN quantity INTEGER DEFAULT 1")
        except Exception:
            pass

        await db.commit()
    logger.info("Cơ sở dữ liệu SQLite đã được khởi tạo thành công.")

async def register_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name
        """, (user_id, username, full_name))
        await db.commit()

async def sync_products(products: list[dict]):
    """Đồng bộ danh sách sản phẩm từ nhà cung cấp vào DB với giá bán = giá gốc + 20%"""
    if not products:
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Xóa các sản phẩm cũ/mock/test không còn nằm trong danh mục mới của nhà cung cấp
        product_ids = [p["id"] for p in products]
        placeholders = ",".join("?" for _ in product_ids)
        await db.execute(f"DELETE FROM products WHERE id NOT IN ({placeholders})", product_ids)

        for p in products:
            stock = int(p.get("stock_count", 0))
            in_stock = 1 if (p.get("in_stock", True) and stock > 0) else 0
            await db.execute("""
                INSERT INTO products (
                    id, supplier_id, name, category, description,
                    cost_price_vnd, sell_price_vnd, profit_vnd, in_stock, stock_count, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    supplier_id=excluded.supplier_id,
                    name=excluded.name,
                    category=excluded.category,
                    description=excluded.description,
                    cost_price_vnd=excluded.cost_price_vnd,
                    sell_price_vnd=excluded.sell_price_vnd,
                    profit_vnd=excluded.profit_vnd,
                    in_stock=excluded.in_stock,
                    stock_count=excluded.stock_count,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                p["id"],
                p.get("supplier_id", p["id"]),
                p["name"],
                p.get("category", "General"),
                p.get("description", ""),
                p["cost_price_vnd"],
                p["sell_price_vnd"],
                p["profit_vnd"],
                in_stock,
                stock
            ))
        await db.commit()

async def get_categories() -> list[str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT DISTINCT category FROM products") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_products_by_category(category: str) -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE category = ? ORDER BY in_stock DESC, name ASC", (category,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_product(product_id: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def create_order(
    order_code: str,
    user_id: int,
    product_id: str,
    product_name: str,
    cost_price: int,
    sell_price: int,
    profit: int,
    quantity: int = 1
) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO orders (
                order_code, user_id, product_id, product_name,
                cost_price_vnd, sell_price_vnd, profit_vnd, quantity, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (order_code, user_id, product_id, product_name, cost_price, sell_price, profit, quantity))
        await db.commit()
        return True

async def get_order(order_code: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE order_code = ?", (order_code,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_order_status(order_code: str, status: str, delivered_data: str = None, error_message: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if status == "PAID":
            await db.execute("""
                UPDATE orders SET status = ?, paid_at = CURRENT_TIMESTAMP WHERE order_code = ?
            """, (status, order_code))
        elif status == "COMPLETED":
            await db.execute("""
                UPDATE orders SET status = ?, delivered_data = ? WHERE order_code = ?
            """, (status, delivered_data, order_code))
        elif status == "FAILED_SUPPLIER":
            await db.execute("""
                UPDATE orders SET status = ?, error_message = ? WHERE order_code = ?
            """, (status, error_message, order_code))
        else:
            await db.execute("""
                UPDATE orders SET status = ? WHERE order_code = ?
            """, (status, order_code))
        await db.commit()

async def get_user_orders(user_id: int, limit: int = 5) -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def record_transaction(order_code: str, gateway: str, amount: int, content: str, raw_payload: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO transactions (order_code, gateway, amount, content, raw_payload)
            VALUES (?, ?, ?, ?, ?)
        """, (order_code, gateway, amount, content, raw_payload))
        await db.commit()

async def get_statistics() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status = 'COMPLETED'") as c1:
            completed_orders = (await c1.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(sell_price_vnd), 0), COALESCE(SUM(profit_vnd), 0) FROM orders WHERE status = 'COMPLETED'") as c2:
            row = await c2.fetchone()
            total_revenue = row[0]
            total_profit = row[1]
        async with db.execute("SELECT COUNT(*) FROM users") as c3:
            total_users = (await c3.fetchone())[0]
        return {
            "completed_orders": completed_orders,
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "total_users": total_users
        }

async def get_admin_detailed_stats() -> dict:
    """Báo cáo thống kê toàn diện cho Admin: Toàn thời gian, Hôm nay, 7 ngày qua, Tỷ lệ đơn & Top bán chạy"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 1. Toàn thời gian (All-Time)
        async with db.execute("""
            SELECT
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_orders,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending_orders,
                SUM(CASE WHEN status LIKE 'FAILED%' THEN 1 ELSE 0 END) as failed_orders,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN sell_price_vnd ELSE 0 END), 0) as total_revenue,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN profit_vnd ELSE 0 END), 0) as total_profit
            FROM orders
        """) as c:
            row = await c.fetchone()
            all_time = {
                "total_orders": row[0] or 0,
                "completed": row[1] or 0,
                "pending": row[2] or 0,
                "failed": row[3] or 0,
                "revenue": row[4] or 0,
                "profit": row[5] or 0,
            }

        # 2. Hôm nay (Dựa vào giờ địa phương)
        async with db.execute("""
            SELECT
                COUNT(*) as today_orders,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN sell_price_vnd ELSE 0 END), 0) as revenue,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN profit_vnd ELSE 0 END), 0) as profit
            FROM orders
            WHERE DATE(created_at, 'localtime') = DATE('now', 'localtime')
               OR DATE(paid_at, 'localtime') = DATE('now', 'localtime')
        """) as c:
            row = await c.fetchone()
            today = {
                "total": row[0] or 0,
                "completed": row[1] or 0,
                "revenue": row[2] or 0,
                "profit": row[3] or 0,
            }

        # 3. 7 ngày gần nhất
        async with db.execute("""
            SELECT
                COUNT(*) as week_orders,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN sell_price_vnd ELSE 0 END), 0) as revenue,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN profit_vnd ELSE 0 END), 0) as profit
            FROM orders
            WHERE created_at >= DATETIME('now', '-7 days')
               OR paid_at >= DATETIME('now', '-7 days')
        """) as c:
            row = await c.fetchone()
            last_7_days = {
                "total": row[0] or 0,
                "completed": row[1] or 0,
                "revenue": row[2] or 0,
                "profit": row[3] or 0,
            }

        # 4. Người dùng & Khách mua hàng thực tế
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total_users = (await c.fetchone())[0] or 0
        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM orders WHERE status = 'COMPLETED'") as c:
            active_buyers = (await c.fetchone())[0] or 0

        # 5. Top 3 sản phẩm bán chạy nhất
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT product_name, COUNT(*) as count, SUM(profit_vnd) as sum_profit
            FROM orders
            WHERE status = 'COMPLETED'
            GROUP BY product_name
            ORDER BY count DESC
            LIMIT 3
        """) as c:
            rows = await c.fetchall()
            top_products = [dict(r) for r in rows]

        return {
            "all_time": all_time,
            "today": today,
            "last_7_days": last_7_days,
            "total_users": total_users,
            "active_buyers": active_buyers,
            "top_products": top_products
        }

async def get_all_orders_admin(limit: int = 6, offset: int = 0) -> list[dict]:
    """Lấy danh sách đơn hàng toàn shop kèm tên khách hàng cho Admin"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT o.*, u.username, u.full_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def count_all_orders() -> int:
    """Đếm tổng số đơn hàng trong toàn bộ hệ thống"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
            return (await cursor.fetchone())[0] or 0

async def get_order_detail_full(order_code: str) -> dict | None:
    """Lấy đầy đủ chi tiết đơn hàng: tài khoản đã giao, log lỗi, giao dịch ngân hàng"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT o.*, u.username, u.full_name, t.gateway, t.content as bank_content, t.created_at as trans_time
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            LEFT JOIN transactions t ON o.order_code = t.order_code
            WHERE o.order_code = ?
        """, (order_code,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def search_orders_admin(keyword: str, limit: int = 5) -> list[dict]:
    """Tìm kiếm đơn hàng theo mã đơn, username hoặc ID khách hàng"""
    clean_kw = keyword.strip().lstrip("#")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT o.*, u.username, u.full_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.order_code LIKE ?
               OR CAST(o.user_id AS TEXT) LIKE ?
               OR u.username LIKE ?
            ORDER BY o.created_at DESC
            LIMIT ?
        """, (f"%{clean_kw}%", f"%{clean_kw}%", f"%{clean_kw}%", limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

