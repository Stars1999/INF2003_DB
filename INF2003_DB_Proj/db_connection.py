import sqlite3

def create_connection(db_file):
    """ Create a database connection to the SQLite database specified by db_file """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("Connection to SQLite DB successful")
    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")
    return conn

def create_table(conn):
    """ Create table if not exists """
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                Username VARCHAR NOT NULL,
                PhoneNumber INT
            );
        ''')
        conn.commit()
        print("Table creation successful")
    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")
