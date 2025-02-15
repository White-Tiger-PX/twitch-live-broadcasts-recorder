import requests

import config

from set_logger import set_logger
from fetch_access_token import fetch_access_token


def get_twitch_user_id(user_name, headers, main_logger):
    """
    Получает user_id через API Twitch.
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
        logger.error(f"Ошибка при получении ID для пользователя [ {correct_user_name} ]: {err}")

        return None
    except Exception as err:
        logger.error(f"Ошибка при работе с базой данных для пользователя [ {correct_user_name} ]: {err}")

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

    headers = {"Client-ID": client_id, "Authorization": f"Bearer {access_token}"}

    user_id = get_twitch_user_id(
        user_name=user_input,
        headers=headers,
        main_logger=logger
    )

    logger.info("User ID: %s", user_id)
