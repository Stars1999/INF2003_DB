from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import bcrypt
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from db_connection import create_connection, create_tables
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
                INSERT INTO Users (username, password, email_add, phone_number, address, user_role, acc_status)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            ''', (username, hashed_password, email, phone_number, address, user_role, 'enabled'))
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
        conn = get_db_connection()
        cursor = conn.cursor()
        user_id = session['user_id']
        try:
            # Fetch distinct medication types from the Medications table
            cursor.execute('SELECT blood_pressure, blood_sugar, date_log FROM user_health WHERE user_id = ?;',
                           (user_id,))
            rows = cursor.fetchall()
            if rows:
                bp = [float(row['blood_pressure']) for row in rows]
                bs = [float(row['blood_sugar']) for row in rows]
                date = [row['date_log'] for row in rows]
                # Create the bar chart
                plt.bar(date, bp, color='#00bfbf')
                plt.xlabel('Date')
                plt.ylabel('Blood Pressure')
                plt.title('Blood Pressure Over Time')
                plt.xticks(fontsize=5)
                plt.tight_layout()
                plt.savefig('static/images/bpchart.png')  # Save to a static folder within your Flask project
                plt.close()
                plt.bar(date, bs, color='#00bfbf')
                plt.xlabel('Date')
                plt.ylabel('Blood Sugar')
                plt.title('Blood Sugar Over Time')
                plt.xticks(fontsize=5)
                plt.tight_layout()
                plt.savefig('static/images/bschart.png')  # Save to a static folder within your Flask project
                plt.close()
                showchart = True
            else:
                showchart = False

            return render_template('user_dashboard.html', username=session['username'], showchart=showchart)


        except sqlite3.Error as e:
            flash(f"Error loading dashboard: {e}", 'danger')
            return redirect(url_for('home'))

        finally:
            conn.close()

    # return render_template('user_dashboard.html', username="test")
    return redirect(url_for('home'))


# Doctor dashboard page
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
        tomorrow = (datetime.now() + timedelta(days=2)).date()

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

            # Step 1: Check if the user ID exists in the Users table
            cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()

            if not user:
                # If the user does not exist, flash an error message and return to the doctor dashboard
                flash(f"Error: User ID {user_id} does not exist.", 'danger')
                return redirect(url_for('doctor_dashboard'))

            # Step 2: Proceed with form submission since the user exists
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
                        ''',
                           (user_id, doctor_id, doc_notes, blood_pressure, blood_sugar, med_name, visit_date, cert_id))

            # Commit the changes
            conn.commit()

            # Flash a success message
            flash('Doctor form details submitted successfully.', 'success')

        except sqlite3.Error as e:
            # Flash an error message
            flash(f"Error submitting doctor form: {e}", 'danger')

        finally:
            conn.close()

        return redirect(url_for('doctor_dashboard'))


# Route to get user history by userID
@app.route('/get_user_history/<user_id>', methods=['GET'])
def get_user_history(user_id):
    if 'username' in session and session['user_role'] == 'doctor':
        # Open a database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Fetch all history for the given user_id
            cursor.execute('''
                SELECT history_id FROM User_History WHERE user_id = ?
            ''', (user_id,))
            histories = cursor.fetchall()

            # Convert to a list of dictionaries for JSON response
            history_list = [{'history_id': row['history_id']} for row in histories]

            return jsonify(history_list)

        except sqlite3.Error as e:
            return jsonify({'error': str(e)}), 500

        finally:
            conn.close()

    return jsonify({'error': 'Unauthorized'}), 401


