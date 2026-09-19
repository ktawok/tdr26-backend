# database.py
import aiosqlite
from datetime import datetime

DB_NAME = "bot_database.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Пользователи и их роли
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            username TEXT,
                            role TEXT DEFAULT 'viewer')''')

        # Домашние задания и сессии
        await db.execute('''CREATE TABLE IF NOT EXISTS homework (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            subject TEXT NOT NULL,
                            deadline TEXT NOT NULL,
                            description TEXT NOT NULL,
                            type TEXT DEFAULT 'dz',
                            created_by INTEGER,
                            created_at TEXT)''')

        # Логи действий (Audit Log)
        await db.execute('''CREATE TABLE IF NOT EXISTS logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            username TEXT,
                            action TEXT,
                            timestamp TEXT)''')
        await db.commit()


async def add_user(user_id: int, username: str, role: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, username, role) VALUES (?, ?, ?)",
                         (user_id, username, role))
        await db.commit()


async def get_user_role(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def log_action(user_id: int, username: str, action: str):
    async with aiosqlite.connect(DB_NAME) as db:
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        await db.execute("INSERT INTO logs (user_id, username, action, timestamp) VALUES (?, ?, ?, ?)",
                         (user_id, username, action, now))
        await db.commit()


async def get_all_logs():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username, action, timestamp FROM logs ORDER BY id DESC LIMIT 50") as cursor:
            return await cursor.fetchall()


async def add_homework(subject: str, deadline: str, description: str, hw_type: str, user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        await db.execute(
            "INSERT INTO homework (subject, deadline, description, type, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (subject, deadline, description, hw_type, user_id, now))
        await db.commit()
    await log_action(user_id, username,
                     f"Добавил {hw_type.upper()} по предметам [{subject}]: '{description}' на {deadline}")


async def get_homework(hw_type: str = 'dz'):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT id, subject, deadline, description FROM homework WHERE type = ? ORDER BY deadline ASC",
                (hw_type,)) as cursor:
            return await cursor.fetchall()


async def delete_homework(hw_id: int, user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM homework WHERE id = ?", (hw_id,))
        await db.commit()
    await log_action(user_id, username, f"Удалил задание ID #{hw_id}")