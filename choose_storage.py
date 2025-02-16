"""
Модуль для выбора хранилища с достаточным количеством свободного места.

Этот модуль содержит функцию `choose_storage`, которая проверяет доступные хранилища
и возвращает путь к папке, если в ней достаточно свободного места.

Краткое описание функций:
    - choose_storage: Выбирает хранилище с достаточным количеством свободного места.
"""
import os
import psutil


def choose_storage(storages, logger):
    """
    Выбирает хранилище с достаточным количеством свободного места.

    Args:
        storages (list): Список словарей, каждый из которых представляет хранилище с
                         директорией и требуемым количеством свободного места.
        logger (logging.Logger): Логгер.

    Returns:
        str or None: Путь к выбранному хранилищу, или None, если не найдено подходящее хранилище.
    """
    try:
        for storage in storages:
            folder_path = storage['path']
            required_free_space_gb = storage['required_free_space_gb']

            root_path = os.path.splitdrive(folder_path)[0] + "/"

            if not os.path.exists(root_path):
                logger.error(f"Диск для {folder_path} не найден или недоступен.")

                continue

            try:
                disk_usage = psutil.disk_usage(root_path)

                if disk_usage.free >= required_free_space_gb * (1024 ** 3):
                    return folder_path
            except OSError as err:
                logger.error(f"Ошибка доступа к диску {root_path}: {err}")

        logger.warning("Хранилища с необходимым объёмом свободного места не найдено.")
    except Exception as err:
        logger.error(f"Неизвестная ошибка при выборе хранилища: {err}")

    return None
