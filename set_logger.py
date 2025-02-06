"""
Модуль для настройки логирования.

Этот модуль предоставляет функцию для настройки логирования, которая создаёт логгер с двумя обработчиками:
1. Файл — если указана папка для хранения логов, лог-файл создаётся с временной меткой в имени.
2. Консоль — выводит сообщения в стандартный поток.

Краткое описание функций:
    - set_logger: Настроить логгер для записи сообщений как в файл, так и в консоль.
"""
import os
import logging

from datetime import datetime


def set_logger(log_folder=None):
    """
    Настроить логгер для записи сообщений в файл и/или консоль.

    Функция создаёт логгер с двумя обработчиками:
    1. Файл — если указана папка для логов, лог-файл будет создан с текущей датой в имени.
    2. Консоль — выводит лог-сообщения в консоль.

    Если папка для логов не указана, будет только вывод в консоль.

    Args:
        log_folder (str, optional): Папка для хранения логов. Если не указана, логирование происходит только в консоль.

    Returns:
        logging.Logger: Настроенный объект логгера.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if log_folder:  # Создание файла с логами только если указана папка
        log_filename = datetime.now().strftime('%Y-%m-%d %H-%M-%S.log')
        log_file_path = os.path.join(log_folder, log_filename)

        os.makedirs(log_folder, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
