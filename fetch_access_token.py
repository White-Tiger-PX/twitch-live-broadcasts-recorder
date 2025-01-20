import time
import requests


def fetch_access_token(client_id, client_secret, logger):
    while True:
        try:
            token_url = "https://id.twitch.tv/oauth2/token?client_id=" + \
                        client_id + "&client_secret=" + client_secret + \
                        "&grant_type=client_credentials"
            token_response = requests.post(token_url, timeout=30)
            token_response.raise_for_status()
            token = token_response.json()

            return token["access_token"]
        except Exception as err:
            logger.error(f"Ошибка при получении токена: {err}")

            time.sleep(30)
