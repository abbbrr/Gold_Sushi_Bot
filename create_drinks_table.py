import sqlite3

# Подключение к SQLite и создание таблицы
sqlite_conn = sqlite3.connect('drinks.db')
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute('''
    CREATE TABLE IF NOT EXISTS drinks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        drink TEXT,
        quantity INTEGER,
        cost REAL
    )
''')

# Закрытие соединения с SQLite
sqlite_conn.close()