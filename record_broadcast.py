"""
Модуль для записи трансляции с Twitch с использованием streamlink.

Краткое описание функций:
    - record_broadcast: Записывает трансляцию с Twitch в указанный файл.
"""
import time
import subprocess


def record_broadcast(recorded_file_path, user_name, app, logger):
    """Записывает трансляцию с Twitch в файл.

    Функция запускает процесс для записи потока с Twitch с использованием `streamlink`.
    Она отслеживает процесс записи и завершает его, когда запись заканчивается или возникает ошибка.

    Args:
        recorded_file_path (str): Путь к файлу, в который будет записан поток.
        user_name (str): Имя пользователя Twitch для записи потока.
        app (object): Объект приложения, использующий методы `add_record` и `remove_record` для управления записями.
        logger (logging.Logger): Логгер.

    Raises:
        Exception: Если возникает ошибка во время записи потока.
    """
    try:
        # Добавляем запись в приложение
        app.add_record(user_name)

        process = subprocess.Popen([
            "streamlink",
            "--twitch-disable-ads",
            f"twitch.tv/{user_name}",
            "best",
            "--ringbuffer-size",
            "128M",
            "-o",
            recorded_file_path
        ], creationflags=subprocess.CREATE_NO_WINDOW)

        while process.poll() is None:
            time.sleep(1)
    except Exception as err:
        logger.error(f"Ошибка во время записи для {user_name}: {err}")
    finally:
        # Убираем запись из приложения, когда процесс завершен или произошла ошибка
        app.remove_record(user_name)
