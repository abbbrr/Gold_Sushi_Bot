import sqlite3


sqlite_conn = sqlite3.connect('products.db')
sqlite_cursor = sqlite_conn.cursor()

sqlite_cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                            user_id INTEGER,
                            product TEXT,
                            quantity REAL,
                            PRIMARY KEY (user_id, product)
                            )''')

sqlite_conn.close()

