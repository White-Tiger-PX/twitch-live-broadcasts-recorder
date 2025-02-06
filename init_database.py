"""
Модуль для инициализации базы данных для хранения информации о трансляциях с Twitch.

Этот модуль содержит функцию `init_database`, которая создает таблицы в базе данных для
хранения данных о трансляциях и маппинга имен пользователей Twitch на их идентификаторы.

Краткое описание функций:
    - init_database: Инициализирует базу данных, создавая необходимые таблицы, если они не существуют.
"""
import sqlite3

import config

from set_logger import set_logger


def init_database(database_path, main_logger):
    """Инициализирует базу данных и создает необходимые таблицы.

    Args:
        database_path (str): Путь к файлу базы данных.
        main_logger (logging.Logger): Логгер.

    Raises:
        Exception: Если возникает ошибка при выполнении операций с базой данных.
    """
    logger = main_logger.getChild('init_database')
    logger.info("Инициализация базы данных.")

    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS live_broadcast (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    user_name TEXT,
                    stream_id TEXT,
                    recording_start TEXT,
                    title TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS twitch_user_name_to_id_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT UNIQUE,
                    user_id TEXT
                )
            ''')

            conn.commit()

        logger.info("Инициализация базы данных завершена.")
    except Exception as err:
        logger.error("Ошибка при инициализации базы данных: %s", err)

        raise


if __name__ == "__main__":
    logger = set_logger(log_folder=config.log_folder)

    init_database(
        database_path=config.database_path,
        main_logger=logger
    )
