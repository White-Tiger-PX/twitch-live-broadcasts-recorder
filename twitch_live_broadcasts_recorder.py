import time
import sqlite3
import requests
import threading
import tkinter as tk

from tkinter import ttk
from datetime import datetime, timezone

import config

from set_logger import set_logger
from init_database import init_database
from record_broadcast import record_broadcast
from fetch_access_token import fetch_access_token
from utils import get_video_path

class RateLimiter:
    def __init__(self, period):
        self.max_requests = 1
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
    """
    Приложение для отображения информации о текущих стримах.

    Этот класс предоставляет функциональность отображения информации
    о пользователях, времени начала и продолжительности стрима.

    Краткое описание функций:
        - add_record: Добавляет новый стрим в список активных записей.
        - update_duration: Обновляет продолжительность активных стримов.
        - remove_record: Удаляет стрим из списка активных.
        - resize_columns: Автоматически регулирует ширину столбцов в таблице для отображения данных.

    Args:
        root (tk.Tk): Основное окно приложения.
        tree (ttk.Treeview): Виджет для отображения информации о стримах.
        active_records (dict): Словарь с активными записями, где ключ — имя стримера, а значение — информация о записи.
    """

    def __init__(self, root):
        """
        Инициализирует приложение StreamRecorderApp.

        Настроены основные элементы UI, включая таблицу для отображения данных о стримах,
        а также настройка стилей и начальных значений.

        Args:
            root (tk.Tk): Основное окно приложения.
        """
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

        self.min_column_widths = {
            "Streamer": 100,
            "Start Time": 150,
            "Duration": 75
        }

        self.tree.column("Streamer", width=self.min_column_widths["Streamer"], anchor="center")
        self.tree.column("Start Time", width=self.min_column_widths["Start Time"], anchor="center")
        self.tree.column("Duration", width=self.min_column_widths["Duration"], anchor="center")

        self.active_records = {}

        self.update_duration()

    def add_record(self, user_name):
        """
        Добавляет новый стрим в список активных стримов.

        Эта функция создает новую запись в таблице, показывая имя стримера, время начала стрима
        и продолжительность (начальная продолжительность — 0).

        Args:
            user_name (str): user_name стримера, трансляция которого была обнаружена.
        """
        start_time = datetime.now()
        self.active_records[user_name] = {
            "start_time": start_time,
            "item_id": self.tree.insert("", "end", values=(user_name, start_time.strftime("%Y-%m-%d %H:%M:%S"), "0:00:00"))
        }

        self.resize_columns()

    def update_duration(self):
        """
        Обновляет продолжительность активных стримов.

        Эта функция рассчитывает прошедшее время с момента начала каждого стрима и обновляет
        информацию в таблице.
        """
        for user_name, record in self.active_records.items():
            start_time = record["start_time"]
            elapsed_time = datetime.now() - start_time
            self.tree.item(record["item_id"], values=(
                user_name,
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                str(elapsed_time).split(".", maxsplit=1)[0]
            ))

        self.root.after(1000, self.update_duration)

    def remove_record(self, user_name):
        """
        Удаляет стрим из списка активных.

        Эта функция удаляет запись о стриме из таблицы и очищает данные о нем
        в словаре активных записей.

        Args:
            user_name (str): Имя стримера, чью запись необходимо удалить.
        """
        if user_name in self.active_records:
            self.tree.delete(self.active_records[user_name]["item_id"])
            del self.active_records[user_name]

            self.resize_columns()

    def resize_columns(self):
        """Автоматически изменяет ширину столбцов в зависимости от их содержимого."""
        column_widths = {}

        for col in self.tree["columns"]:
            max_width = 0

            for row in self.tree.get_children():
                item_text = str(self.tree.item(row)["values"][self.tree["columns"].index(col)])
                max_width = max(max_width, len(item_text))

            min_width = self.min_column_widths.get(col, 100)
            column_widths[col] = max(max_width * 10, min_width)

        def apply_column_widths():
            for col, width in column_widths.items():
                self.tree.column(col, width=width)

        self.tree.after(0, apply_column_widths)


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
        user_id   = stream_data['user_id']
        stream_id = stream_data['id']

        video_label = f"[ {user_name} - {stream_id} ]"

        active_users.add(user_id)

        recording_start = datetime.now(timezone.utc).strftime('%Y-%m-%d %H-%M-%S')
        name_components = [recording_start, stream_id, 'broadcast', user_name]

        recorded_file_path = get_video_path(
            storages        = storages,
            user_name       = user_name,
            name_components = name_components,
            logger          = logger
        )

        logger.info(f"Запись стрима пользователя {video_label} началась.")

        add_record_to_db(stream_data=stream_data, recording_start=recording_start)
        record_broadcast(recorded_file_path, user_name, app, logger)

        logger.info(f"Запись стрима пользователя {video_label} закончилась.")
    except Exception as err:
        logger.error(f"Ошибка при записи трансляции канала [ {user_name} ]: {err}")
    finally:
        time.sleep(5)
        active_users.discard(user_id)


def check_users(token_container, user_ids):
    active_streamers = []

    if not user_ids:
        return active_streamers

    try:
        headers = {"Client-ID": config.client_id, "Authorization": f"Bearer {token_container["access_token"]}"}
        params = '&'.join([f'user_id={user_id}' for user_id in user_ids])
        r = requests.get(f"https://api.twitch.tv/helix/streams?{params}", headers=headers, timeout=15)
        r.raise_for_status()
        info = r.json() if r.json() else None

        for stream in info.get("data", []):
            if stream:
                active_streamers.append(stream)

        return active_streamers
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response.status_code == 401:
            logger.info("🔄 Токен устарел или неверный, обновление...")

            token_container["access_token"] = fetch_access_token(
                client_id     = config.client_id,
                client_secret = config.client_secret,
                logger        = logger
            )
        else:
            logger.error(f"Ошибка при проверки статуса пользователей {user_ids}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при проверки статуса пользователей: {e}")

    return active_streamers


def loop_check_with_rate_limit(user_ids, storages, app):
    """
    Бесконечный цикл для проверки активных пользователей и записи обнаруженных трансляций.

    Эта функция периодически проверяет статус трансляций пользователей, и если трансляция активна,
    запускает отдельный поток для записи трансляции.

    Args:
        user_identifiers (list): Список идентификаторов пользователей для проверки.
        storages (dict): Контейнер для хранения информации о хранилищах для записи.
        app (StreamRecorderApp): Приложение для записи и управления стримами.
    """
    token_container = {"access_token": None}
    active_users = set()

    while True:
        try:
            limiter.wait()

            user_ids_for_check = [
                user_id for user_id
                in user_ids
                if user_id not in active_users
            ]

            streams_data = check_users(token_container=token_container, user_ids=user_ids_for_check)

            for stream_data in streams_data:
                recording_thread_name = f"thread_{stream_data['user_name']}"
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

    user_ids = config.user_ids
    storages = config.storages

    threading.Thread(
        target=loop_check_with_rate_limit,
        args=(user_ids, storages, app),
        daemon=True
    ).start()

    root.mainloop()


if __name__ == "__main__":
    logger = set_logger(log_folder=config.log_folder)
    limiter = RateLimiter(period=5)

    main()
