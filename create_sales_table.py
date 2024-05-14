import sqlite3

sqlite_conn = sqlite3.connect('sales.db')
sqlite_cursor = sqlite_conn.cursor()

sqlite_cursor.execute(''' CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL, 
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                            )''')

sqlite_conn.close()

