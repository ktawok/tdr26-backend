import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config

app = FastAPI(title="TDR-26 Homework API")

# Разрешаем запросы (CORS) с фронтенда GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = getattr(config, "DB_NAME", "bot_database.db")


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            deadline TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


# Pydantic-модель входящих данных ДЗ
class HomeworkItem(BaseModel):
    id: Optional[int] = None
    subject: str
    description: str
    deadline: str  # Формат: YYYY-MM-DD


# Единая функция проверки прав доступа (Проверяет и числа, и строки)
def get_user_role_and_permissions(user_id: str | int):
    try:
        uid_int = int(user_id)
    except (ValueError, TypeError):
        uid_int = None
    uid_str = str(user_id)

    super_admins = getattr(config, "SUPER_ADMINS", [])
    editors = getattr(config, "EDITORS", [])

    # 1. Главный админ
    if (uid_int in super_admins) or (uid_str in super_admins):
        return "superadmin", True

    # 2. Редактор
    if (uid_int in editors) or (uid_str in editors):
        return "editor", True

    # 3. Обычный зритель
    return "viewer", False


# 1. Информация о пользователе
@app.get("/api/user_info")
async def get_user_info(user_id: str):
    role, can_edit = get_user_role_and_permissions(user_id)
    return {"role": role, "can_edit": can_edit}


# 2. Получение списка всех ДЗ
@app.get("/api/homework")
async def get_homework():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, subject, description, deadline FROM homework")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# 3. Сохранение / Редактирование ДЗ (Доступно и Главным Админам, и Эдиторам)
@app.post("/api/homework")
async def save_homework(item: HomeworkItem, user_id: str = Query(...)):
    role, can_edit = get_user_role_and_permissions(user_id)

    if not can_edit:
        raise HTTPException(
            status_code=403, detail="У вас нет прав на редактирование заданий."
        )

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if item.id:
        # Редактирование существующей записи
        cursor.execute(
            """
            UPDATE homework
            SET subject = ?, description = ?, deadline = ?
            WHERE id = ?
        """,
            (item.subject, item.description, item.deadline, item.id),
        )
        print(f"Пользователь {user_id} ({role}) обновил ДЗ с ID {item.id}")
    else:
        # Создание новой записи
        cursor.execute(
            """
            INSERT INTO homework (subject, description, deadline)
            VALUES (?, ?, ?)
        """,
            (item.subject, item.description, item.deadline),
        )
        print(f"Пользователь {user_id} ({role}) создал новое ДЗ")

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Задание успешно сохранено"}


# 4. Удаление ДЗ
@app.delete("/api/homework/{item_id}")
async def delete_homework(item_id: int, user_id: str = Query(...)):
    role, can_edit = get_user_role_and_permissions(user_id)

    if not can_edit:
        raise HTTPException(
            status_code=403, detail="У вас нет прав на удаление заданий."
        )

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM homework WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    print(f"Пользователь {user_id} ({role}) удалил ДЗ с ID {item_id}")
    return {"status": "success", "message": "Задание удалено"}
