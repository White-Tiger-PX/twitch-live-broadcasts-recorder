"""
Модуль для выбора хранилища с достаточным количеством свободного места.

Этот модуль содержит функцию `choose_storage`, которая проверяет доступные хранилища
и возвращает путь к папке, если в ней достаточно свободного места.

Краткое описание функций:
    - choose_storage: Выбирает хранилище с достаточным количеством свободного места.
"""
import psutil


def choose_storage(storages, logger):
    """Выбирает хранилище с достаточным количеством свободного места.

    Функция проверяет доступные хранилища и выбирает первое, в которой свободного места
    достаточно для выполнения операции. В случае ошибки доступа или недостатка места
    функция пытается повторить проверку через 10 минут.

    Args:
        storages (list): Список словарей, каждый из которых представляет хранилище с
                         путём и требуемым количеством свободного места.
        logger (logging.Logger): Логгер.

    Returns:
        str or None: Путь к выбранному хранилищу, или None, если не найдено подходящее хранилище.
    """
    try:
        for storage in storages:
            folder_path = storage['path']
            required_free_space_gb = storage['required_free_space_gb']

            try:
                disk_usage = psutil.disk_usage(folder_path)

                if disk_usage.free >= required_free_space_gb * (1024 ** 3):
                    return folder_path
            except FileNotFoundError as err:
                logger.error(f"Папка {folder_path} не найдена или недоступна: {err}")
            except OSError as err:
                logger.error(f"Ошибка доступа или создания папки {folder_path}: {err}")
    except Exception as err:
        logger.error(f"Неизвестная ошибка при выборе папки: {err}")

        raise

    return None
