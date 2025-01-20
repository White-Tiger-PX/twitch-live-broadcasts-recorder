import os
from datetime import datetime

from choose_storage import choose_storage


def create_file_basename(name_components, extension, logger):
    try:
        name_components = [str(item) for item in name_components]
        raw_filename = f"{' - '.join(name_components)} - 1.{extension}"
        sanitized_filename = "".join(
            char for char in raw_filename if char.isalnum() or char in [" ", "-", "_", "."]
        )

        return sanitized_filename
    except Exception as err:
        logger.error(f"Ошибка при создании имени файла: {err}")

        raise


def create_file_path(folder_path, name_components, extension, logger):
    try:
        basename = create_file_basename(name_components, extension, logger)
        file_path = os.path.join(folder_path, basename)

        return os.path.normpath(file_path)
    except Exception as err:
        logger.error(f"Ошибка при создании пути к файлу: {err}")

        raise


def get_file_path(storages, stream_id, user_name, logger):
    file_path = None

    date = datetime.now().strftime('%Y-%m-%d %H-%M-%S')

    name_components = [date, 'broadcast', user_name]

    name_components.insert(1, stream_id)

    storage_path = choose_storage(storages=storages, logger=logger)
    folder_path = os.path.join(storage_path, user_name)

    os.makedirs(folder_path, exist_ok=True)

    file_path = create_file_path(
        folder_path=folder_path,
        name_components=name_components,
        extension='mp4',
        logger=logger
    )

    return file_path