@app.route('/get_user_history_top5/<user_id>', methods=['GET'])
def get_user_history_top5(user_id):
    if 'username' in session and session['user_role'] == 'doctor':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Fetch the top 5 history records for the given user_id and join to fetch doctor's name
            cursor.execute('''
                            SELECT uh.doc_notes, uh.blood_pressure, uh.blood_sugar, uh.visit_date, 
                                   d.username AS doctor_name, 
                                   p.username AS patient_name, 
                                   uh.prescribed_med
                            FROM User_History uh
                            JOIN Users d ON uh.doc_id = d.user_id  -- Join to get doctor's name
                            JOIN Users p ON uh.user_id = p.user_id  -- Join to get patient's name
                            WHERE uh.user_id = ?
                            ORDER BY uh.visit_date DESC
                            LIMIT 5;
                        ''', (user_id,))
            history_records = cursor.fetchall()

            # Format the data for JSON response
            records = [
                {
                    'doc_notes': record['doc_notes'],
                    'blood_pressure': record['blood_pressure'],
                    'blood_sugar': record['blood_sugar'],
                    'visit_date': record['visit_date'],
                    'doctor_name': record['doctor_name'],  # Doctor's name
                    'patient_name': record['patient_name'],  # Patient's name
                    'prescribed_med': record['prescribed_med']  # Prescribed medication
                } for record in history_records
            ]

            return jsonify(records)

        except sqlite3.Error as e:
            return jsonify({'error': str(e)}), 500

        finally:
            conn.close()

    return jsonify({'error': 'Unauthorized'}), 401


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


# Settings page
@app.route('/settings')
def settings():
    if 'username' in session and (session['user_role'] == 'user' or session['user_role'] == 'doctor'):
        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL query to fetch user details by username from the session
        query = "SELECT email_add, phone_number, address FROM users WHERE username = ?"
        cursor.execute(query, (session['username'],))
        user_data = cursor.fetchone()

        if user_data:
            # user_data[0] = email, user_data[1] = phone_number, user_data[2] = address
            email, phone_number, address = user_data

            # Pass the fetched user details to the template
            return render_template(
                'settings.html',
                username=session['username'],
                email=email,
                phone_number=phone_number,
                address=address,
                role=session['user_role']
            )
        else:
            # If no user data is found, redirect to home
            return redirect(url_for('home'))

    # Redirect to home if the user is not authenticated
    return redirect(url_for('home'))


