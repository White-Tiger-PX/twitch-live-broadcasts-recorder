"""
Модуль для получения Twitch user_id по имени пользователя через API.
"""
import requests

import config

from set_logger import set_logger
from fetch_access_token import fetch_access_token


def get_twitch_user_id(user_name: str, headers: dict, main_logger) -> str:
    """
    Получает user_id пользователя Twitch по его имени через API.

    Args:
        user_name (str): Имя пользователя Twitch для поиска.
        headers (dict): Заголовки для запроса, включая Client-ID и Authorization.
        main_logger (logging.Logger): Логгер.

    Returns:
        str or None: Возвращает user_id пользователя, если найден, или None в случае ошибки.

    Raises:
        Exception: Если возникает ошибка в процессе получения данных через API или обработки данных.
    """
    try:
        logger = main_logger.getChild('get_twitch_user_id')
        correct_user_name = user_name.lower()

        url_user_id = f"https://api.twitch.tv/helix/users?login={correct_user_name}"
        response = requests.get(url_user_id, headers=headers, timeout=15)
        response.raise_for_status()
        user_data = response.json().get("data", [])

        if not user_data:
            return None

        user_id = user_data[0].get("id")

        return user_id
    except requests.exceptions.RequestException as err:
        logger.error("Ошибка при получении ID для пользователя [ %s ]: %s", correct_user_name, err)

        raise
    except Exception as err:
        logger.error("Ошибка при работе с базой данных для пользователя [ %s ]: %s", correct_user_name, err)

        raise


if __name__ == "__main__":
    user_input = input("Введите ник пользователя Twitch, чтобы получить его user_id: ")

    logger = set_logger(config.log_folder)

    access_token = fetch_access_token(
        client_id     = config.client_id,
        client_secret = config.client_secret,
        logger        = logger
    )

    headers = {"Client-ID": config.client_id, "Authorization": f"Bearer {access_token}"}

    user_id = get_twitch_user_id(
        user_name   = user_input,
        headers     = headers,
        main_logger = logger
    )

    logger.info("User ID: %s", user_id)
