import sqlite3

def create_month_sales_table():
    conn = sqlite3.connect('month.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS month_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            earnings REAL,
            costs REAL,
            net_earnings REAL
        )
    ''')
    conn.commit()
    conn.close()

create_month_sales_table()