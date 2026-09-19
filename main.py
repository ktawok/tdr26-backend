# main.py
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

import config
import database
import parser_mmis

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Разрешаем CORS для GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# --- ТЕЛЕГРАМ БОТ ---

async def check_access(user_id: int) -> bool:
    if user_id in config.SUPER_ADMINS:
        return True
    role = await database.get_user_role(user_id)
    return role is not None


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    if user_id in config.SUPER_ADMINS:
        await database.add_user(user_id, username, "superadmin")

    if not await check_access(user_id):
        await message.answer("Нажмите Открыть Портал")
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎓 Открыть портал ТДР-26", web_app=WebAppInfo(url=config.WEBAPP_URL))]
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"Привет, {message.from_user.first_name}!\n"
        f"Добро пожаловать в портал группы {config.GROUP_NAME} {config.UNIVERSITY}.\n\n"
        "Нажми кнопку ниже, чтобы открыть расписание, ДЗ, сессию и логи.",
        reply_markup=keyboard
    )


@dp.message(Command("add_editor"))
async def add_editor_cmd(message: types.Message):
    if message.from_user.id not in config.SUPER_ADMINS:
        return
    try:
        args = message.text.split()
        target_id = int(args[1])
        await database.add_user(target_id, f"user_{target_id}", "editor")
        await database.log_action(message.from_user.id, message.from_user.username,
                                  f"Выдал права редактора ID {target_id}")
        await message.answer(f"✅ Пользователю {target_id} выданы права на редактирование.")
    except Exception:
        await message.answer("Использование: `/add_editor <TELEGRAM_ID>`")


# --- API ДЛЯ MINI APP ---

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Бот ТДР-26 работает 24/7"}


from config import SUPER_ADMINS, EDITORS

@app.get("/api/user_info")
async def get_user_info(user_id: str):
    # Преобразуем ID в число и строку, чтобы избежать ошибок с типами
    try:
        uid_int = int(user_id)
    except ValueError:
        uid_int = None
    uid_str = str(user_id)

    # 1. Проверка на Главного Админа (из config.py)
    if (uid_int in config.SUPER_ADMINS) or (uid_str in config.SUPER_ADMINS):
        return {"role": "superadmin", "can_edit": True}

    # 2. Проверка на Редактора (из config.py) — ТЕПЕРЬ РАБОТАЕТ!
    if hasattr(config, 'EDITORS') and ((uid_int in config.EDITORS) or (uid_str in config.EDITORS)):
        return {"role": "editor", "can_edit": True}

    # 3. Если пользователя нет в конфиге, проверяем роль в базе данных
    role = await database.get_user_role(uid_int if uid_int is not None else user_id)
    if not role:
        role = "viewer"

    return {"role": role, "can_edit": role in ['editor', 'superadmin']}


@app.get("/api/schedule")
async def get_schedule(date: str):
    pairs = parser_mmis.get_mgri_schedule(date)
    all_hw = await database.get_homework('dz')

    # Привязываем ДЗ к парам по дате
    return {"pairs": pairs, "homework": all_hw}


@app.get("/api/homework")
async def get_hw(type: str = 'dz'):
    return await database.get_homework(type)


@app.post("/api/homework/add")
async def add_hw(data: dict):
    user_id = data.get("user_id")
    username = data.get("username", "Неизвестный")

    role = await database.get_user_role(user_id)
    if user_id not in config.SUPER_ADMINS and role not in ['editor', 'superadmin']:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")

    await database.add_homework(
        subject=data['subject'],
        deadline=data['deadline'],
        description=data['description'],
        hw_type=data.get('type', 'dz'),
        user_id=user_id,
        username=username
    )
    return {"status": "success"}


@app.post("/api/homework/delete")
async def delete_hw(data: dict):
    user_id = data.get("user_id")
    username = data.get("username", "Неизвестный")
    hw_id = data.get("hw_id")

    role = await database.get_user_role(user_id)
    if user_id not in config.SUPER_ADMINS and role not in ['editor', 'superadmin']:
        raise HTTPException(status_code=403, detail="Нет прав на удаление")

    await database.delete_homework(hw_id, user_id, username)
    return {"status": "success"}


@app.get("/api/logs")
async def get_logs(user_id: int):
    if not await check_access(user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return await database.get_all_logs()


async def main():
    await database.init_db()
    # Запускаем бота и веб-сервер API одновременно
    config_server = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config_server)

    print(">>> Бот и API запущены на сервере <<<")
    await asyncio.gather(
        dp.start_polling(bot),
        server.serve()
    )


if __name__ == "__main__":
    asyncio.run(main())
