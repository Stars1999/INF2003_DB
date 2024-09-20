import sqlite3


def create_connection(db_file):
    """ Database connection to SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("Connection to SQLite DB successful")
    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")
    return conn


def create_tables(conn):
    """ Create all the tables """
    try:
        cursor = conn.cursor()

        # User Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR NOT NULL,
                password VARCHAR NOT NULL,  -- To Hash
                email_add VARCHAR,
                phone_number INT,
                address VARCHAR,
                user_role VARCHAR
            );
        ''')

        # User_History Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS User_History (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INT,
                doc_id INT,
                doc_notes VARCHAR,
                blood_pressure VARCHAR,
                blood_sugar VARCHAR,
                prescribed_med VARCHAR,
                visit_date DATE,
                certificate_id INT,
                FOREIGN KEY(user_id) REFERENCES Users(user_id),
                FOREIGN KEY(certificate_id) REFERENCES Medical_Cert(certificate_id)
            );
        ''')

        # Clinic_Schedule Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Clinic_Schedule (
                schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                time TIME,
                status VARCHAR
            );
        ''')

        # Appointments Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Appointments (
                appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INT,
                schedule_id INT,
                status VARCHAR,
                FOREIGN KEY(user_id) REFERENCES Users(user_id),
                FOREIGN KEY(schedule_id) REFERENCES Clinic_Schedule(schedule_id)
            );
        ''')

        # Medications Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Medications (
                medication_id INTEGER PRIMARY KEY AUTOINCREMENT,
                med_name VARCHAR,
                med_description VARCHAR,
                med_type VARCHAR,
                med_quantity INT
            );
        ''')

        # Medical_Cert Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Medical_Cert (
                certificate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INT,
                doc_id INT,
                issue_date DATE,
                cert_details VARCHAR,
                FOREIGN KEY(user_id) REFERENCES Users(user_id)
            );
        ''')

        # user_health Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_health (
                health_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INT,
                blood_sugar VARCHAR,
                blood_pressure VARCHAR,
                date_log DATE,
                FOREIGN KEY(user_id) REFERENCES Users(user_id)
            );
        ''')

        conn.commit()
        print("All tables created successfully")

    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")

# Main block to run the file standalone and call create_tables
if __name__ == '__main__':
    # Define the path to your SQLite database
    DATABASE = r"INF2003_Proj_DB.db"

    # Create a connection to the database
    conn = create_connection(DATABASE)

    # Call the create_tables function if the connection is successful
    if conn is not None:
        create_tables(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")