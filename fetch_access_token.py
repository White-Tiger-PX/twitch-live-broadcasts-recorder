"""
Модуль для получения учётных данных от Twitch.

Краткое описание функций:
- fetch_access_token: Получает учётные данные для Twitch.
"""
import time
import requests


def fetch_access_token(client_id, client_secret, logger):
    """
    Получает учётные данные для Twitch.

    Функция выполняет запрос к API Twitch для получения учётных данных.
    Функция будет повторять попытку каждые 60 секунд до успешного получения токена.

    Args:
        client_id (str): Идентификатор клиента Twitch.
        client_secret (str): Секрет клиента Twitch.
        logger (logging.Logger): Логгер.

    Returns:
        str: Access token для использования в API запросах.

    Raises:
        Exception: Если произошла неизвестная ошибка.
    """
    while True:
        try:
            token_url = "https://id.twitch.tv/oauth2/token?client_id=" + \
                        client_id + "&client_secret=" + client_secret + \
                        "&grant_type=client_credentials"
            token_response = requests.post(token_url, timeout=30)
            token_response.raise_for_status()
            token = token_response.json()

            return token["access_token"]
        except requests.exceptions.RequestException as err:
            logger.error(f"Ошибка при получении токена в модуле fetch_access_token: {err}")

            time.sleep(60)
        except Exception as err:
            logger.error(f"Неизвестная ошибка в модуле fetch_access_token: {err}")

            return None
