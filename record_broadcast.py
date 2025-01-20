import subprocess

from tqdm import tqdm


def record_broadcast(recorded_file_path, user_name, active_pbars):
    with tqdm(total=0, desc=f'Запись стрима [ {user_name} ]',
        ncols=0, leave=False, bar_format='{desc} {elapsed}') as pbar:
        active_pbars.append(pbar)

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

        process.wait()
        active_pbars.remove(pbar)
