from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import bcrypt
from datetime import datetime, timedelta # For handling dates and times
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# Required for flash messages and session management
app.secret_key = 'your_secret_key'

# # Path to your SQLite database
# DATABASE = r"INF2003_Proj_DB.db"

# Initialize Firebase
cred = credentials.Certificate("inf2003-2ba47-firebase-adminsdk-kwxph-97051cd15f.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


@app.route('/')
def home():
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/appointment')
def appointment():
    if 'username' in session and session['user_role'] == 'user':
        return render_template('appointment.html', username=session['username'])
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

        # Store the user in Firestore
        users_ref = db.collection('Users')
        try:
            users_ref.add({
                'username': username,
                'password': hashed_password.decode('utf-8'),  # Convert hash to string
                'email_add': email,
                'phone_number': phone_number,
                'address': address,
                'user_role': user_role,
                'acc_status': 'enabled'
            })
            return render_template('register.html', registered=True)
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Get the user from Firestore
        users_ref = db.collection('Users')
        user_query = users_ref.where('username', '==', username).stream()

        user = None
        for u in user_query:
            user = u
            break

        if user:
            user_data = user.to_dict()
            # Check if the password matches
            if bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
                # Store user information in the session
                session['user_id'] = user.id
                session['username'] = user_data['username']
                session['user_role'] = user_data['user_role']

                if user_data['user_role'] == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                else:
                    print(session)
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Incorrect password.', 'danger')
        else:
            flash('User not found.', 'danger')

    return redirect(url_for('home'))


@app.route('/user_dashboard')
def user_dashboard():
    if 'username' in session and session['user_role'] == 'user':
        user_id = session['user_id']  # Assume user_id is stored in the session after login

        try:
            # Fetch user health data from Firestore
            user_health_ref = db.collection('user_health').where('user_id', '==', user_id).stream()
            rows = [doc.to_dict() for doc in user_health_ref]

            if rows:
                bp = [float(row['blood_pressure']) for row in rows]
                bs = [float(row['blood_sugar']) for row in rows]
                date = [row['date_log'] for row in rows]  # Ensure 'date_log' is in proper format (e.g., string)

                # Create Blood Pressure chart
                plt.bar(date, bp, color='#00bfbf')
                plt.xlabel('Date')
                plt.ylabel('Blood Pressure')
                plt.title('Blood Pressure Over Time')
                plt.xticks(fontsize=5)
                plt.tight_layout()
                plt.savefig('static/images/bpchart.png')  # Save to static folder within Flask
                plt.close()

                # Create Blood Sugar chart
                plt.bar(date, bs, color='#00bfbf')
                plt.xlabel('Date')
                plt.ylabel('Blood Sugar')
                plt.title('Blood Sugar Over Time')
                plt.xticks(fontsize=5)
                plt.tight_layout()
                plt.savefig('static/images/bschart.png')  # Save to static folder within Flask
                plt.close()

                showchart = True
            else:
                showchart = False

            return render_template('user_dashboard.html', username=session['username'], showchart=showchart)

        except Exception as e:
            flash(f"Error loading dashboard: {e}", 'danger')
            return redirect(url_for('home'))

    return redirect(url_for('home'))


@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Fetch distinct medication types from Firestore
            medications_ref = db.collection('Medications')
            distinct_med_types = medications_ref.stream()

            # Extract distinct medication types
            med_types = list(set([doc.to_dict()['med_type'] for doc in distinct_med_types]))

            # Get the doctor ID (user_id) from the session
            doctor_id = session['user_id']

            return render_template('doctor_dashboard.html', username=session['username'], med_types=med_types,
                                   doctor_id=doctor_id)

        except Exception as e:
            flash(f"Error loading dashboard: {e}", 'danger')
            return redirect(url_for('home'))

    return redirect(url_for('home'))


@app.route('/create_schedule', methods=['POST'])
def create_schedule():
    try:
        # Get tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()

        # Check if there's already a schedule for tomorrow
        schedules_ref = db.collection('Clinic_Schedule').where('date', '==', tomorrow).stream()
        existing_rows = [doc.to_dict() for doc in schedules_ref]

        if existing_rows:
            flash("Tomorrow's schedule already exists.", 'info')
            return redirect(url_for('doctor_dashboard'))

        # Define the time slots
        time_slots = [('10:00', '12:00'), ('14:00', '17:00')]

        # Add time slots to Firestore
        for time_range in time_slots:
            start_time = datetime.strptime(time_range[0], '%H:%M')
            end_time = datetime.strptime(time_range[1], '%H:%M')

            while start_time < end_time:
                # Insert a 30-minute interval into Firestore
                db.collection('Clinic_Schedule').add({
                    'date': tomorrow,
                    'time': start_time.strftime('%H:%M'),
                    'status': 'available'
                })

                # Increment the start time by 30 minutes
                start_time += timedelta(minutes=30)

        flash("Tomorrow's schedule created successfully!", 'success')
        return redirect(url_for('doctor_dashboard'))

    except Exception as e:
        flash(f"Error creating schedule: {e}", 'danger')
        return redirect(url_for('doctor_dashboard'))


@app.route('/submit_doctor_form', methods=['POST'])
def submit_doctor_form():
    if 'username' in session and session['user_role'] == 'doctor':
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

            # Step 1: Check if the user ID exists in the Users collection
            user_ref = db.collection('Users').document(user_id)
            user = user_ref.get()

            if not user.exists:
                # If the user does not exist, flash an error message and return to the doctor dashboard
                flash(f"Error: User ID {user_id} does not exist.", 'danger')
                return redirect(url_for('doctor_dashboard'))

            # Step 2: Proceed with form submission since the user exists
            # Insert medical certificate data into Medical_Cert collection
            cert_data = {
                'user_id': user_id,
                'doc_id': doctor_id,
                'issue_date': issue_date,
                'cert_details': cert_details
            }
            cert_ref = db.collection('Medical_Cert').add(cert_data)

            # Retrieve the certificate_id (Firestore document ID) of the last inserted record
            cert_id = cert_ref[1].id

            # Step 3: Insert health tracking data into User_History collection with the retrieved certificate_id
            history_data = {
                'user_id': user_id,
                'doc_id': doctor_id,
                'doc_notes': doc_notes,
                'blood_pressure': blood_pressure,
                'blood_sugar': blood_sugar,
                'prescribed_med': med_name,
                'visit_date': visit_date,
                'certificate_id': cert_id
            }
            db.collection('User_History').add(history_data)

            # Flash a success message
            flash('Doctor form details submitted successfully.', 'success')

        except Exception as e:
            # Flash an error message
            flash(f"Error submitting doctor form: {e}", 'danger')

        return redirect(url_for('doctor_dashboard'))


@app.route('/get_user_history/<user_id>', methods=['GET'])
def get_user_history(user_id):
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Fetch all history for the given user_id from Firestore
            user_history_ref = db.collection('User_History').where('user_id', '==', user_id).stream()

            # Convert to a list of dictionaries for JSON response
            history_list = [{'history_id': doc.id} for doc in user_history_ref]  # Use document ID for history_id
            return jsonify(history_list)

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Unauthorized'}), 401


@app.route('/get_user_history_top5/<user_id>', methods=['GET'])
def get_user_history_top5(user_id):
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Fetch the top 5 history records for the given user_id from Firestore
            user_history_ref = db.collection('User_History')\
                                 .where('user_id', '==', user_id)\
                                 .order_by('visit_date', direction=firestore.Query.DESCENDING)\
                                 .limit(5).stream()

            history_records = [doc.to_dict() for doc in user_history_ref]

            # Fetch doctor and patient names (from Users collection)
            doctor_names = {history['doc_id']: db.collection('Users').document(history['doc_id']).get().to_dict()['username'] for history in history_records}
            patient_names = {user_id: db.collection('Users').document(user_id).get().to_dict()['username']}  # All histories are for the same patient

            # Format the data for JSON response
            records = [
                {
                    'doc_notes': record['doc_notes'],
                    'blood_pressure': record['blood_pressure'],
                    'blood_sugar': record['blood_sugar'],
                    'visit_date': record['visit_date'],
                    'doctor_name': doctor_names[record['doc_id']],  # Get doctor's name from the lookup
                    'patient_name': patient_names[user_id],  # Patient's name (all same user_id)
                    'prescribed_med': record['prescribed_med']
                } for record in history_records
            ]

            return jsonify(records)

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Unauthorized'}), 401


@app.route('/get_medications/<med_type>', methods=['GET'])
def get_medications(med_type):
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Fetch medications based on the selected type from Firestore
            meds_ref = db.collection('Medications').where('med_type', '==', med_type).stream()

            # Convert Firestore documents to a list of dictionaries for JSON response
            med_list = [{'med_name': doc.to_dict()['med_name']} for doc in meds_ref]

            return jsonify(med_list)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Unauthorized'}), 401


@app.route('/settings')
def settings():
    if 'username' in session and (session['user_role'] == 'user' or session['user_role'] == 'doctor'):
        try:
            # Fetch user details by username from Firestore
            user_ref = db.collection('Users').where('username', '==', session['username']).stream()
            user_data = [doc.to_dict() for doc in user_ref]

            if user_data:
                user = user_data[0]  # Get the first document
                email = user.get('email_add')
                phone_number = user.get('phone_number')
                address = user.get('address')

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
                return redirect(url_for('home'))
        except Exception as e:
            flash(f"Error retrieving user settings: {e}", 'danger')
            return redirect(url_for('home'))

    return redirect(url_for('home'))


@app.route('/update_account', methods=['POST'])
def update_account():
    if 'username' not in session:
        flash('You are not logged in.', 'danger')
        return redirect(url_for('login'))

    email = request.form.get('email')
    phone_number = request.form.get('phone_number')
    address = request.form.get('address')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm-password')
    username = session['username']

    if not email or not phone_number or not address:
        flash('Email, phone number, and address are required.', 'danger')
        return redirect(url_for('settings'))

    if password and password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('settings'))

    try:
        # Update email, phone number, and address in Firestore
        user_ref = db.collection('Users').where('username', '==', username).get()
        if user_ref:
            user_doc_id = user_ref[0].id  # Get document ID for update
            db.collection('Users').document(user_doc_id).update({
                'email_add': email,
                'phone_number': phone_number,
                'address': address
            })

            if password:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                db.collection('Users').document(user_doc_id).update({'password': hashed_password})

        return render_template('login.html', updated=True)
    except Exception as e:
        flash(f"Error updating account: {e}", 'danger')

    return redirect(url_for('settings'))


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'username' in session:
        username = session['username']

        try:
            # Delete user document from Firestore
            user_ref = db.collection('Users').where('username', '==', username).get()
            if user_ref:
                user_doc_id = user_ref[0].id
                db.collection('Users').document(user_doc_id).delete()

            flash('Your account has been deleted successfully.', 'success')
            session.clear()

        except Exception as e:
            flash(f"Error deleting account: {e}", 'danger')

    return redirect(url_for('home'))


