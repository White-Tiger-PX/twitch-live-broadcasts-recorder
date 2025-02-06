import os

from choose_storage import choose_storage
from get_twitch_user_id import get_twitch_user_id


def create_file_basename(name_components, extension, logger):
    try:
        name_components = [str(item) for item in name_components]
        raw_filename = f"{' - '.join(name_components)}.{extension}"
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


def get_video_path(storages, user_name, name_components, logger):
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


def get_twitch_user_ids(client_id, access_token, database_path, user_identifiers, logger):
    headers = {"Client-ID": client_id, "Authorization": f"Bearer {access_token}"}

    user_ids = set()

    for user_identifier in user_identifiers:
        if isinstance(user_identifier, int):
            user_ids.add(str(user_identifier))
        elif user_identifier.isdigit():
            user_ids.add(str(user_identifier))
        else:
            user_id = get_twitch_user_id(
                database_path=database_path,
                user_name=user_identifier,
                headers=headers,
                main_logger=logger
            )

            if user_id:
                user_ids.add(user_id)

    return list(user_ids)
