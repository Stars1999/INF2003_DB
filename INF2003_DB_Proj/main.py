import sqlite3
from db_connection import create_connection, create_tables


def show_menu():
    print("\n--- Main Menu ---")
    print("1) Login")
    print("2) Register")
    print("0) Exit")


def register_user(conn):
    username = input("Enter username: ")
    password = input("Enter password: ")  # To add hashing afterwards
    email = input("Enter email: ")
    phone_number = input("Enter phone number: ")
    address = input("Enter address: ")
    user_role = input("Enter user role (doctor/user): ")

    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Users (username, password, email_add, phone_number, address, user_role)
            VALUES (?, ?, ?, ?, ?, ?);
        ''', (username, password, email, phone_number, address, user_role))
        conn.commit()
        print(f"User {username} registered successfully!")
    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")


def login_user(conn):
    username = input("Enter username: ")
    password = input("Enter password: ")  # To add hashing afterwards

    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, user_role FROM Users WHERE username = ? AND password = ?;
        ''', (username, password))
        user = cursor.fetchone()

        if user:
            username, user_role = user
            if user_role == 'user':
                print(f"Welcome, {username}!")
            elif user_role == 'doctor':
                print(f"Welcome Doctor {username}!")
        else:
            print("Login failed. Incorrect username or password.")
    except sqlite3.Error as e:
        print(f"The error '{e}' occurred")


def main():
    database = r"INF2003_Proj_DB.db"
    conn = create_connection(database)

    if conn:
        create_tables(conn)  # Check if database tables are created

        while True:
            show_menu()
            choice = input("Select an option: ")

            if choice == "1":
                login_user(conn)
            elif choice == "2":
                register_user(conn)
            elif choice == "0":
                print("Exiting the program. Goodbye!")
                break
            else:
                print("Invalid option, please try again.")

        conn.close()


if __name__ == "__main__":
    main()
