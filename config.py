log_folder = "logs/live_broadcasts"

# API
client_id = "your_client_id_here"
client_secret = "your_client_secret_here"

# Время смещения от UTC (можно использовать отрицательные числа)
utc_offset_hours = 0

# Путь к базе данных
database_path = "streams.db"

# Идентификаторы пользователей, может быть как ником, так и ID
# Предпочитительно ID, так как ник может смениться
user_identifiers = [
    "user_name_1",  # Ник пользователя
    "user_name_2",  # Ник пользователя
    123456789,      # ID пользователя (число)
    "987654321",    # ID пользователя (число в формате строки)
]

# Список хранилищ для записи стримов. Каждый элемент представляет собой
# словарь с информацией о пути к хранилищу и минимальном требуемом
# свободном пространстве на диске в гигабайтах.
storages = [
    {"path": "/path/to/storage1", "required_free_space_gb": 200},
    {"path": "/path/to/storage2", "required_free_space_gb": 100}
]
