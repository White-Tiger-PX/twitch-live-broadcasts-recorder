import time
import enum
import sqlite3
import requests
import threading
import tkinter as tk

from tkinter import ttk
from datetime import datetime, timedelta

import config

from set_logger import set_logger
from init_database import init_database
from record_broadcast import record_broadcast
from fetch_access_token import fetch_access_token
from utils import (
    get_video_path,
    get_twitch_user_ids
)


class TwitchResponseStatus(enum.Enum):
    ONLINE = 0
    OFFLINE = 1
    NOT_FOUND = 2
    UNAUTHORIZED = 3
    ERROR = 4


class StreamRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stream Recorder")
        self.root.geometry("600x400")

        # Создаем таблицу
        self.tree = ttk.Treeview(root, columns=("Streamer", "Start Time", "Duration"), show="headings")
        self.tree.heading("Streamer", text="Streamer")
        self.tree.heading("Start Time", text="Start Time")
        self.tree.heading("Duration", text="Duration")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Словарь для отслеживания активных записей
        self.active_records = {}

        # Запуск обновления длительности
        self.update_duration()

    def add_record(self, user_name):
        start_time = datetime.now()
        self.active_records[user_name] = {
            "start_time": start_time,
            "item_id": self.tree.insert("", "end", values=(user_name, start_time.strftime("%Y-%m-%d %H:%M:%S"), "0:00:00"))
        }

    def update_duration(self):
        for user_name, record in self.active_records.items():
            start_time = record["start_time"]
            elapsed_time = datetime.now() - start_time
            self.tree.item(record["item_id"], values=(
                user_name,
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                str(elapsed_time).split(".")[0]
            ))

        self.root.after(1000, self.update_duration)

    def remove_record(self, user_name):
        if user_name in self.active_records:
            self.tree.delete(self.active_records[user_name]["item_id"])
            del self.active_records[user_name]


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
            self.requests.append(time.time())


def current_datetime_to_utc_iso():
    now = datetime.now() + timedelta(hours=config.utc_offset_hours)

    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def add_record_to_db(stream_data, recording_start):
    try:
        conn = sqlite3.connect(config.database_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO live_broadcast (
                user_id,
                user_name,
                stream_id,
                recording_start,
                title
            )
            VALUES (?, ?, ?, ?, ?)
        ''', (
            stream_data['user_id'],
            stream_data['user_name'],
            stream_data['id'],
            recording_start,
            stream_data['title']
        ))

        conn.commit()
    except Exception as err:
        logger.error(f"Ошибка при добавлении записи: {err}")
    finally:
        cursor.close()
        conn.close()


def record_twitch_channel(active_users, stream_data, storages, app):
    try:
        user_name = stream_data['user_name']
        user_id = stream_data['user_id']
        stream_id = stream_data['id']

        active_users.add(user_id)

        recording_start = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        name_components = [recording_start, 'broadcast', user_name]

        recorded_file_path = get_video_path(
            storages=storages,
            user_name=user_name,
            name_components=name_components,
            logger=logger
        )

        logger.info(f"Запись стрима пользователя [ {user_name} - {stream_id} ] началась.")

        add_record_to_db(
            stream_data=stream_data,
            recording_start=recording_start
        )

        record_broadcast(recorded_file_path, user_name, app, logger)

        logger.info(f"Запись стрима пользователя [ {user_name} - {stream_id} ] закончилась.")
    except Exception as err:
        logger.error(f"Ошибка при записи трансляции канала {user_name}: {err}")
    finally:
        time.sleep(5)
        active_users.discard(user_id)


def check_user(user_id, client_id, access_token):
    info = None
    status = TwitchResponseStatus.ERROR
    url = "https://api.twitch.tv/helix/streams"

    try:
        headers = {"Client-ID": client_id, "Authorization": "Bearer " + access_token}
        r = requests.get(url + "?user_id=" + user_id, headers=headers, timeout=15)
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
                status = TwitchResponseStatus.UNAUTHORIZED
            elif e.response.status_code == 404:
                status = TwitchResponseStatus.NOT_FOUND

    if status == TwitchResponseStatus.NOT_FOUND:
        logger.info(f"1. {user_id}\n2. {status}\n3. {info}")
    elif status == TwitchResponseStatus.ERROR:
        if info is not None:
            logger.info(f"1. {user_id}\n2. {status}\n3. {info}")
    elif status == TwitchResponseStatus.UNAUTHORIZED:
        logger.warning(f"Токен устарел для {user_id}, обновляем...")

        access_token = fetch_access_token(
            client_id=client_id,
            client_secret=config.client_secret,
            logger=logger
        )

    return None


def loop_check_with_rate_limit(client_id, client_secret, storages, user_identifiers, app):
    active_users = set()

    access_token = fetch_access_token(
        client_id=client_id,
        client_secret=client_secret,
        logger=logger
    )

    user_ids = get_twitch_user_ids(
        client_id=client_id,
        access_token=access_token,
        user_identifiers=user_identifiers,
        logger=logger
    )

    while True:
        try:
            user_ids_for_check = [
                user_id for user_id
                in user_ids
                if user_id not in active_users
            ]

            for user_id in user_ids_for_check:
                limiter.wait()
                stream_data = check_user(user_id, client_id, access_token)

                if stream_data is None:
                    continue

                recording_thread_name = f"process_recorded_broadcasts_thread_{user_id}"
                recording_thread = threading.Thread(
                    target=record_twitch_channel,
                    args=(
                        active_users,
                        stream_data,
                        storages,
                        app
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
    root = tk.Tk()
    app = StreamRecorderApp(root)

    threading.Thread(target=app.update_duration, daemon=True).start()

    logger.info("Программа для записи трансляций запущена!")

    init_database(
        database_path=config.database_path,
        main_logger=logger
    )

    client_id = config.client_id
    client_secret = config.client_secret
    usernames = config.user_identifiers
    storages = config.storages

    threading.Thread(
        target=loop_check_with_rate_limit,
        args=(client_id, client_secret, storages, usernames, app),
        daemon=True
    ).start()

    root.mainloop()


if __name__ == "__main__":
    limiter = RateLimiter(max_requests=1, period=1)
    logger = set_logger(log_folder=config.log_folder)

    main()