@app.route('/user_health', methods=['POST'])
def user_health():
    if 'username' in session:
        username = session['username']

        try:
            # Get user_id from Firestore
            user_ref = db.collection('Users').where('username', '==', username).get()
            if user_ref:
                user_id = user_ref[0].id

                blood_pressure = request.form.get('blood-pressure')
                blood_sugar = request.form.get('blood-sugar')

                if not blood_pressure or not blood_sugar:
                    flash('Please enter valid blood pressure and blood sugar values.', 'danger')
                    return redirect(url_for('user_health'))

                date_log = datetime.now().isoformat()

                # Insert health data into Firestore user_health collection
                db.collection('user_health').add({
                    'user_id': user_id,
                    'blood_sugar': blood_sugar,
                    'blood_pressure': blood_pressure,
                    'date_log': date_log
                })

                flash('Health data inserted successfully!', 'success')

        except Exception as e:
            flash(f"Error saving health data: {e}", 'danger')

    return redirect(url_for('user_dashboard'))


@app.route('/available-dates')
def get_available_dates():
    try:
        availability_data = {}

        # Fetch clinic schedule from Firestore
        clinic_schedule_ref = db.collection('Clinic_Schedule').stream()

        for doc in clinic_schedule_ref:
            schedule = doc.to_dict()
            date_str = schedule['date']
            time_str = schedule['time']
            total_slots = 1  # Assuming 1 slot per time
            booked_slots = 1 if schedule['status'] == 'booked' else 0

            if date_str not in availability_data:
                availability_data[date_str] = {
                    'fullyBooked': booked_slots == total_slots,
                    'appointments': []
                }

            if booked_slots < total_slots:
                availability_data[date_str]['appointments'].append(time_str)

        return jsonify(availability_data)
    except Exception as e:
        print(f"Error fetching available dates: {e}")
        return jsonify({}), 500


