import time
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
from utils import get_video_path, get_twitch_user_ids


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


class StreamRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stream Recorder")
        self.root.geometry("600x300")

        self.root.configure(bg="black")

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background="black",
            foreground="white",
            fieldbackground="black",
            font=("Arial", 12),
            rowheight=25
        )
        style.configure(
            "Treeview.Heading",
            background="gray",
            foreground="white",
            font=("Arial", 12, "bold")
        )
        style.map("Treeview", background=[("selected", "gray")])

        self.tree = ttk.Treeview(
            root,
            columns=("Streamer", "Start Time", "Duration"),
            show="headings",
            style="Treeview"
        )

        self.tree.heading("Streamer", text="Streamer")
        self.tree.heading("Start Time", text="Start Time")
        self.tree.heading("Duration", text="Duration")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Настройка столбцов: ширины и выравнивания
        self.tree.column("Streamer", width=100, anchor="center")
        self.tree.column("Start Time", width=100, anchor="center")
        self.tree.column("Duration", width=100, anchor="center")

        self.active_records = {}

        self.update_duration()

    def add_record(self, user_name):
        start_time = datetime.now()
        self.active_records[user_name] = {
            "start_time": start_time,
            "item_id": self.tree.insert("", "end", values=(user_name, start_time.strftime("%Y-%m-%d %H:%M:%S"), "0:00:00"))
        }

        # Подбираем ширину столбцов
        self.resize_columns()

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

            # Подбираем ширину столбцов
            self.resize_columns()

    def resize_columns(self):
        """Автоматически изменяет ширину столбцов в зависимости от их содержимого."""
        for col in self.tree["columns"]:
            max_width = 0

            # Пройти по всем строкам в столбце и найти максимальную длину текста
            for row in self.tree.get_children():

                item_text = str(self.tree.item(row)["values"][self.tree["columns"].index(col)])
                max_width = max(max_width, len(item_text))

            # Установить ширину столбца в соответствии с максимальной длиной текста
            # с учетом множителя для отступов
            self.tree.column(col, width=max(max_width * 10, 100))  # минимум 100 пикселей


def current_datetime_to_utc_iso():
    now = datetime.now() + timedelta(hours=config.utc_offset_hours)

    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def add_record_to_db(stream_data, recording_start):
    try:
        with sqlite3.connect(config.database_path) as conn:
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


def record_twitch_channel(active_users, stream_data, storages, app):
    try:
        user_name = stream_data['user_name']
        user_id = stream_data['user_id']
        stream_id = stream_data['id']

        video_label = f"[ {user_name} - {stream_id} ]"

        active_users.add(user_id)

        recording_start = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        name_components = [recording_start, 'broadcast', user_name, stream_id]

        recorded_file_path = get_video_path(
            storages=storages,
            user_name=user_name,
            name_components=name_components,
            logger=logger
        )

        logger.info(f"Запись стрима пользователя {video_label} началась.")

        add_record_to_db(
            stream_data=stream_data,
            recording_start=recording_start
        )

        record_broadcast(recorded_file_path, user_name, app, logger)

        logger.info(f"Запись стрима пользователя {video_label} закончилась.")
    except Exception as err:
        logger.error(f"Ошибка при записи трансляции канала [ {user_name} ]: {err}")
    finally:
        time.sleep(5)
        active_users.discard(user_id)


def check_users(client_id, client_secret, token_container, user_ids):
    info = None
    url = "https://api.twitch.tv/helix/streams"
    params = '&'.join([f'user_id={user_id}' for user_id in user_ids])

    try:
        headers = {"Client-ID": client_id, "Authorization": f"Bearer {token_container["access_token"]}" }
        r = requests.get(f"{url}?{params}", headers=headers, timeout=15)
        r.raise_for_status()
        info = r.json()

        active_streamers = []

        for stream in info.get("data", []):
            active_streamers.append(stream)

        return active_streamers
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response.status_code == 401:
            logger.info("🔄 Токен устарел или неверный, обновление...")

            token_container["access_token"] = fetch_access_token(
                client_id=client_id,
                client_secret=client_secret,
                logger=logger
            )
        else:
            logger.error(f"Ошибка при проверки статуса пользователей {user_ids}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при проверки статуса пользователей: {e}")

    return None


def loop_check_with_rate_limit(client_id, client_secret, token_container, storages, user_identifiers, app):
    active_users = set()

    # Изначально получаем идентификаторы пользователей
    user_ids = get_twitch_user_ids(
        client_id=client_id,
        access_token=token_container["access_token"],
        database_path=config.database_path,
        user_identifiers=user_identifiers,
        logger=logger
    )

    while True:
        try:
            limiter.wait()

            user_ids_for_check = [
                user_id for user_id
                in user_ids
                if user_id not in active_users
            ]

            if not user_ids_for_check:
                continue

            streams_data = check_users(
                client_id=client_id,
                client_secret=client_secret,
                token_container=token_container,
                user_ids=user_ids_for_check
            )

            if streams_data is None:
                continue

            for stream_data in streams_data:
                recording_thread_name = f"process_recorded_broadcasts_thread_{stream_data['user_id']}"
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


def main():
    root = tk.Tk()
    app = StreamRecorderApp(root)

    logger.info("Программа для записи трансляций запущена!")

    init_database(database_path=config.database_path, main_logger=logger)

    client_id = config.client_id
    client_secret = config.client_secret
    user_identifiers = config.user_identifiers
    storages = config.storages

    token_container = {"access_token": None}

    # запускаем в отдельном потоке чтобы иметь возможность обновлять GUI
    threading.Thread(
        target=loop_check_with_rate_limit,
        args=(client_id, client_secret, token_container, storages, user_identifiers, app),
        daemon=True
    ).start()

    root.mainloop()


if __name__ == "__main__":
    logger = set_logger(log_folder=config.log_folder)
    limiter = RateLimiter(max_requests=1, period=5)

    main()
