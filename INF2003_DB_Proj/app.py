from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import bcrypt
from cryptography.fernet import Fernet
from db_connection import create_connection, create_tables

app = Flask(__name__)

# Required for flash messages and session management
app.secret_key = 'your_secret_key'

# Path to your SQLite database
DATABASE = r"INF2003_Proj_DB.db"

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
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone_number = request.form['phone_number']
        address = request.form['address']
        user_role = 'user'

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Store the encrypted password in the database
            cursor.execute('''
                INSERT INTO Users (username, password, email_add, phone_number, address, user_role)
                VALUES (?, ?, ?, ?, ?, ?);
            ''', (username, hashed_password, email, phone_number, address, user_role))
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
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, password, user_role FROM Users WHERE username = ?;
        ''', (username,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Compare the input password with the decrypted hashed password using bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), user['password']):
                session['username'] = user['username']
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
    if 'username' in session and session['user_role'] == 'user':
        return render_template('user_dashboard.html', username=session['username'])
    return redirect(url_for('home'))

# Doctor dashboard
@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'username' in session and session['user_role'] == 'doctor':
        # Open a database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Fetch distinct medication types from the Medications table
            cursor.execute('SELECT DISTINCT med_type FROM Medications')
            med_types = [row['med_type'] for row in cursor.fetchall()]

            return render_template('doctor_dashboard.html', username=session['username'], med_types=med_types)

        except sqlite3.Error as e:
            flash(f"Error loading dashboard: {e}", 'danger')
            return redirect(url_for('home'))

        finally:
            conn.close()

    return redirect(url_for('home'))

# Handle consolidated POST request for health, medication, and medical certificate data
@app.route('/submit_doctor_form', methods=['POST'])
def submit_doctor_form():
    if 'username' in session and session['user_role'] == 'doctor':
        # Open a database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Retrieve form data
            user_id = request.form['user_id']
            doctor_id = request.form['doc_id']
            doc_notes = request.form['doc_notes']
            blood_pressure = request.form['blood_pressure']
            blood_sugar = request.form['blood_sugar']
            med_name = request.form['med_name']
            issue_date = request.form['issue_date']
            visit_date = request.form['visit_date']
            cert_details = request.form['cert_details']

            # Insert medical certificate data into Medical_Cert table
            cursor.execute('''
                            INSERT INTO Medical_Cert (user_id, doc_id, issue_date, cert_details)
                            VALUES (?, ?, ?, ?)
                        ''', (user_id, doctor_id, issue_date, cert_details))

            # Commit the changes
            conn.commit()

            # Retrieve the certificate_id of the last inserted record
            cert_id = cursor.lastrowid

            # Insert health tracking data into User_History table with the retrieved certificate_id
            cursor.execute('''
                            INSERT INTO User_History (user_id, doc_id, doc_notes, blood_pressure, blood_sugar, prescribed_med, visit_date, certificate_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (user_id, doctor_id, doc_notes, blood_pressure, blood_sugar, med_name, visit_date, cert_id))

            # Commit the changes
            conn.commit()

            flash('All details submitted successfully.', 'success')

        except sqlite3.Error as e:
            flash(f"Error: {e}", 'danger')

        finally:
            conn.close()

        return redirect(url_for('doctor_dashboard'))


@app.route('/get_medications/<med_type>', methods=['GET'])
def get_medications(med_type):
    if 'username' in session and session['user_role'] == 'doctor':
        # Open a database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Fetch medications based on the selected type
            cursor.execute('''
                SELECT med_name FROM Medications WHERE med_type = ?
            ''', (med_type,))
            medications = cursor.fetchall()

            # Convert to a list of dictionaries for JSON response
            med_list = [{'med_name': row['med_name']} for row in medications]

            return jsonify(med_list)

        except sqlite3.Error as e:
            return jsonify({'error': str(e)}), 500

        finally:
            conn.close()

    return jsonify({'error': 'Unauthorized'}), 401

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
