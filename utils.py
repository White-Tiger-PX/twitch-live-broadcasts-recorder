"""
Модуль общих (базовых) функций.

Краткое описание функций:
    - create_file_basename: Создает имя файла из списка компонентов.
    - create_file_path: Формирует полный путь к файлу на основе имени и директории.
    - get_video_path: Определяет путь для сохранения видео в выбранном хранилище.
    - get_twitch_user_ids: Получает идентификаторы пользователей Twitch по их логинам или ID.
"""
import os

from choose_storage import choose_storage


def create_file_basename(name_components, extension, logger):
    """
    Создает имя файла, объединяя компоненты имени и расширение файла.

    Args:
        name_components (list): Список компонентов, составляющих имя файла.
        extension (str): Расширение файла (без точки).
        logger (Logger): Логгер.

    Returns:
        str: Имя файла.

    Raises:
        Exception: Генерируется при ошибке создания имени файла.
    """
    try:
        raw_filename = f"{' - '.join(map(str, name_components))}.{extension}"
        sanitized_filename = "".join(char for char in raw_filename if char.isalnum() or char in " -_.:")

        return sanitized_filename
    except Exception as err:
        logger.error(f"Ошибка при создании имени файла: {err}")

        raise


def create_file_path(folder_path, name_components, extension, logger):
    """
    Создает путь к файлу, используя путь к папке, компоненты имени файла и расширение.

    Args:
        folder_path (str): Путь к папке, в которой будет создан файл.
        name_components (list): Список компонентов, составляющих имя файла.
        extension (str): Расширение файла (без точки).
        logger (Logger): Логгер.

    Returns:
        str: Нормализованный полный путь к файлу.

    Raises:
        Exception: Генерируется при ошибке создания пути к файлу.
    """
    try:
        basename = create_file_basename(name_components=name_components, extension=extension, logger=logger)
        file_path = os.path.join(folder_path, basename)

        return os.path.normpath(file_path)
    except Exception as err:
        logger.error(f"Ошибка при создании пути к файлу: {err}")

        raise


def get_video_path(storages, user_name, name_components, logger):
    """
    Определяет путь для сохранения видео в выбранном хранилище.

    Args:
        storages (list): Список доступных путей к хранилищам.
        user_name (str): Имя пользователя Twitch.
        name_components (list): Список компонентов, составляющих имя файла.
        logger (Logger): Логгер.

    Returns:
        str: Путь к файлу видео или None, если не удалось выбрать хранилище.
    """
    storage_path = choose_storage(storages=storages, logger=logger)

    if not storage_path:
        return None

    folder_path = os.path.join(storage_path, user_name)

    os.makedirs(folder_path, exist_ok=True)

    file_path = create_file_path(
        folder_path=folder_path,
        name_components=name_components,
        extension='mp4',
        logger=logger
    )

    return file_path
