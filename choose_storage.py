import time
import psutil


def choose_storage(storages, logger):
    try:
        for storage in storages:
            folder_path = storage['path']
            required_free_space_gb = storage['required_free_space_gb']

            try:
                disk_usage = psutil.disk_usage(folder_path)

                if disk_usage.free >= required_free_space_gb * (1024 ** 3):
                    return folder_path
            except FileNotFoundError as err:
                logger.error(f"Папка не найдена или недоступна: {folder_path}. Ошибка: {err}")
            except OSError as err:
                logger.error(f"Ошибка доступа или создания папки {folder_path}: {err}")

        time.sleep(600)

        raise Exception("Нет папки с достаточным количеством свободного места.")
    except Exception as err:
        logger.error(f"Неизвестная ошибка при выборе папки: {err}", log_type="")

        raise
