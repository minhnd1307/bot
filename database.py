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
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for p in products:
            await db.execute("""
                INSERT INTO products (
                    id, supplier_id, name, category, description,
                    cost_price_vnd, sell_price_vnd, profit_vnd, in_stock, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    supplier_id=excluded.supplier_id,
                    name=excluded.name,
                    category=excluded.category,
                    description=excluded.description,
                    cost_price_vnd=excluded.cost_price_vnd,
                    sell_price_vnd=excluded.sell_price_vnd,
                    profit_vnd=excluded.profit_vnd,
                    in_stock=excluded.in_stock,
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
                1 if p.get("in_stock", True) else 0
            ))
        await db.commit()

async def get_categories() -> list[str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT DISTINCT category FROM products WHERE in_stock = 1") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_products_by_category(category: str) -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE category = ? AND in_stock = 1", (category,)
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
    profit: int
) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO orders (
                order_code, user_id, product_id, product_name,
                cost_price_vnd, sell_price_vnd, profit_vnd, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (order_code, user_id, product_id, product_name, cost_price, sell_price, profit))
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
