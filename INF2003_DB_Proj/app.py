from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import bcrypt
from datetime import datetime, timedelta
from db_connection import create_connection

app = Flask(__name__)

# Required for flash messages and session management
app.secret_key = 'your_secret_key'

# Path to your SQLite database
DATABASE = r"INF2003_Proj_DB.db"

# Function to connect to the database
def get_db_connection():
    conn = create_connection(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Home page with login
@app.route('/')
def home():
    get_db_connection()
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

        # Modify the query to also fetch the user_id
        cursor.execute('''
            SELECT user_id, username, password, user_role FROM Users WHERE username = ?;
        ''', (username,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Compare the input password with the hashed password using bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), user['password']):
                session['user_id'] = user['user_id']  # Store user_id in session
                session['username'] = user['username']
                session['user_role'] = user['user_role']

                if user['user_role'] == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Login failed. Incorrect username or password.', 'danger')
        else:
            flash('Login failed. Incorrect username or password.', 'danger')

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

            # Get the doctor ID (user_id) from the session
            doctor_id = session['user_id']

            return render_template('doctor_dashboard.html', username=session['username'],
                                   med_types=med_types, doctor_id=doctor_id)

        except sqlite3.Error as e:
            flash(f"Error loading dashboard: {e}", 'danger')
            return redirect(url_for('home'))

        finally:
            conn.close()

    return redirect(url_for('home'))


@app.route('/create_schedule', methods=['POST'])
def create_schedule():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).date()

        # Check if there's already a schedule for tomorrow
        cursor.execute('SELECT * FROM Clinic_Schedule WHERE date = ?', (tomorrow,))
        existing_rows = cursor.fetchall()

        if existing_rows:
            # If rows already exist for tomorrow, return a message indicating no action was taken
            flash("Tomorrow's schedule already exists.", 'info')
            return redirect(url_for('doctor_dashboard'))

        # Define the time slots
        time_slots = [
            ('10:00', '12:00'),  # Morning session (before lunch)
            ('14:00', '17:00')  # Afternoon session (after lunch)
        ]

        # Insert time slots for the morning and afternoon
        for time_range in time_slots:
            start_time = datetime.strptime(time_range[0], '%H:%M')
            end_time = datetime.strptime(time_range[1], '%H:%M')

            while start_time < end_time:
                # Insert a 30-minute interval into Clinic_Schedule
                cursor.execute('''
                    INSERT INTO Clinic_Schedule (date, time, status)
                    VALUES (?, ?, ?);
                ''', (tomorrow, start_time.strftime('%H:%M'), 'available'))

                # Increment the start time by 30 minutes
                start_time += timedelta(minutes=30)

        # Commit the transaction
        conn.commit()
        flash("Tomorrow's schedule created successfully!", 'success')
        return redirect(url_for('doctor_dashboard'))

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash(f"Error creating schedule: {e}", 'danger')
        return redirect(url_for('doctor_dashboard'))

    finally:
        conn.close()


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

#Settings
@app.route('/settings')
def settings():
    if 'username' in session and session['user_role'] == 'user':
        return render_template('settings.html', username=session['username'])
    return redirect(url_for('home'))

# Delete account route
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'username' in session:
        username = session['username']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Delete user from the database
            cursor.execute('DELETE FROM Users WHERE username = ?', (username,))
            conn.commit()

            flash('Your account has been deleted successfully.', 'success')

            # Clear the session after account deletion
            session.clear()

        except sqlite3.Error as e:
            flash(f"Error deleting account: {e}", 'danger')

        finally:
            conn.close()

    return redirect(url_for('home'))

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
