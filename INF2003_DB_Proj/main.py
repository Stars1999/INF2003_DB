from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import bcrypt
from cryptography.fernet import Fernet
from db_connection import create_connection, create_tables

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages and session

# Path to your SQLite database
DATABASE = r"INF2003_Proj_DB.db"

# Symmetric key for AES encryption (this would usually be securely stored)
# For a real application, store this securely in an environment variable or secure vault
aes_key = Fernet.generate_key()
cipher = Fernet(aes_key)


# Function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Home page with login
@app.route('/')
def home():
    return render_template('login.html')

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        userID = request.form['userID']
        password = request.form['password']
        email = request.form['email']
        phone_number = request.form['phone_number']
        address = request.form['address']
        user_role = 'user'

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Encrypt the hashed password using AES-256
        encrypted_password = cipher.encrypt(hashed_password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Store the encrypted password in the database
            cursor.execute('''
                INSERT INTO Users (username, password, email_add, phone_number, address, user_role)
                VALUES (?, ?, ?, ?, ?, ?);
            ''', (userID, encrypted_password, email, phone_number, address, user_role))
            conn.commit()
            # Instead of flash, we pass a flag to the template
            return render_template('register.html', registered=True)
        except sqlite3.Error as e:
            flash(f"Error: {e}", "danger")
        finally:
            conn.close()

    return render_template('register.html')

# Login route
@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        userID = request.form['userID']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, password, user_role FROM Users WHERE username = ?;
        ''', (userID,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Decrypt the stored password
            decrypted_password = cipher.decrypt(user['password']).decode('utf-8')

            # Compare the input password with the decrypted hashed password using bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), decrypted_password.encode('utf-8')):
                session['userID'] = user['username']
                session['user_role'] = user['user_role']

                if user['user_role'] == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Login failed. Incorrect userID or password.', 'danger')
        else:
            flash('Login failed. Incorrect userID or password.', 'danger')

        return redirect(url_for('home'))

# User dashboard
@app.route('/user_dashboard')
def user_dashboard():
    if 'userID' in session and session['user_role'] == 'user':
        return render_template('user_dashboard.html', userID=session['userID'])
    return redirect(url_for('home'))

# Doctor dashboard
@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'userID' in session and session['user_role'] == 'doctor':
        return render_template('doctor_dashboard.html', userID=session['userID'])
    return redirect(url_for('home'))

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
