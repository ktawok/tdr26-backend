# parser_mmis.py
import requests
import logging


def get_mgri_schedule(date_str: str, group_name: str = "ТДР-26"):
    """
    Получает расписание для группы ТДР-26 МГРИ на указанную дату (ДД.ММ.ГГГГ)
    """
    # Стандартная структура пар МГРИ
    schedule_data = {
        "21.09.2026": [
            {"num": 1, "time": "09:00 - 10:30", "subject": "Физические процессы нефтегазового производства",
             "room": "402-1"},
            {"num": 2, "time": "10:40 - 12:10", "subject": "Высшая математика", "room": "315-2"},
            {"num": 3, "time": "12:50 - 14:20", "subject": "Общая физика", "room": "201-1"}
        ]
    }

    # Попытка динамического запроса к MMIS / расписанию МГРИ
    try:
        # Endpoint МГРИ MMIS
        url = f"https://mgri.ru/api/schedule?group={group_name}&date={date_str}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return response.json().get("pairs", [])
    except Exception as e:
        logging.warning(f"MMIS сервер недоступен, используем локальную базу расписания: {e}")

    return schedule_data.get(date_str, [
        {"num": 1, "time": "09:00 - 10:30", "subject": "Нет пар / Информационные данные не загружены", "room": "-"}
    ])