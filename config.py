import os

# Считываем токен из секретных переменных Render
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Список Telegram ID главных админов
SUPER_ADMINS = [1788867885, "1788867885"]

# Список редакторов (если нужно добавить кого-то из одногруппников)
EDITORS = []

# Ссылка на твой GitHub Pages (со слэшем на конце)
WEBAPP_URL = "https://ktawok.github.io/tdr26-mini-app/"

# Группа и ВУЗ
GROUP_NAME = "ТДР-26"
UNIVERSITY = "МГРИ"

# Файл базы данных
DB_NAME = "bot_database.db"