@app.route('/update_account', methods=['POST'])
def update_account():
    if 'username' not in session:
        flash('You are not logged in.', 'danger')
        return redirect(url_for('login'))
    # Retrieve form data
    email = request.form.get('email')
    phone_number = request.form.get('phone_number')
    address = request.form.get('address')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm-password')
    # Get the current logged-in user's username from the session
    username = session['username']
    # Validation checks
    if not email or not phone_number or not address:
        flash('Email, phone number, and address are required.', 'danger')
        return redirect(url_for('settings'))
    if password and password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('settings'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Update email, phone number, and address
        cursor.execute('''
            UPDATE Users 
            SET email_add = ?, phone_number = ?, address = ? 
            WHERE username = ?
        ''', (email, phone_number, address, username))
        # Update password if provided
        if password:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('UPDATE Users SET password = ? WHERE username = ?', (hashed_password, username))
        conn.commit()
        return render_template('login.html', updated=True)
    except sqlite3.Error as e:
        flash(f"Error updating account: {e}", 'danger')
    finally:
        conn.close()
    return redirect(url_for('settings'))


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


@app.route('/user_health', methods=['POST'])
def user_health():
    if 'username' in session:
        username = session['username']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Step 1: Retrieve user_id based on the username stored in the session
        try:
            query = "SELECT user_id FROM users WHERE username = ?"
            cursor.execute(query, (username,))
            user_data = cursor.fetchone()

            if not user_data:
                flash('User not found!', 'danger')
                return redirect(url_for('user_health'))

            user_id = user_data[0]  # Extract the user_id from the fetched data

            # Step 2: Get blood pressure and blood sugar from the submitted form
            blood_pressure = request.form.get('blood-pressure')
            blood_sugar = request.form.get('blood-sugar')

            if not blood_pressure or not blood_sugar:
                flash('Please enter valid blood pressure and blood sugar values.', 'danger')
                return redirect(url_for('user_health'))

            # Step 3: Prepare the datetime for logging
            date_log = datetime.now()

            # Step 4: Insert the new health record into the user_health table
            insert_query = '''
                INSERT INTO user_health (user_id, blood_sugar, blood_pressure, date_log)
                VALUES (?, ?, ?, ?)
            '''
            cursor.execute(insert_query, (user_id, blood_sugar, blood_pressure, date_log))

            conn.commit()
            flash('Health data inserted successfully!', 'success')

        except sqlite3.Error as e:
            conn.rollback()  # Rollback if there's an error
            flash(f"Database error: {e}", 'danger')

        finally:
            conn.close()  # Close the connection

    return redirect(url_for('user_dashboard'))


# Appointments Page
@app.route('/available-dates')
def get_available_dates():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Get the user_id from the session
        user_id = session.get('user_id')

        # Fetch dates and times for appointments specific to the logged-in user
        cursor.execute("""
            SELECT cs.date, cs.time, 
                   COUNT(a.appointment_id) as appointment_count, 
                   COUNT(cs.schedule_id) as total_slots,
                   SUM(CASE WHEN cs.status = 'booked' THEN 1 ELSE 0 END) as booked_slots
            FROM clinic_schedule cs
            LEFT JOIN appointments a ON cs.schedule_id = a.schedule_id AND a.user_id = ?
            GROUP BY cs.date, cs.time
        """, (user_id,))
        rows = cursor.fetchall()

        # Dictionary to store availability data
        availability_data = {}

        for row in rows:
            date_str = row['date']  # e.g., '2024-09-14'
            time_str = row['time']  # e.g., '10:00'
            appointment_count = row['appointment_count']  # Number of appointments at this time
            total_slots = row['total_slots']  # Total time slots for that date
            booked_slots = row['booked_slots']  # Number of booked time slots

            # Initialize the dictionary for this date if it doesn't exist yet
            if date_str not in availability_data:
                fully_booked = (booked_slots == total_slots)
                availability_data[date_str] = {
                    'fullyBooked': fully_booked,
                    'appointments': []  # List to store appointment times
                }

            # Add the appointment time if there is an appointment
            if appointment_count > 0:
                availability_data[date_str]['appointments'].append(time_str)
                # If we add an appointment, ensure the day is not fully booked
                availability_data[date_str]['fullyBooked'] = False

        return jsonify(availability_data)

    except sqlite3.Error as e:
        print(f"Error fetching available dates: {e}")
        return jsonify({}), 500  # Return an empty response in case of error

    finally:
        connection.close()


@app.route('/appointment')
def appointment():
    if 'username' in session and session['user_role'] == 'user':
        return render_template('appointment.html', username=session['username'])


@app.route('/book-appointment', methods=['POST'])
def book_appointment():
    # Get the selected date and time slot from the form
    date_str = request.form.get('date')
    time_slot = request.form.get('timeslot')
    user_id = session.get('user_id')

    # Ensure the user is logged in
    if not user_id:
        flash('Please log in to book an appointment.', 'danger')
        return redirect(url_for('home'))

    # Convert the date to yyyy-mm-dd format
    try:
        formatted_date = datetime.strptime(date_str, '%a %b %d %Y').strftime('%Y-%m-%d')
    except ValueError:
        flash('Invalid date format. Please try again.', 'danger')
        return redirect(url_for('appointment'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Step 1: Fetch the corresponding schedule_id from the clinic_schedule table
        cursor.execute("""
            SELECT schedule_id FROM clinic_schedule
            WHERE date = ? AND time = ?
        """, (formatted_date, time_slot))
        schedule = cursor.fetchone()

        # Check if a valid schedule was found
        if not schedule:
            flash('No valid schedule found for the selected date and time.', 'danger')
            return redirect(url_for('appointment'))

        schedule_id = schedule['schedule_id']

        # Step 2: Update the clinic_schedule status to 'booked'
        cursor.execute("""
            UPDATE clinic_schedule
            SET status = 'booked'
            WHERE schedule_id = ?
        """, (schedule_id,))

        # Step 3: Insert a new row in the appointments table
        cursor.execute("""
            INSERT INTO appointments (user_id, schedule_id, status)
            VALUES (?, ?, 'booked')
        """, (user_id, schedule_id))

        # Commit the changes
        connection.commit()

        flash('Appointment booked successfully!', 'success')

    except sqlite3.Error as e:
        connection.rollback()
        flash(f'Error booking appointment: {e}', 'danger')

    finally:
        connection.close()

    return redirect(url_for('appointment'))


# Check if the user has an appointment on the selected date
@app.route('/check-appointment', methods=['GET'])
def check_appointment():
    try:
        date = request.args.get('date')  # Get the selected date from the frontend
        user_id = session.get('user_id')  # Get the current user ID from the session

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401

        # Convert the date into YYYY-MM-DD format
        parsed_date = datetime.strptime(date, '%a %b %d %Y').strftime('%Y-%m-%d')
        print(parsed_date)
        # parsed_date = date
        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if the user has an appointment on this date
        cursor.execute("""
            SELECT a.appointment_id, cs.time FROM appointments a
            JOIN clinic_schedule cs ON a.schedule_id = cs.schedule_id
            WHERE cs.date = ? AND a.user_id = ?
        """, (parsed_date, user_id))

        appointment = cursor.fetchone()

        if appointment:
            # User already has an appointment
            return jsonify({
                'hasAppointment': True,
                'appointmentTime': appointment['time'],
                'message': 'You already have an appointment for today.'
            })
        else:
            # Fetch available time slots for booking if no appointment exists
            cursor.execute("""
                SELECT time FROM clinic_schedule
                WHERE date = ? AND status = 'available'
            """, (parsed_date,))
            available_time_slots = [row['time'] for row in cursor.fetchall()]

            return jsonify({
                'hasAppointment': False,
                'availableTimeSlots': available_time_slots
            })

    except Exception as e:
        print(f"Error checking appointment: {str(e)}")
        return "Internal Server Error", 500

    finally:
        connection.close()


@app.route('/available_timeslots')
def get_available_timeslots():
    try:
        date = request.args.get('date')  # Get the selected date from the frontend
        print(f"Fetching available time slots for date: {date}")  # Log the date

        # Convert the date into YYYY-MM-DD format
        formatted_date = datetime.strptime(date, '%a %b %d %Y').strftime('%Y-%m-%d')
        print(f"Fetching available time slots for date: {date}")
        print(f"Formatted date for query: {formatted_date}")

        connection = get_db_connection()

        # Fetch all available time slots directly from the clinic_schedule for the selected date
        clinic_schedule_query = """
            SELECT * FROM clinic_schedule WHERE date = ? AND status = 'available'
            """
        available_time_slots = [row['time'] for row in connection.execute(clinic_schedule_query, (formatted_date,))]

        print(f"Remaining slots for {formatted_date}: {available_time_slots}")  # Log the available slots

        return jsonify({'timeslots': available_time_slots})

    except Exception as e:
        print(f"Error fetching time slots: {str(e)}")  # Log the error
        return "Internal Server Error", 500  # Return a 500 response


@app.route('/cancel-appointment', methods=['POST'])
def cancel_appointment():
    data = request.json
    date = data.get('date')
    time = data.get('time')
    user_id = session.get('user_id')

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Convert the incoming date to yyyy-mm-dd format
        formatted_date = datetime.strptime(date, '%a %b %d %Y').strftime('%Y-%m-%d')

        # Log the incoming request data
        print(f"Cancel request for date: {formatted_date}, time: {time}, user_id: {user_id}")

        # Find the schedule_id for the selected date and time
        cursor.execute("""
            SELECT schedule_id FROM clinic_schedule
            WHERE date = ? AND time = ?
        """, (formatted_date, time))
        schedule = cursor.fetchone()

        if not schedule:
            print("No appointment found for the provided date and time.")
            return jsonify({'error': 'No appointment found'}), 400

        schedule_id = schedule['schedule_id']

        # Delete the appointment from the appointments table
        cursor.execute("""
            DELETE FROM appointments WHERE user_id = ? AND schedule_id = ?
        """, (user_id, schedule_id))

        # Update the clinic schedule status back to 'available'
        cursor.execute("UPDATE clinic_schedule SET status = 'available' WHERE schedule_id = ?", (schedule_id,))

        connection.commit()

        print("Appointment canceled successfully.")
        return jsonify({'success': 'Appointment canceled successfully'})

    except sqlite3.Error as e:
        connection.rollback()
        print(f"Error canceling appointment: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        connection.close()


@app.route('/edit-appointment', methods=['POST'])
def edit_appointment():
    data = request.json
    print("Received data:", data)  # Log the incoming data for debugging

    # Extract the date, current time, and new time from the JSON data
    date = data.get('date')
    current_time = data.get('currentTime')
    new_time = data.get('newTime')
    user_id = session.get('user_id')

    if not date:
        return jsonify({'error': 'Date is missing'}), 400  # Check if the date is missing and return error

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Convert the incoming date to yyyy-mm-dd format
        formatted_date = datetime.strptime(date, '%a %b %d %Y').strftime('%Y-%m-%d')

        print(
            f"Edit request for user_id: {user_id}, current_time: {current_time}, new_time: {new_time}, date: {formatted_date}")

        # Find the current schedule_id for the user's existing appointment
        cursor.execute("""
            SELECT a.schedule_id 
            FROM appointments a
            JOIN clinic_schedule cs ON a.schedule_id = cs.schedule_id
            WHERE a.user_id = ? AND cs.date = ? AND cs.time = ?
        """, (user_id, formatted_date, current_time))
        current_schedule = cursor.fetchone()

        if not current_schedule:
            print("No appointment found for the provided date and current time.")
            return jsonify({'error': 'No appointment found to edit.'}), 400

        current_schedule_id = current_schedule['schedule_id']

        # Find the new schedule_id for the selected time
        cursor.execute("""
            SELECT schedule_id 
            FROM clinic_schedule 
            WHERE date = ? AND time = ? AND status = 'available'
        """, (formatted_date, new_time))
        new_schedule = cursor.fetchone()

        if not new_schedule:
            print("No available time slot for the selected time.")
            return jsonify({'error': 'No available time slot for the selected time.'}), 400

        new_schedule_id = new_schedule['schedule_id']

        # Update the clinic schedule:
        # 1. Set the old time slot status back to 'available'
        # 2. Set the new time slot status to 'booked'
        cursor.execute("UPDATE clinic_schedule SET status = 'available' WHERE schedule_id = ?", (current_schedule_id,))
        cursor.execute("UPDATE clinic_schedule SET status = 'booked' WHERE schedule_id = ?", (new_schedule_id,))

        # Update the appointment to the new schedule_id
        cursor.execute("""
            UPDATE appointments
            SET schedule_id = ?
            WHERE user_id = ? AND schedule_id = ?
        """, (new_schedule_id, user_id, current_schedule_id))

        # Commit the changes to the database
        connection.commit()

        print("Appointment edited successfully.")
        return jsonify({'success': 'Appointment edited successfully.'})

    except sqlite3.Error as e:
        connection.rollback()
        print(f"Error editing appointment: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        connection.close()


# Function to create today's appointment
@app.route('/get_today_appointments', methods=['GET'])
def get_today_appointments():
    if 'username' in session and session['user_role'] == 'doctor':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Use a specific test date for testing
            today = datetime.now().date()

            # Fetch appointments for the test date
            cursor.execute('''
                           SELECT a.user_id, u.username, cs.date, cs.time
                           FROM Appointments a
                           JOIN Users u ON a.user_id = u.user_id
                           JOIN Clinic_Schedule cs ON a.schedule_id = cs.schedule_id
                           WHERE cs.date = ? AND cs.status = 'booked';
                       ''', (today,))
            appointments = cursor.fetchall()

            # Prepare the result as a list of dictionaries
            appointments_list = [{'patient': row['username'], 'date': row['date'], 'time': row['time']} for row in
                                 appointments]

            return jsonify(appointments_list)

        except sqlite3.Error as e:
            return jsonify({'error': str(e)}), 500

        finally:
            conn.close()

    return jsonify({'error': 'Unauthorized'}), 401


# Function to mark patient as a no-show
@app.route('/mark_no_show', methods=['POST'])
def mark_no_show():
    if 'username' in session and session['user_role'] == 'doctor':
        data = request.get_json()
        date = data.get('date')
        time = data.get('time')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # First, find the schedule_id based on the date and time
            cursor.execute('''
                SELECT schedule_id FROM Clinic_Schedule WHERE date = ? AND time = ?;
            ''', (date, time))
            schedule = cursor.fetchone()

            if schedule:
                schedule_id = schedule['schedule_id']

                # Update the status in the Appointments table
                cursor.execute('''
                    UPDATE Appointments SET status = 'No-Show' 
                    WHERE schedule_id = ?;
                ''', (schedule_id,))

                # Commit the changes
                conn.commit()

                # Update the status in the Clinic_Schedule table
                cursor.execute('''
                    UPDATE Clinic_Schedule SET status = 'No-Show'
                    WHERE schedule_id = ?;
                ''', (schedule_id,))

                conn.commit()

                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'message': 'Schedule not found'})

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return jsonify({'success': False, 'error': str(e)})
        finally:
            conn.close()

    return jsonify({'success': False, 'message': 'Unauthorized'}), 401


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
