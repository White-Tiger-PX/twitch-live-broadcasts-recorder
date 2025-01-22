import time
import subprocess


def record_broadcast(recorded_file_path, user_name, app, logger):
    app.add_record(user_name)

    try:
        process = subprocess.Popen([
            "streamlink",
            "--twitch-disable-ads",
            "twitch.tv/" + user_name,
            "best",
            "--ringbuffer-size",
            "300M",
            "-o",
            recorded_file_path
        ], creationflags=subprocess.CREATE_NO_WINDOW)

        while process.poll() is None:
            time.sleep(1)  #
    except Exception as err:
        logger.error(f"Ошибка во время записи для {user_name}: {err}")
    finally:
        app.remove_record(user_name)
