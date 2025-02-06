"""
Модуль для получения user_id пользователя Twitch.

Этот модуль предоставляет  для получения уникального идентификатора пользователя (user_id) из базы данных,
если он уже сохранён, или через запрос к API Twitch, если пользователь не найден в базе данных. Если user_id успешно
получен через API, он сохраняется в базу данных для последующего использования.

Краткое описание функций:
    - get_user_id_from_db: Получает user_id из базы данных для указанного логина пользователя.
    - fetch_user_id_from_api: Получает user_id пользователя с помощью запроса к API Twitch.
    - save_user_id_to_db: Сохраняет полученный user_id в базу данных для дальнейшего использования.
    - get_twitch_user_id: Основная функция для получения user_id, сначала из базы данных, а если не найдено, через API Twitch.
"""
import sqlite3
import requests

import config

from set_logger import set_logger
from init_database import init_database
from fetch_access_token import fetch_access_token


def get_user_id_from_db(user_login, cursor):
    """
    Получает user_id из базы данных.

    Args:
        database_path (str): Путь к базе данных.
        user_login (str): Логин пользователя Twitch.
        cursor (sqlite3.Cursor): Курсор базы данных.

    Returns:
        str or None: Возвращает user_id, если найден, иначе None.
    """
    cursor.execute('''
        SELECT user_id
        FROM twitch_user_name_to_id_mapping
        WHERE user_name = ?
    ''', (user_login,))

    result = cursor.fetchone()

    if result:
        return result[0]  # Возвращаем найденный user_id
    return None


def fetch_user_id_from_api(user_login, headers):
    """
    Получает user_id с помощью API Twitch.

    Args:
        user_login (str): Логин пользователя Twitch.
        headers (dict): Заголовки для запросов к API Twitch.

    Returns:
        str or None: Возвращает user_id, если найден, иначе None.
    """
    url_user_id = f"https://api.twitch.tv/helix/users?login={user_login}"

    try:
        response = requests.get(url_user_id, headers=headers, timeout=15)
        response.raise_for_status()
        user_data = response.json().get("data", [])

        if not user_data:
            return None

        return user_data[0].get("id")
    except requests.exceptions.RequestException as err:
        return None


def save_user_id_to_db(database_path, user_login, user_id):
    """
    Сохраняет user_id в базу данных.

    Args:
        database_path (str): Путь к базе данных.
        user_login (str): Логин пользователя Twitch.
        user_id (str): ID пользователя Twitch.
    """
    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO twitch_user_name_to_id_mapping
                (user_name, user_id)
                VALUES (?, ?)
            ''', (user_login, user_id))
            conn.commit()
    except Exception as err:
        raise Exception(f"Ошибка при сохранении user_id в базе данных: {err}")


def get_twitch_user_id(database_path, user_name, headers, main_logger):
    """
    Получает user_id из базы данных, или из API, если его нет в базе данных.

    Если user_id не найден в базе данных, он будет получен через API Twitch и сохранен в базу данных.

    Args:
        database_path (str): Путь к базе данных.
        user_name (str): Имя пользователя Twitch.
        headers (dict): Заголовки для запросов к API Twitch.
        main_logger (logging.Logger): Логгер.

    Returns:
        str or None: Возвращает user_id, если он найден или получен, или None, если произошла ошибка.
    """
    logger = main_logger.getChild('get_twitch_user_id')
    user_login = user_name.lower()

    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()

            # Попытка получить user_id из базы данных
            user_id = get_user_id_from_db(user_login, cursor)

            if user_id:
                return user_id  # Возвращаем найденный user_id

            # Если ID не найден в базе данных, запрашиваем его с Twitch API
            user_id = fetch_user_id_from_api(user_login, headers)

            if not user_id:
                return None  # Если API не вернул ID, возвращаем None

            # Сохраняем полученный user_id в базе данных
            save_user_id_to_db(database_path, user_login, user_id)

            return user_id
    except Exception as err:
        logger.error(f"Ошибка при работе с базой данных или API для пользователя {user_login}: {err}")

    return None


if __name__ == "__main__":
    user_input = input("Введите ник пользователя Twitch, чтобы получить его user_id: ")

    logger = set_logger(config.log_folder)

    client_id = config.client_id
    client_secret = config.client_secret

    access_token = fetch_access_token(
        client_id=client_id,
        client_secret=client_secret,
        logger=logger
    )

    init_database(database_path=config.database_path, main_logger=logger)

    headers = {"Client-ID": client_id, "Authorization": f"Bearer {access_token}"}

    user_id = get_twitch_user_id(
        database_path=config.database_path,
        user_name=user_input,
        headers=headers,
        main_logger=logger
    )

    logger.info("User ID: %s", user_id)
