import os
import asyncio
import aiosqlite
from datetime import datetime

DB_NAME = "bot_database.db"
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def _pg_query(query, params=(), fetch=None):
    """Вспомогательная функция для синхронных запросов в PostgreSQL"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetch == "one":
        res = cursor.fetchone()
    elif fetch == "all":
        res = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    return res


async def init_db():
    if DATABASE_URL:
        await asyncio.to_thread(_pg_query, """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                role TEXT DEFAULT 'viewer'
            );
        """)
        await asyncio.to_thread(_pg_query, """
            CREATE TABLE IF NOT EXISTS homework (
                id SERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                deadline TEXT NOT NULL,
                description TEXT NOT NULL,
                type TEXT DEFAULT 'dz',
                created_by BIGINT,
                created_at TEXT
            );
        """)
        await asyncio.to_thread(_pg_query, """
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                username TEXT,
                action TEXT,
                timestamp TEXT
            );
        """)
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS users (
                                user_id INTEGER PRIMARY KEY,
                                username TEXT,
                                role TEXT DEFAULT 'viewer')''')

            await db.execute('''CREATE TABLE IF NOT EXISTS homework (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                subject TEXT NOT NULL,
                                deadline TEXT NOT NULL,
                                description TEXT NOT NULL,
                                type TEXT DEFAULT 'dz',
                                created_by INTEGER,
                                created_at TEXT)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS logs (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER,
                                username TEXT,
                                action TEXT,
                                timestamp TEXT)''')
            await db.commit()


async def add_user(user_id: int, username: str, role: str):
    if DATABASE_URL:
        query = """
            INSERT INTO users (user_id, username, role) VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, role = EXCLUDED.role
        """
        await asyncio.to_thread(_pg_query, query, (user_id, username, role))
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT OR REPLACE INTO users (user_id, username, role) VALUES (?, ?, ?)",
                             (user_id, username, role))
            await db.commit()


async def get_user_role(user_id: int):
    if DATABASE_URL:
        query = "SELECT role FROM users WHERE user_id = %s"
        row = await asyncio.to_thread(_pg_query, query, (user_id,), "one")
        return row[0] if row else None
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None


async def log_action(user_id: int, username: str, action: str):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    if DATABASE_URL:
        query = "INSERT INTO logs (user_id, username, action, timestamp) VALUES (%s, %s, %s, %s)"
        await asyncio.to_thread(_pg_query, query, (user_id, username, action, now))
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT INTO logs (user_id, username, action, timestamp) VALUES (?, ?, ?, ?)",
                             (user_id, username, action, now))
            await db.commit()


async def get_all_logs():
    if DATABASE_URL:
        query = "SELECT username, action, timestamp FROM logs ORDER BY id DESC LIMIT 50"
        res = await asyncio.to_thread(_pg_query, query, (), "all")
        return res if res else []
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT username, action, timestamp FROM logs ORDER BY id DESC LIMIT 50") as cursor:
                return await cursor.fetchall()


async def add_homework(subject: str, deadline: str, description: str, hw_type: str, user_id: int, username: str):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    if DATABASE_URL:
        query = """
            INSERT INTO homework (subject, deadline, description, type, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        await asyncio.to_thread(_pg_query, query, (subject, deadline, description, hw_type, user_id, now))
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT INTO homework (subject, deadline, description, type, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (subject, deadline, description, hw_type, user_id, now))
            await db.commit()
    await log_action(user_id, username,
                     f"Добавил {hw_type.upper()} по предметам [{subject}]: '{description}' на {deadline}")


async def get_homework(hw_type: str = 'dz'):
    if DATABASE_URL:
        query = "SELECT id, subject, deadline, description FROM homework WHERE type = %s ORDER BY deadline ASC"
        res = await asyncio.to_thread(_pg_query, query, (hw_type,), "all")
        return res if res else []
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute(
                    "SELECT id, subject, deadline, description FROM homework WHERE type = ? ORDER BY deadline ASC",
                    (hw_type,)) as cursor:
                return await cursor.fetchall()


async def delete_homework(hw_id: int, user_id: int, username: str):
    if DATABASE_URL:
        query = "DELETE FROM homework WHERE id = %s"
        await asyncio.to_thread(_pg_query, query, (hw_id,))
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("DELETE FROM homework WHERE id = ?", (hw_id,))
            await db.commit()
    await log_action(user_id, username, f"Удалил задание ID #{hw_id}")