@app.route('/book-appointment', methods=['POST'])
def book_appointment():
    date_str = request.form.get('date')
    time_slot = request.form.get('timeslot')
    user_id = session.get('user_id')

    try:
        formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        flash('Invalid date format. Please try again.', 'danger')
        return redirect(url_for('appointment'))

    try:
        # Fetch the schedule document based on date and time from Firestore
        schedule_ref = db.collection('Clinic_Schedule')\
                        .where('date', '==', formatted_date)\
                        .where('time', '==', time_slot).stream()

        schedule_docs = [doc for doc in schedule_ref]
        if not schedule_docs:
            flash('No valid schedule found for the selected date and time.', 'danger')
            return redirect(url_for('appointment'))

        schedule_id = schedule_docs[0].id

        # Update the clinic schedule status to 'booked'
        db.collection('Clinic_Schedule').document(schedule_id).update({
            'status': 'booked'
        })

        # Insert a new appointment
        db.collection('appointments').add({
            'user_id': user_id,
            'schedule_id': schedule_id,
            'status': 'booked'
        })

        flash('Appointment booked successfully!', 'success')
    except Exception as e:
        flash(f'Error booking appointment: {e}', 'danger')

    return redirect(url_for('appointment'))

@app.route('/edit-appointment', methods=['POST'])
def edit_appointment():
    try:
        data = request.json
        print("Received data:", data)  # Log the incoming data for debugging

        # Extract the date, current time, and new time from the JSON data
        date = data.get('date')
        current_time = data.get('currentTime')
        new_time = data.get('newTime')
        user_id = session.get('user_id')

        if not date:
            return jsonify({'error': 'Date is missing'}), 400  # Check if the date is missing and return error

        # Convert the incoming date to yyyy-mm-dd format
        formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')

        print(f"Edit request for user_id: {user_id}, current_time: {current_time}, new_time: {new_time}, date: {formatted_date}")

        # Step 1: Find the current schedule_id for the user's existing appointment
        appointment_ref = db.collection('appointments').where('user_id', '==', user_id).stream()

        current_schedule_id = None
        for appointment in appointment_ref:
            schedule_id = appointment.to_dict().get('schedule_id')
            schedule_ref = db.collection('Clinic_Schedule').document(schedule_id).get()

            if schedule_ref.exists and schedule_ref.to_dict()['date'] == formatted_date and schedule_ref.to_dict()['time'] == current_time:
                current_schedule_id = schedule_id
                break

        if not current_schedule_id:
            print("No appointment found for the provided date and current time.")
            return jsonify({'error': 'No appointment found to edit.'}), 400

        # Step 2: Find the new schedule_id for the selected new time
        new_schedule_ref = db.collection('Clinic_Schedule') \
                             .where('date', '==', formatted_date) \
                             .where('time', '==', new_time) \
                             .where('status', '==', 'available').stream()

        new_schedule_id = None
        for schedule in new_schedule_ref:
            new_schedule_id = schedule.id
            break

        if not new_schedule_id:
            print("No available time slot for the selected time.")
            return jsonify({'error': 'No available time slot for the selected time.'}), 400

        # Step 3: Update the Clinic_Schedule collection
        # 1. Set the old time slot status back to 'available'
        # 2. Set the new time slot status to 'booked'
        db.collection('Clinic_Schedule').document(current_schedule_id).update({'status': 'available'})
        db.collection('Clinic_Schedule').document(new_schedule_id).update({'status': 'booked'})

        # Step 4: Update the appointment to the new schedule_id
        appointment_query = db.collection('appointments').where('user_id', '==', user_id).where('schedule_id', '==', current_schedule_id).stream()
        for appointment in appointment_query:
            db.collection('appointments').document(appointment.id).update({'schedule_id': new_schedule_id})

        print("Appointment edited successfully.")
        return jsonify({'success': 'Appointment edited successfully.'})

    except Exception as e:
        print(f"Error editing appointment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/available_timeslots', methods=['GET'])
def get_available_timeslots():
    try:
        date = request.args.get('date')  # Get the selected date from the frontend
        print(f"Fetching available time slots for date: {date}")  # Log the date

        # Convert the date into YYYY-MM-DD format
        formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        print(f"Formatted date for query: {formatted_date}")

        # Initialize Firebase connection (assuming it's already set up globally in your app)
        db = firestore.client()

        # Query Firestore for available slots on the selected date
        Clinic_schedule_ref = db.collection('Clinic_Schedule')
        query = Clinic_schedule_ref.where('date', '==', formatted_date).where('status', '==', 'available')
        results = query.stream()

        # Extract available time slots
        available_time_slots = [doc.to_dict()['time'] for doc in results]

        print(f"Remaining slots for {formatted_date}: {available_time_slots}")  # Log the available slots

        return jsonify({'timeslots': available_time_slots})

    except Exception as e:
        print(f"Error fetching time slots: {str(e)}")  # Log the error
        return "Internal Server Error", 500  # Return a 500 response


@app.route('/check-appointment', methods=['GET'])
def check_appointment():
    try:
        date = request.args.get('date')
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401

        # Try to parse the date in the format '%a %b %d %Y'
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError as e:
            return jsonify({'error': f"Incorrect date format: {str(e)}"}), 400

        # Proceed with fetching appointments after date conversion
        appointment_ref = db.collection('appointments').where('user_id', '==', user_id).stream()
        appointments = [doc.to_dict() for doc in appointment_ref]

        for appointment in appointments:
            schedule_id = appointment.get('schedule_id')
            schedule_ref = db.collection('Clinic_Schedule').document(schedule_id).get()

            if schedule_ref.exists and schedule_ref.to_dict()['date'] == parsed_date:
                return jsonify({
                    'hasAppointment': True,
                    'appointmentTime': schedule_ref.to_dict()['time'],
                    'message': 'You already have an appointment for today.'
                })

        # If no appointments, get available slots for that date
        schedule_ref = db.collection('Clinic_Schedule')\
                         .where('date', '==', parsed_date)\
                         .where('status', '==', 'available').stream()

        available_time_slots = [doc.to_dict()['time'] for doc in schedule_ref]
        return jsonify({
            'hasAppointment': False,
            'availableTimeSlots': available_time_slots
        })
    except Exception as e:
        print(f"Error checking appointment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/cancel-appointment', methods=['POST'])
def cancel_appointment():
    data = request.json
    date = data.get('date')
    time = data.get('time')
    user_id = session.get('user_id')

    try:
        formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')

        # Find the schedule in Firestore
        schedule_ref = db.collection('Clinic_Schedule')\
                         .where('date', '==', formatted_date)\
                         .where('time', '==', time).stream()

        schedule_docs = [doc for doc in schedule_ref]
        if not schedule_docs:
            return jsonify({'error': 'No appointment found'}), 400

        schedule_id = schedule_docs[0].id

        # Delete the appointment from Firestore
        appointments_ref = db.collection('appointments')\
                            .where('user_id', '==', user_id)\
                            .where('schedule_id', '==', schedule_id).get()

        for appointment in appointments_ref:
            db.collection('appointments').document(appointment.id).delete()

        # Update the clinic schedule status back to 'available'
        db.collection('Clinic_Schedule').document(schedule_id).update({
            'status': 'available'
        })

        return jsonify({'success': 'Appointment canceled successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Function to connect to the database
# def get_db_connection():
#     conn = sqlite3.connect(DATABASE)
#     conn.row_factory = sqlite3.Row
#     return conn
#
# # Registration route
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         email = request.form['email']
#         phone_number = request.form['phone_number']
#         address = request.form['address']
#         user_role = 'user'
#
#         # Hash the password using bcrypt
#         hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
#
#         conn = get_db_connection()
#         cursor = conn.cursor()
#
#         try:
#             # Store the encrypted password in the database
#             cursor.execute('''
#                 INSERT INTO Users (username, password, email_add, phone_number, address, user_role, acc_status)
#                 VALUES (?, ?, ?, ?, ?, ?, ?);
#             ''', (username, hashed_password, email, phone_number, address, user_role, 'enabled'))
#             conn.commit()
#             # Instead of flash, we pass a flag to the template
#             return render_template('register.html', registered=True)
#         except sqlite3.Error as e:
#             flash(f"Error: {e}", "danger")
#         finally:
#             conn.close()
#
#     return render_template('register.html')
#
#
# # Login route
# @app.route('/login', methods=['POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#
#         conn = get_db_connection()
#         cursor = conn.cursor()
#
#         # Modify the query to also fetch the user_id
#         cursor.execute('''
#             SELECT user_id, username, password, user_role FROM Users WHERE username = ?;
#         ''', (username,))
#         user = cursor.fetchone()
#         conn.close()
#
#         if user:
#             # Compare the input password with the hashed password using bcrypt
#             if bcrypt.checkpw(password.encode('utf-8'), user['password']):
#                 session['user_id'] = user['user_id']  # Store user_id in session
#                 session['username'] = user['username']
#                 session['user_role'] = user['user_role']
#
#                 if user['user_role'] == 'doctor':
#                     return redirect(url_for('doctor_dashboard'))
#                 else:
#                     return redirect(url_for('user_dashboard'))
#             else:
#                 flash('Login failed. Incorrect username or password.', 'danger')
#         else:
#             flash('Login failed. Incorrect username or password.', 'danger')
#
#         return redirect(url_for('home'))
#
#
# # User dashboard
# @app.route('/user_dashboard')
# def user_dashboard():
#     if 'username' in session and session['user_role'] == 'user':
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         user_id = session['user_id']
#         try:
#             # Fetch distinct medication types from the Medications table
#             cursor.execute('SELECT blood_pressure, blood_sugar, date_log FROM user_health WHERE user_id = ?;',
#                            (user_id,))
#             rows = cursor.fetchall()
#             if rows:
#                 bp = [float(row['blood_pressure']) for row in rows]
#                 bs = [float(row['blood_sugar']) for row in rows]
#                 date = [row['date_log'] for row in rows]
#                 # Create the bar chart
#                 plt.bar(date, bp, color='#00bfbf')
#                 plt.xlabel('Date')
#                 plt.ylabel('Blood Pressure')
#                 plt.title('Blood Pressure Over Time')
#                 plt.xticks(fontsize=5)
#                 plt.tight_layout()
#                 plt.savefig('static/images/bpchart.png')  # Save to a static folder within your Flask project
#                 plt.close()
#                 plt.bar(date, bs, color='#00bfbf')
#                 plt.xlabel('Date')
#                 plt.ylabel('Blood Sugar')
#                 plt.title('Blood Sugar Over Time')
#                 plt.xticks(fontsize=5)
#                 plt.tight_layout()
#                 plt.savefig('static/images/bschart.png')  # Save to a static folder within your Flask project
#                 plt.close()
#                 showchart = True
#             else:
#                 showchart = False
#
#             return render_template('user_dashboard.html', username=session['username'], showchart=showchart)
#
#
#         except sqlite3.Error as e:
#             flash(f"Error loading dashboard: {e}", 'danger')
#             return redirect(url_for('home'))
#
#         finally:
#             conn.close()
#
#     # return render_template('user_dashboard.html', username="test")
#     return redirect(url_for('home'))
#
#
# # Doctor dashboard page
# @app.route('/doctor_dashboard')
# def doctor_dashboard():
#     if 'username' in session and session['user_role'] == 'doctor':
#         # Open a database connection
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         try:
#             # Fetch distinct medication types from the Medications table
#             cursor.execute('SELECT DISTINCT med_type FROM Medications')
#             med_types = [row['med_type'] for row in cursor.fetchall()]
#
#             # Get the doctor ID (user_id) from the session
#             doctor_id = session['user_id']
#
#             return render_template('doctor_dashboard.html', username=session['username'],
#                                    med_types=med_types, doctor_id=doctor_id)
#
#         except sqlite3.Error as e:
#             flash(f"Error loading dashboard: {e}", 'danger')
#             return redirect(url_for('home'))
#
#         finally:
#             conn.close()
#
#     return redirect(url_for('home'))
#
#
# @app.route('/create_schedule', methods=['POST'])
# def create_schedule():
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#
#         # Get tomorrow's date
#         tomorrow = (datetime.now() + timedelta(days=2)).date()
#
#         # Check if there's already a schedule for tomorrow
#         cursor.execute('SELECT * FROM Clinic_Schedule WHERE date = ?', (tomorrow,))
#         existing_rows = cursor.fetchall()
#
#         if existing_rows:
#             # If rows already exist for tomorrow, return a message indicating no action was taken
#             flash("Tomorrow's schedule already exists.", 'info')
#             return redirect(url_for('doctor_dashboard'))
#
#         # Define the time slots
#         time_slots = [
#             ('10:00', '12:00'),  # Morning session (before lunch)
#             ('14:00', '17:00')  # Afternoon session (after lunch)
#         ]
#
#         # Insert time slots for the morning and afternoon
#         for time_range in time_slots:
#             start_time = datetime.strptime(time_range[0], '%H:%M')
#             end_time = datetime.strptime(time_range[1], '%H:%M')
#
#             while start_time < end_time:
#                 # Insert a 30-minute interval into Clinic_Schedule
#                 cursor.execute('''
#                     INSERT INTO Clinic_Schedule (date, time, status)
#                     VALUES (?, ?, ?);
#                 ''', (tomorrow, start_time.strftime('%H:%M'), 'available'))
#
#                 # Increment the start time by 30 minutes
#                 start_time += timedelta(minutes=30)
#
#         # Commit the transaction
#         conn.commit()
#         flash("Tomorrow's schedule created successfully!", 'success')
#         return redirect(url_for('doctor_dashboard'))
#
#     except sqlite3.Error as e:
#         print(f"Database error: {e}")
#         flash(f"Error creating schedule: {e}", 'danger')
#         return redirect(url_for('doctor_dashboard'))
#
#     finally:
#         conn.close()
#
#
# # Handle consolidated POST request for health, medication, and medical certificate data
# @app.route('/submit_doctor_form', methods=['POST'])
# def submit_doctor_form():
#     if 'username' in session and session['user_role'] == 'doctor':
#         # Open a database connection
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         try:
#             # Retrieve form data
#             user_id = request.form['user_id']
#             doctor_id = request.form['doc_id']
#             doc_notes = request.form['doc_notes']
#             blood_pressure = request.form['blood_pressure']
#             blood_sugar = request.form['blood_sugar']
#             med_name = request.form['med_name']
#             issue_date = request.form['issue_date']
#             visit_date = request.form['visit_date']
#             cert_details = request.form['cert_details']
#
#             # Step 1: Check if the user ID exists in the Users table
#             cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
#             user = cursor.fetchone()
#
#             if not user:
#                 # If the user does not exist, flash an error message and return to the doctor dashboard
#                 flash(f"Error: User ID {user_id} does not exist.", 'danger')
#                 return redirect(url_for('doctor_dashboard'))
#
#             # Step 2: Proceed with form submission since the user exists
#             # Insert medical certificate data into Medical_Cert table
#             cursor.execute('''
#                             INSERT INTO Medical_Cert (user_id, doc_id, issue_date, cert_details)
#                             VALUES (?, ?, ?, ?)
#                         ''', (user_id, doctor_id, issue_date, cert_details))
#
#             # Commit the changes
#             conn.commit()
#
#             # Retrieve the certificate_id of the last inserted record
#             cert_id = cursor.lastrowid
#
#             # Insert health tracking data into User_History table with the retrieved certificate_id
#             cursor.execute('''
#                             INSERT INTO User_History (user_id, doc_id, doc_notes, blood_pressure, blood_sugar, prescribed_med, visit_date, certificate_id)
#                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#                         ''',
#                            (user_id, doctor_id, doc_notes, blood_pressure, blood_sugar, med_name, visit_date, cert_id))
#
#             # Commit the changes
#             conn.commit()
#
#             # Flash a success message
#             flash('Doctor form details submitted successfully.', 'success')
#
#         except sqlite3.Error as e:
#             # Flash an error message
#             flash(f"Error submitting doctor form: {e}", 'danger')
#
#         finally:
#             conn.close()
#
#         return redirect(url_for('doctor_dashboard'))
#
#
# # Route to get user history by userID
# @app.route('/get_user_history/<user_id>', methods=['GET'])
# def get_user_history(user_id):
#     if 'username' in session and session['user_role'] == 'doctor':
#         # Open a database connection
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         try:
#             # Fetch all history for the given user_id
#             cursor.execute('''
#                 SELECT history_id FROM User_History WHERE user_id = ?
#             ''', (user_id,))
#             histories = cursor.fetchall()
#
#             # Convert to a list of dictionaries for JSON response
#             history_list = [{'history_id': row['history_id']} for row in histories]
#
#             return jsonify(history_list)
#
#         except sqlite3.Error as e:
#             return jsonify({'error': str(e)}), 500
#
#         finally:
#             conn.close()
#
#     return jsonify({'error': 'Unauthorized'}), 401
#
#
# @app.route('/get_user_history_top5/<user_id>', methods=['GET'])
# def get_user_history_top5(user_id):
#     if 'username' in session and session['user_role'] == 'doctor':
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         try:
#             # Fetch the top 5 history records for the given user_id and join to fetch doctor's name
#             cursor.execute('''
#                             SELECT uh.doc_notes, uh.blood_pressure, uh.blood_sugar, uh.visit_date,
#                                    d.username AS doctor_name,
#                                    p.username AS patient_name,
#                                    uh.prescribed_med
#                             FROM User_History uh
#                             JOIN Users d ON uh.doc_id = d.user_id  -- Join to get doctor's name
#                             JOIN Users p ON uh.user_id = p.user_id  -- Join to get patient's name
#                             WHERE uh.user_id = ?
#                             ORDER BY uh.visit_date DESC
#                             LIMIT 5;
#                         ''', (user_id,))
#             history_records = cursor.fetchall()
#
#             # Format the data for JSON response
#             records = [
#                 {
#                     'doc_notes': record['doc_notes'],
#                     'blood_pressure': record['blood_pressure'],
#                     'blood_sugar': record['blood_sugar'],
#                     'visit_date': record['visit_date'],
#                     'doctor_name': record['doctor_name'],  # Doctor's name
#                     'patient_name': record['patient_name'],  # Patient's name
#                     'prescribed_med': record['prescribed_med']  # Prescribed medication
#                 } for record in history_records
#             ]
#
#             return jsonify(records)
#
#         except sqlite3.Error as e:
#             return jsonify({'error': str(e)}), 500
#
#         finally:
#             conn.close()
#
#     return jsonify({'error': 'Unauthorized'}), 401
#
#
# @app.route('/get_medications/<med_type>', methods=['GET'])
# def get_medications(med_type):
#     if 'username' in session and session['user_role'] == 'doctor':
#         # Open a database connection
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         try:
#             # Fetch medications based on the selected type
#             cursor.execute('''
#                 SELECT med_name FROM Medications WHERE med_type = ?
#             ''', (med_type,))
#             medications = cursor.fetchall()
#
#             # Convert to a list of dictionaries for JSON response
#             med_list = [{'med_name': row['med_name']} for row in medications]
#
#             return jsonify(med_list)
#
#         except sqlite3.Error as e:
#             return jsonify({'error': str(e)}), 500
#
#         finally:
#             conn.close()
#
#     return jsonify({'error': 'Unauthorized'}), 401
#
#
# # Settings page
# @app.route('/settings')
# def settings():
#     if 'username' in session and (session['user_role'] == 'user' or session['user_role'] == 'doctor'):
#         # Establish database connection
#         conn = get_db_connection()
#         cursor = conn.cursor()
#
#         # SQL query to fetch user details by username from the session
#         query = "SELECT email_add, phone_number, address FROM users WHERE username = ?"
#         cursor.execute(query, (session['username'],))
#         user_data = cursor.fetchone()
#
#         if user_data:
#             # user_data[0] = email, user_data[1] = phone_number, user_data[2] = address
#             email, phone_number, address = user_data
#
#             # Pass the fetched user details to the template
#             return render_template(
#                 'settings.html',
#                 username=session['username'],
#                 email=email,
#                 phone_number=phone_number,
#                 address=address,
#                 role=session['user_role']
#             )
#         else:
#             # If no user data is found, redirect to home
#             return redirect(url_for('home'))
#
#     # Redirect to home if the user is not authenticated
#     return redirect(url_for('home'))
#
#
# @app.route('/update_account', methods=['POST'])
# def update_account():
#     if 'username' not in session:
#         flash('You are not logged in.', 'danger')
#         return redirect(url_for('login'))
#     # Retrieve form data
#     email = request.form.get('email')
#     phone_number = request.form.get('phone_number')
#     address = request.form.get('address')
#     password = request.form.get('password')
#     confirm_password = request.form.get('confirm-password')
#     # Get the current logged-in user's username from the session
#     username = session['username']
#     # Validation checks
#     if not email or not phone_number or not address:
#         flash('Email, phone number, and address are required.', 'danger')
#         return redirect(url_for('settings'))
#     if password and password != confirm_password:
#         flash('Passwords do not match.', 'danger')
#         return redirect(url_for('settings'))
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         # Update email, phone number, and address
#         cursor.execute('''
#             UPDATE Users
#             SET email_add = ?, phone_number = ?, address = ?
#             WHERE username = ?
#         ''', (email, phone_number, address, username))
#         # Update password if provided
#         if password:
#             hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
#             cursor.execute('UPDATE Users SET password = ? WHERE username = ?', (hashed_password, username))
#         conn.commit()
#         return render_template('login.html', updated=True)
#     except sqlite3.Error as e:
#         flash(f"Error updating account: {e}", 'danger')
#     finally:
#         conn.close()
#     return redirect(url_for('settings'))
#
#
# # Delete account route
# @app.route('/delete_account', methods=['POST'])
# def delete_account():
#     if 'username' in session:
#         username = session['username']
#
#         conn = get_db_connection()
#         cursor = conn.cursor()
#
#         try:
#             # Delete user from the database
#             cursor.execute('DELETE FROM Users WHERE username = ?', (username,))
#             conn.commit()
#
#             flash('Your account has been deleted successfully.', 'success')
#
#             # Clear the session after account deletion
#             session.clear()
#
#         except sqlite3.Error as e:
#             flash(f"Error deleting account: {e}", 'danger')
#
#         finally:
#             conn.close()
#
#     return redirect(url_for('home'))
#
#
# @app.route('/user_health', methods=['POST'])
# def user_health():
#     if 'username' in session:
#         username = session['username']
#
#         conn = get_db_connection()
#         cursor = conn.cursor()
#
#         # Step 1: Retrieve user_id based on the username stored in the session
#         try:
#             query = "SELECT user_id FROM users WHERE username = ?"
#             cursor.execute(query, (username,))
#             user_data = cursor.fetchone()
#
#             if not user_data:
#                 flash('User not found!', 'danger')
#                 return redirect(url_for('user_health'))
#
#             user_id = user_data[0]  # Extract the user_id from the fetched data
#
#             # Step 2: Get blood pressure and blood sugar from the submitted form
#             blood_pressure = request.form.get('blood-pressure')
#             blood_sugar = request.form.get('blood-sugar')
#
#             if not blood_pressure or not blood_sugar:
#                 flash('Please enter valid blood pressure and blood sugar values.', 'danger')
#                 return redirect(url_for('user_health'))
#
#             # Step 3: Prepare the datetime for logging
#             date_log = datetime.now()
#
#             # Step 4: Insert the new health record into the user_health table
#             insert_query = '''
#                 INSERT INTO user_health (user_id, blood_sugar, blood_pressure, date_log)
#                 VALUES (?, ?, ?, ?)
#             '''
#             cursor.execute(insert_query, (user_id, blood_sugar, blood_pressure, date_log))
#
#             conn.commit()
#             flash('Health data inserted successfully!', 'success')
#
#         except sqlite3.Error as e:
#             conn.rollback()  # Rollback if there's an error
#             flash(f"Database error: {e}", 'danger')
#
#         finally:
#             conn.close()  # Close the connection
#
#     return redirect(url_for('user_dashboard'))
#
#
# # Appointments Page
# @app.route('/available-dates')
# def get_available_dates():
#     connection = get_db_connection()
#     cursor = connection.cursor()
#
#     try:
#         # Get the user_id from the session
#         user_id = session.get('user_id')
#
#         # Fetch dates and times for appointments specific to the logged-in user
#         cursor.execute("""
#             SELECT cs.date, cs.time,
#                    COUNT(a.appointment_id) as appointment_count,
#                    COUNT(cs.schedule_id) as total_slots,
#                    SUM(CASE WHEN cs.status = 'booked' THEN 1 ELSE 0 END) as booked_slots
#             FROM clinic_schedule cs
#             LEFT JOIN appointments a ON cs.schedule_id = a.schedule_id AND a.user_id = ?
#             GROUP BY cs.date, cs.time
#         """, (user_id,))
#         rows = cursor.fetchall()
#
#         # Dictionary to store availability data
#         availability_data = {}
#
#         for row in rows:
#             date_str = row['date']  # e.g., '2024-09-14'
#             time_str = row['time']  # e.g., '10:00'
#             appointment_count = row['appointment_count']  # Number of appointments at this time
#             total_slots = row['total_slots']  # Total time slots for that date
#             booked_slots = row['booked_slots']  # Number of booked time slots
#
#             # Initialize the dictionary for this date if it doesn't exist yet
#             if date_str not in availability_data:
#                 fully_booked = (booked_slots == total_slots)
#                 availability_data[date_str] = {
#                     'fullyBooked': fully_booked,
#                     'appointments': []  # List to store appointment times
#                 }
#
#             # Add the appointment time if there is an appointment
#             if appointment_count > 0:
#                 availability_data[date_str]['appointments'].append(time_str)
#                 # If we add an appointment, ensure the day is not fully booked
#                 availability_data[date_str]['fullyBooked'] = False
#
#         return jsonify(availability_data)
#
#     except sqlite3.Error as e:
#         print(f"Error fetching available dates: {e}")
#         return jsonify({}), 500  # Return an empty response in case of error
#
#     finally:
#         connection.close()
#
#

#
#
# @app.route('/book-appointment', methods=['POST'])
# def book_appointment():
#     # Get the selected date and time slot from the form
#     date_str = request.form.get('date')
#     time_slot = request.form.get('timeslot')
#     user_id = session.get('user_id')
#
#     # Ensure the user is logged in
#     if not user_id:
#         flash('Please log in to book an appointment.', 'danger')
#         return redirect(url_for('home'))
#
#     # Convert the date to yyyy-mm-dd format
#     try:
#         formatted_date = datetime.strptime(date_str, '%a %b %d %Y').strftime('%Y-%m-%d')
#     except ValueError:
#         flash('Invalid date format. Please try again.', 'danger')
#         return redirect(url_for('appointment'))
#
#     connection = get_db_connection()
#     cursor = connection.cursor()
#
#     try:
#         # Step 1: Fetch the corresponding schedule_id from the clinic_schedule table
#         cursor.execute("""
#             SELECT schedule_id FROM clinic_schedule
#             WHERE date = ? AND time = ?
#         """, (formatted_date, time_slot))
#         schedule = cursor.fetchone()
#
#         # Check if a valid schedule was found
#         if not schedule:
#             flash('No valid schedule found for the selected date and time.', 'danger')
#             return redirect(url_for('appointment'))
#
#         schedule_id = schedule['schedule_id']
#
#         # Step 2: Update the clinic_schedule status to 'booked'
#         cursor.execute("""
#             UPDATE clinic_schedule
#             SET status = 'booked'
#             WHERE schedule_id = ?
#         """, (schedule_id,))
#
#         # Step 3: Insert a new row in the appointments table
#         cursor.execute("""
#             INSERT INTO appointments (user_id, schedule_id, status)
#             VALUES (?, ?, 'booked')
#         """, (user_id, schedule_id))
#
#         # Commit the changes
#         connection.commit()
#
#         flash('Appointment booked successfully!', 'success')
#
#     except sqlite3.Error as e:
#         connection.rollback()
#         flash(f'Error booking appointment: {e}', 'danger')
#
#     finally:
#         connection.close()
#
#     return redirect(url_for('appointment'))
#
#
# # Check if the user has an appointment on the selected date
# @app.route('/check-appointment', methods=['GET'])
# def check_appointment():
#     try:
#         date = request.args.get('date')  # Get the selected date from the frontend
#         user_id = session.get('user_id')  # Get the current user ID from the session
#
#         if not user_id:
#             return jsonify({'error': 'User not logged in'}), 401
#
#         # Convert the date into YYYY-MM-DD format
#         parsed_date = datetime.strptime(date, '%a %b %d %Y').strftime('%Y-%m-%d')
#         print(parsed_date)
#         # parsed_date = date
#         connection = get_db_connection()
#         cursor = connection.cursor()
#
#         # Check if the user has an appointment on this date
#         cursor.execute("""
#             SELECT a.appointment_id, cs.time FROM appointments a
#             JOIN clinic_schedule cs ON a.schedule_id = cs.schedule_id
#             WHERE cs.date = ? AND a.user_id = ?
#         """, (parsed_date, user_id))
#
#         appointment = cursor.fetchone()
#
#         if appointment:
#             # User already has an appointment
#             return jsonify({
#                 'hasAppointment': True,
#                 'appointmentTime': appointment['time'],
#                 'message': 'You already have an appointment for today.'
#             })
#         else:
#             # Fetch available time slots for booking if no appointment exists
#             cursor.execute("""
#                 SELECT time FROM clinic_schedule
#                 WHERE date = ? AND status = 'available'
#             """, (parsed_date,))
#             available_time_slots = [row['time'] for row in cursor.fetchall()]
#
#             return jsonify({
#                 'hasAppointment': False,
#                 'availableTimeSlots': available_time_slots
#             })
#
#     except Exception as e:
#         print(f"Error checking appointment: {str(e)}")
#         return "Internal Server Error", 500
#
#     finally:
#         connection.close()
#
#
# @app.route('/available_timeslots')
# def get_available_timeslots():
#     try:
#         date = request.args.get('date')  # Get the selected date from the frontend
#         print(f"Fetching available time slots for date: {date}")  # Log the date
#
#         # Convert the date into YYYY-MM-DD format
#         formatted_date = datetime.strptime(date, '%a %b %d %Y').strftime('%Y-%m-%d')
#         print(f"Fetching available time slots for date: {date}")
#         print(f"Formatted date for query: {formatted_date}")
#
#         connection = get_db_connection()
#
#         # Fetch all available time slots directly from the clinic_schedule for the selected date
#         clinic_schedule_query = """
#             SELECT * FROM clinic_schedule WHERE date = ? AND status = 'available'
#             """
#         available_time_slots = [row['time'] for row in connection.execute(clinic_schedule_query, (formatted_date,))]
#
#         print(f"Remaining slots for {formatted_date}: {available_time_slots}")  # Log the available slots
#
#         return jsonify({'timeslots': available_time_slots})
#
#     except Exception as e:
#         print(f"Error fetching time slots: {str(e)}")  # Log the error
#         return "Internal Server Error", 500  # Return a 500 response
#
#
# @app.route('/cancel-appointment', methods=['POST'])
# def cancel_appointment():
#     data = request.json
#     date = data.get('date')
#     time = data.get('time')
#     user_id = session.get('user_id')
#
#     connection = get_db_connection()
#     cursor = connection.cursor()
#
#     try:
#         # Convert the incoming date to yyyy-mm-dd format
#         formatted_date = datetime.strptime(date, '%a %b %d %Y').strftime('%Y-%m-%d')
#
#         # Log the incoming request data
#         print(f"Cancel request for date: {formatted_date}, time: {time}, user_id: {user_id}")
#
#         # Find the schedule_id for the selected date and time
#         cursor.execute("""
#             SELECT schedule_id FROM clinic_schedule
#             WHERE date = ? AND time = ?
#         """, (formatted_date, time))
#         schedule = cursor.fetchone()
#
#         if not schedule:
#             print("No appointment found for the provided date and time.")
#             return jsonify({'error': 'No appointment found'}), 400
#
#         schedule_id = schedule['schedule_id']
#
#         # Delete the appointment from the appointments table
#         cursor.execute("""
#             DELETE FROM appointments WHERE user_id = ? AND schedule_id = ?
#         """, (user_id, schedule_id))
#
#         # Update the clinic schedule status back to 'available'
#         cursor.execute("UPDATE clinic_schedule SET status = 'available' WHERE schedule_id = ?", (schedule_id,))
#
#         connection.commit()
#
#         print("Appointment canceled successfully.")
#         return jsonify({'success': 'Appointment canceled successfully'})
#
#     except sqlite3.Error as e:
#         connection.rollback()
#         print(f"Error canceling appointment: {str(e)}")
#         return jsonify({'error': str(e)}), 500
#
#     finally:
#         connection.close()
#
#
# @app.route('/edit-appointment', methods=['POST'])
# def edit_appointment():
#     data = request.json
#     print("Received data:", data)  # Log the incoming data for debugging
#
#     # Extract the date, current time, and new time from the JSON data
#     date = data.get('date')
#     current_time = data.get('currentTime')
#     new_time = data.get('newTime')
#     user_id = session.get('user_id')
#
#     if not date:
#         return jsonify({'error': 'Date is missing'}), 400  # Check if the date is missing and return error
#
#     connection = get_db_connection()
#     cursor = connection.cursor()
#
#     try:
#         # Convert the incoming date to yyyy-mm-dd format
#         formatted_date = datetime.strptime(date, '%a %b %d %Y').strftime('%Y-%m-%d')
#
#         print(
#             f"Edit request for user_id: {user_id}, current_time: {current_time}, new_time: {new_time}, date: {formatted_date}")
#
#         # Find the current schedule_id for the user's existing appointment
#         cursor.execute("""
#             SELECT a.schedule_id
#             FROM appointments a
#             JOIN clinic_schedule cs ON a.schedule_id = cs.schedule_id
#             WHERE a.user_id = ? AND cs.date = ? AND cs.time = ?
#         """, (user_id, formatted_date, current_time))
#         current_schedule = cursor.fetchone()
#
#         if not current_schedule:
#             print("No appointment found for the provided date and current time.")
#             return jsonify({'error': 'No appointment found to edit.'}), 400
#
#         current_schedule_id = current_schedule['schedule_id']
#
#         # Find the new schedule_id for the selected time
#         cursor.execute("""
#             SELECT schedule_id
#             FROM clinic_schedule
#             WHERE date = ? AND time = ? AND status = 'available'
#         """, (formatted_date, new_time))
#         new_schedule = cursor.fetchone()
#
#         if not new_schedule:
#             print("No available time slot for the selected time.")
#             return jsonify({'error': 'No available time slot for the selected time.'}), 400
#
#         new_schedule_id = new_schedule['schedule_id']
#
#         # Update the clinic schedule:
#         # 1. Set the old time slot status back to 'available'
#         # 2. Set the new time slot status to 'booked'
#         cursor.execute("UPDATE clinic_schedule SET status = 'available' WHERE schedule_id = ?", (current_schedule_id,))
#         cursor.execute("UPDATE clinic_schedule SET status = 'booked' WHERE schedule_id = ?", (new_schedule_id,))
#
#         # Update the appointment to the new schedule_id
#         cursor.execute("""
#             UPDATE appointments
#             SET schedule_id = ?
#             WHERE user_id = ? AND schedule_id = ?
#         """, (new_schedule_id, user_id, current_schedule_id))
#
#         # Commit the changes to the database
#         connection.commit()
#
#         print("Appointment edited successfully.")
#         return jsonify({'success': 'Appointment edited successfully.'})
#
#     except sqlite3.Error as e:
#         connection.rollback()
#         print(f"Error editing appointment: {str(e)}")
#         return jsonify({'error': str(e)}), 500
#
#     finally:
#         connection.close()
#
#
# # Function to create today's appointment
# @app.route('/get_today_appointments', methods=['GET'])
# def get_today_appointments():
#     if 'username' in session and session['user_role'] == 'doctor':
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         try:
#             # Use a specific test date for testing
#             today = datetime.now().date()
#
#             # Fetch appointments for the test date
#             cursor.execute('''
#                            SELECT a.user_id, u.username, cs.date, cs.time
#                            FROM Appointments a
#                            JOIN Users u ON a.user_id = u.user_id
#                            JOIN Clinic_Schedule cs ON a.schedule_id = cs.schedule_id
#                            WHERE cs.date = ? AND cs.status = 'booked';
#                        ''', (today,))
#             appointments = cursor.fetchall()
#
#             # Prepare the result as a list of dictionaries
#             appointments_list = [{'patient': row['username'], 'date': row['date'], 'time': row['time']} for row in
#                                  appointments]
#
#             return jsonify(appointments_list)
#
#         except sqlite3.Error as e:
#             return jsonify({'error': str(e)}), 500
#
#         finally:
#             conn.close()
#
#     return jsonify({'error': 'Unauthorized'}), 401
#
#
# # Function to mark patient as a no-show
# @app.route('/mark_no_show', methods=['POST'])
# def mark_no_show():
#     if 'username' in session and session['user_role'] == 'doctor':
#         data = request.get_json()
#         date = data.get('date')
#         time = data.get('time')
#
#         conn = get_db_connection()
#         cursor = conn.cursor()
#
#         try:
#             # First, find the schedule_id based on the date and time
#             cursor.execute('''
#                 SELECT schedule_id FROM Clinic_Schedule WHERE date = ? AND time = ?;
#             ''', (date, time))
#             schedule = cursor.fetchone()
#
#             if schedule:
#                 schedule_id = schedule['schedule_id']
#
#                 # Update the status in the Appointments table
#                 cursor.execute('''
#                     UPDATE Appointments SET status = 'No-Show'
#                     WHERE schedule_id = ?;
#                 ''', (schedule_id,))
#
#                 # Commit the changes
#                 conn.commit()
#
#                 # Update the status in the Clinic_Schedule table
#                 cursor.execute('''
#                     UPDATE Clinic_Schedule SET status = 'No-Show'
#                     WHERE schedule_id = ?;
#                 ''', (schedule_id,))
#
#                 conn.commit()
#
#                 return jsonify({'success': True})
#             else:
#                 return jsonify({'success': False, 'message': 'Schedule not found'})
#
#         except sqlite3.Error as e:
#             print(f"Database error: {e}")
#             return jsonify({'success': False, 'error': str(e)})
#         finally:
#             conn.close()
#
#     return jsonify({'success': False, 'message': 'Unauthorized'}), 401

if __name__ == "__main__":
    app.run(debug=True)
