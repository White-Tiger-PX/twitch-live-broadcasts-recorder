import time
import enum
import sqlite3
import requests
import threading

from datetime import datetime, timedelta

import config

from set_logger import set_logger
from init_database import init_database
from utils_file_path import get_file_path
from record_broadcast import record_broadcast
from fetch_access_token import fetch_access_token


class CustomError(Exception):
    pass

class TwitchResponseStatus(enum.Enum):
    ONLINE = 0
    OFFLINE = 1
    NOT_FOUND = 2
    UNAUTHORIZED = 3
    ERROR = 4


class RateLimiter:
    def __init__(self, max_requests, period):
        self.max_requests = max_requests
        self.period = period
        self.requests = []
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()

            # Очищаем старые запросы, которые вышли за пределы периода
            self.requests = [req for req in self.requests if req > now - self.period]

            # Проверяем, не превышает ли количество запросов лимит
            if len(self.requests) >= self.max_requests:
                # Ждем до тех пор, пока не пройдет период с первого запроса
                sleep_time = self.period - (now - self.requests[0])

                if sleep_time > 0:
                    time.sleep(sleep_time)

            # Добавляем текущий запрос в список
            self.requests.append(time.time())  # Используем обновлённое текущее время для точности


def current_datetime_to_utc_iso():
    now = datetime.now() + timedelta(hours=config.utc_offset_hours)

    return now.strftime("%Y-%m-%dT%H:%M:%SZ")  # Форматирование с "Z" для обозначения UTC


def add_record_to_db(user_name, stream_id, recording_start, title):
    try:
        conn = sqlite3.connect(config.database_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO live_broadcast (
                user_name,
                twitch_broadcast_id,
                created_at,
                title
            )
            VALUES (?, ?, ?, ?)
            ''', (user_name, stream_id, recording_start, title)
        )
    except Exception as err:
        logger.error(f"Ошибка при добавлении записи: {err}")
    finally:
        cursor.close()
        conn.close()


def record_twitch_channel(active_users, active_pbars, user_name, stream_id, stream_data, recorded_file_path):
    try:
        active_users.add(user_name)
        logger.info(f"Запись стрима пользователя [ {user_name} - {stream_id} ] началась.")

        record_broadcast(recorded_file_path, user_name, active_pbars)

        logger.info(f"Запись стрима пользователя [ {user_name} - {stream_id} ] закончилась.")

        add_record_to_db(user_name, stream_id, stream_data['started_at'], stream_data['title'])
    except Exception as err:
        logger.error(f"Ошибка при записи трансляции канала {user_name}: {err}")
    finally:
        time.sleep(5)
        active_users.discard(user_name)


def check_user(user_name, client_id, access_token):
    info = None
    status = TwitchResponseStatus.ERROR
    url = "https://api.twitch.tv/helix/streams"

    try:
        headers = {"Client-ID": client_id, "Authorization": "Bearer " + access_token}
        r = requests.get(url + "?user_login=" + user_name, headers=headers, timeout=15)
        r.raise_for_status()
        info = r.json()

        if info is None or not info["data"]:
            status = TwitchResponseStatus.OFFLINE
        else:
            status = TwitchResponseStatus.ONLINE

            return info["data"][0]
    except requests.exceptions.RequestException as e:
        if e.response:
            if e.response.status_code == 401:
                # Ошибка авторизации — токен устарел, нужно обновить
                status = TwitchResponseStatus.UNAUTHORIZED
            elif e.response.status_code == 404:
                status = TwitchResponseStatus.NOT_FOUND

    if status == TwitchResponseStatus.NOT_FOUND:
        logger.info(f"1. {user_name}\n2. {status}\n3. {info}")
    elif status == TwitchResponseStatus.ERROR:
        if info is not None:
            logger.info(f"1. {user_name}\n2. {status}\n3. {info}")
    elif status == TwitchResponseStatus.UNAUTHORIZED:
        logger.warning(f"Токен устарел для {user_name}, обновляем...")

        access_token = fetch_access_token(
            client_id=client_id,
            client_secret=config.client_secret,
            logger=logger
        )

    return None


def update_pbars(active_pbars):
    """Функция для обновления всех прогресс-баров."""
    while True:
        for pbar in active_pbars:
            pbar.refresh()

        time.sleep(1)


def loop_check_with_rate_limit(client_id, client_secret, storages, user_names):
    active_pbars = []
    active_users = set()

    update_thread = threading.Thread(
        target=update_pbars,
        args=(active_pbars,),
        daemon=True
    )
    update_thread.start()

    access_token = fetch_access_token(
        client_id=client_id,
        client_secret=client_secret,
        logger=logger
    )

    while True:
        try:
            user_names_for_check = [
                user_name for user_name
                in user_names
                if user_name not in active_users
            ]

            for user_name in user_names_for_check:
                limiter.wait()
                stream_data = check_user(user_name, client_id, access_token)

                if stream_data is None:
                    continue

                file_path = get_file_path(
                    storages=storages,
                    stream_id=stream_data['id'],
                    user_name=user_name,
                    logger=logger
                )
                recording_thread_name = f"process_recorded_broadcasts_thread_{user_name}"
                recording_thread = threading.Thread(
                    target=record_twitch_channel,
                    args=(
                        active_users,
                        active_pbars,
                        user_name,
                        stream_data['id'],
                        stream_data,
                        file_path
                    ),
                    name=recording_thread_name,
                    daemon=True
                )
                recording_thread.start()

                time.sleep(5)
        except Exception as err:
            logger.error(f"Ошибка при проверке трансляции: {err}")
            time.sleep(15)

        time.sleep(1)


def main():
    logger.info("Программа для записи трансляций запущена!")

    init_database(
        database_path=config.database_path,
        main_logger=logger
    )

    client_id = config.client_id
    client_secret = config.client_secret
    usernames = config.user_names
    storages = config.storages

    loop_check_with_rate_limit(client_id, client_secret, storages, usernames)


if __name__ == "__main__":
    limiter = RateLimiter(max_requests=1, period=1)
    logger = set_logger(log_folder=config.log_folder)

    main()
