import sqlite3
import requests

import config

from set_logger import set_logger
from init_database import init_database
from fetch_access_token import fetch_access_token


def get_twitch_user_id(database_path, user_name, headers, main_logger):
    """
    Получает user_id из базы данных или из API, если его нет в базе данных.
    """
    try:
        logger = main_logger.getChild('get_twitch_user_id')
        correct_user_name = user_name.lower()
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_id
            FROM twitch_user_name_to_id_mapping
            WHERE user_name = ?
        ''', (correct_user_name,))

        result = cursor.fetchone()

        if result:
            return result[0]  # Возвращаем найденный user_id

        # Если ID не найден в базе данных, запрашиваем его с Twitch API
        url_user_id = f"https://api.twitch.tv/helix/users?login={correct_user_name}"
        response = requests.get(url_user_id, headers=headers, timeout=15)
        response.raise_for_status()
        user_data = response.json().get("data", [])

        if not user_data:
            return None

        user_id = user_data[0].get("id")

        cursor.execute('''
            INSERT OR REPLACE INTO twitch_user_name_to_id_mapping
            (user_name, user_id)
            VALUES (?, ?)
        ''', (correct_user_name, user_id))

        conn.commit()

        return user_id
    except requests.exceptions.RequestException as err:
        logger.error(f"Ошибка при получении ID для пользователя {correct_user_name}: {err}")

        return None
    except Exception as err:
        logger.error(f"Ошибка при работе с базой данных для пользователя {correct_user_name}: {err}")

        return None
    finally:
        cursor.close()
        conn.close()


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

    init_database(
        database_path=config.database_path,
        main_logger=logger
    )

    headers = {"Client-ID": client_id, "Authorization": f"Bearer {access_token}"}

    user_id = get_twitch_user_id(
        database_path=config.database_path,
        user_name=user_input,
        headers=headers,
        main_logger=logger
    )

    logger.info("User ID: %s", user_id)
