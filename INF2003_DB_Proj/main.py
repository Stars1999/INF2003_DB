from db_connection import create_connection, create_table

def insert_user(conn, username, phone_number):
    """ Insert a new user into the user table """
    sql = ''' INSERT INTO user(Username, PhoneNumber)
              VALUES(?, ?) '''
    cur = conn.cursor()
    cur.execute(sql, (username, phone_number))
    conn.commit()
    return cur.lastrowid

def print_users(conn):
    """ Print all rows in the user table """
    cur = conn.cursor()
    cur.execute("SELECT * FROM user")
    rows = cur.fetchall()
    for row in rows:
        print(row)

def check_user_exists_ID(conn, user_id):
    """ Check if a user exists with the given UserID """
    cur = conn.cursor()
    cur.execute("SELECT UserID, Username, PhoneNumber FROM user WHERE UserID = ?", (user_id,))
    return cur.fetchone()  # Returns None if no match is found

def check_user_exists_ID_Username(conn, user_id, username):
    """ Check if a user exists with the given UserID and Username """
    cur = conn.cursor()
    cur.execute("SELECT * FROM user WHERE UserID = ? AND Username = ?", (user_id, username))
    return cur.fetchone()  # Returns None if no match is found

def update_user(conn, user_id, username, new_phone_number):
    """ Update a user's phone number by user_id and username """
    sql = ''' UPDATE user
              SET PhoneNumber = ?
              WHERE UserID = ? AND Username = ?'''
    cur = conn.cursor()
    updated = cur.execute(sql, (new_phone_number, user_id, username))
    conn.commit()
    return cur.rowcount  # Returns the number of rows affected

def delete_user(conn, user_id):
    """ Delete a user by UserID """
    sql = 'DELETE FROM user WHERE UserID = ?'
    cur = conn.cursor()
    cur.execute(sql, (user_id,))
    conn.commit()
    return cur.rowcount  # Returns the number of rows affected

def main():
    database = "INF2003_DB.db"

    # create a database connection
    conn = create_connection(database)
    if conn is not None:
        create_table(conn)

        while True:
            print("\nMenu:")
            print("1) Print Users")
            print("2) Insert User")
            print("3) Update User")
            print("4) Delete User")
            print("5) Exit")
            choice = input("Enter choice: ")

            if choice == '1':
                print_users(conn)
            elif choice == '2':
                username = input("Enter username to insert: ")
                phone_number = input("Enter phone number to insert: ")
                try:
                    phone_number = int(phone_number)
                    insert_user(conn, username, phone_number)
                    print(f"User '{username}' with phone number '{phone_number}' added successfully.")
                except ValueError:
                    print("Invalid phone number. Please enter a valid integer.")
            elif choice == '3':
                while True:
                    user_id = input("Enter user ID to update: ")
                    username = input("Enter username associated with the ID: ")
                    if check_user_exists_ID_Username(conn, user_id, username):
                        new_phone_number = input("Enter new phone number: ")
                        try:
                            new_phone_number = int(new_phone_number)
                            if update_user(conn, user_id, username, new_phone_number) > 0:
                                print("User phone number updated successfully.")
                                break
                        except ValueError:
                            print("Invalid phone number. Please enter a valid integer.")
                    else:
                        print("No user found with the given ID and username combination. Please try again.")
            elif choice == '4':
                user_id = input("Enter user ID to delete: ")
                user = check_user_exists_ID(conn, user_id)
                if user:
                    print(f"User Found: ID = {user[0]}, Username = {user[1]}, Phone Number = {user[2]}")
                    confirm = input("Are you sure you want to delete this user? (y/n): ")
                    if confirm.lower() == 'y':
                        if delete_user(conn, user_id) > 0:
                            print("User deleted successfully.")
                        else:
                            print("Failed to delete user.")
                    else:
                        print("Deletion canceled.")
                else:
                    print("No user found with the given ID. Please try again.")
            elif choice == '5':
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please choose 1, 2, 3, or 4.")
    else:
        print("Error! cannot create the database connection.")

if __name__ == '__main__':
    main()
