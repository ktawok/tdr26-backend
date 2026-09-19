import sqlite3
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config

app = FastAPI(title="TDR-26 Homework API")

# Разрешаем запросы с фронтенда GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = getattr(config, "DB_NAME", "bot_database.db")


# Инициализация базы данных (создаем таблицы для ДЗ и Логов)
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            deadline TEXT NOT NULL,
            description TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'dz'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# --- Модели данных (как ожидает твой фронтенд) ---
class AddHomeworkRequest(BaseModel):
    id: Optional[int] = None
    subject: str
    deadline: str
    description: str
    type: str
    user_id: str
    username: str

class DeleteHomeworkRequest(BaseModel):
    hw_id: int
    user_id: str
    username: str


# --- Та самая функция проверки прав (теперь видит эдиторов) ---
def check_permissions(user_id: str):
    try:
        uid_int = int(user_id)
    except (ValueError, TypeError):
        uid_int = None
    uid_str = str(user_id)

    super_admins = getattr(config, "SUPER_ADMINS", [])
    editors = getattr(config, "EDITORS", [])

    if (uid_int in super_admins) or (uid_str in super_admins):
        return "superadmin", True
    if (uid_int in editors) or (uid_str in editors):
        return "editor", True
    
    return "viewer", False


# --- ЭНДПОИНТЫ (Все твои оригинальные пути возвращены) ---

@app.get("/api/user_info")
async def get_user_info(user_id: str):
    role, can_edit = check_permissions(user_id)
    return {"role": role, "can_edit": can_edit}


@app.get("/api/homework")
async def get_homework(type: str = "dz"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Возвращаем массивом (id, subject, deadline, description), как ждет JS
    cursor.execute("SELECT id, subject, deadline, description FROM homework WHERE type = ?", (type,))
    rows = cursor.fetchall()
    conn.close()
    return rows


@app.post("/api/homework/add")
async def add_homework(data: AddHomeworkRequest):
    role, can_edit = check_permissions(data.user_id)
    
    if not can_edit:
        raise HTTPException(status_code=403, detail="Нет прав на добавление/редактирование")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if data.id:
        cursor.execute("""
            UPDATE homework SET subject=?, deadline=?, description=?, type=? WHERE id=?
        """, (data.subject, data.deadline, data.description, data.type, data.id))
        action_text = f"Отредактировал(а) {data.type}: {data.subject}"
    else:
        cursor.execute("""
            INSERT INTO homework (subject, deadline, description, type) VALUES (?, ?, ?, ?)
        """, (data.subject, data.deadline, data.description, data.type))
        action_text = f"Добавил(а) {data.type}: {data.subject}"
    
    # Сохраняем действие в логи
    time_now = datetime.now().strftime("%d.%m.%Y %H:%M")
    cursor.execute("INSERT INTO logs (username, action, timestamp) VALUES (?, ?, ?)", 
                   (data.username, action_text, time_now))
    
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/homework/delete")
async def delete_homework(data: DeleteHomeworkRequest):
    role, can_edit = check_permissions(data.user_id)
    
    if not can_edit:
        raise HTTPException(status_code=403, detail="Нет прав на удаление")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Получаем название предмета для записи в логи перед удалением
    cursor.execute("SELECT subject, type FROM homework WHERE id=?", (data.hw_id,))
    row = cursor.fetchone()
    if row:
        subject, hw_type = row[0], row[1]
        cursor.execute("DELETE FROM homework WHERE id=?", (data.hw_id,))
        
        # Пишем в логи
        action_text = f"Удалил(а) {hw_type}: {subject}"
        time_now = datetime.now().strftime("%d.%m.%Y %H:%M")
        cursor.execute("INSERT INTO logs (username, action, timestamp) VALUES (?, ?, ?)", 
                       (data.username, action_text, time_now))
        
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/api/logs")
async def get_logs(user_id: str):
    role, can_edit = check_permissions(user_id)
    # Если хочешь скрыть логи от обычных зрителей, раскомментируй следующие 2 строки:
    # if not can_edit:
    #     raise HTTPException(status_code=403, detail="Логи только для редакторов")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Возвращаем массивом (username, action, timestamp)
    cursor.execute("SELECT username, action, timestamp FROM logs ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return rows
