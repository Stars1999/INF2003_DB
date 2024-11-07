import functools
import time
from datetime import datetime, timedelta  # For handling dates and times
from concurrent.futures import ThreadPoolExecutor
import bcrypt
import firebase_admin
import matplotlib
import psutil
from firebase_admin import credentials, firestore
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify

matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# Required for flash messages and session management
app.secret_key = 'your_secret_key'

# Initialize Firebase
cred = credentials.Certificate("inf2003-2ba47-firebase-adminsdk-kwxph-97051cd15f.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def performance_analysis(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Measure start time and memory usage
        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss / (1024 ** 2)  # in MB

        # Execute the function
        result = func(*args, **kwargs)

        # Measure end time and memory usage
        end_time = time.time()
        end_memory = process.memory_info().rss / (1024 ** 2)  # in MB
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory

        # Print performance analysis
        print(f"NOSQL Performance Analysis for {func.__name__}")
        print(f"Execution Time: {execution_time:.8f} seconds")
        print(f"Memory Usage: {memory_usage:.8f} MB")

        return result

    return wrapper


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

# Function to get the next auto-incrementing ID for any collection
def get_next_id(collection_name):
    try:
        counter_ref = db.collection('Counters').document(collection_name)
        counter_doc = counter_ref.get()

        if counter_doc.exists:
            current_id = counter_doc.to_dict().get('current_id', 0)  # Get the current ID
            new_id = current_id + 1  # Increment the ID
            counter_ref.update({'current_id': new_id})  # Update the counter in Firestore
        else:
            # If the counter doesn't exist, create it and start from 1
            new_id = 1
            counter_ref.set({'current_id': new_id})

        return new_id

    except Exception as e:
        raise Exception(f"Error generating new ID: {e}")

@app.route('/register', methods=['GET', 'POST'])
@performance_analysis
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone_number = request.form['phone_number']
        address = request.form['address']
        user_role = 'user'

        # Get the next user_id
        user_id = get_next_id('Users')

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Store the user in Firestore
        users_ref = db.collection('Users')
        try:
            users_ref.add({
                'user_id': user_id,  # Auto-incremented user_id
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
@performance_analysis
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
                # Store the correct user_id (from the document field, not Firestore doc ID) in the session
                session['user_id'] = user_data['user_id']  # Use the user_id from the document data
                session['username'] = user_data['username']
                session['user_role'] = user_data['user_role']

                if user_data['user_role'] == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Incorrect password.', 'danger')
        else:
            flash('User not found.', 'danger')

    return redirect(url_for('home'))


# Fetches user health data from Firestore based on user_id.
def fetch_user_health_data(user_id):
    user_health_ref = db.collection('user_health').where('user_id', '==', user_id).stream()
    return [doc.to_dict() for doc in user_health_ref]

# User Dashboard
@app.route('/user_dashboard')
@performance_analysis
def user_dashboard():
    if 'username' in session and session['user_role'] == 'user':
        user_id = session['user_id']  # Assume user_id is stored in the session after login

        try:
            # Use ThreadPoolExecutor to run Firestore data fetching concurrently
            with ThreadPoolExecutor() as executor:
                health_future = executor.submit(fetch_user_health_data, user_id)

                # Wait for the health data result
                rows = health_future.result()

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

# Fetches distinct medication types from Firestore
def fetch_medications():
    medications_ref = db.collection('Medications').stream()
    return list(set([doc.to_dict()['med_type'] for doc in medications_ref]))

@app.route('/doctor_dashboard')
@performance_analysis
def doctor_dashboard():
    if 'username' in session and session['user_role'] == 'doctor':
        doctor_id = session['user_id']
        try:
            # Use ThreadPoolExecutor to fetch medications and doctor information concurrently
            with ThreadPoolExecutor() as executor:
                # Schedule concurrent fetching of medications and doctor info
                medications_future = executor.submit(fetch_medications)

            # Get results from futures
            med_types = medications_future.result()

            return render_template('doctor_dashboard.html', username=session['username'], med_types=med_types,
                                   doctor_id=doctor_id)

        except Exception as e:
            flash(f"Error loading dashboard: {e}", 'danger')
            return redirect(url_for('home'))

    return redirect(url_for('home'))


@app.route('/create_schedule', methods=['POST'])
@performance_analysis
def create_schedule():
    try:
        # Get tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()

        # Define the time slots
        time_slots = [('10:00', '12:00'), ('14:00', '17:00')]

        # Initialize a batch
        batch = db.batch()

        # Prepare the batch write for each time slot
        for time_range in time_slots:
            start_time = datetime.strptime(time_range[0], '%H:%M')
            end_time = datetime.strptime(time_range[1], '%H:%M')

            while start_time < end_time:
                # Create a new document reference for each time slot
                schedule_ref = db.collection('Clinic_Schedule').document()

                # Add the data to the batch
                batch.set(schedule_ref, {
                    'schedule_id': get_next_id('Clinic_Schedule'),
                    'date': tomorrow,
                    'time': start_time.strftime('%H:%M'),
                    'status': 'available'
                })

                # Increment the start time by 30 minutes
                start_time += timedelta(minutes=30)

        # Commit all batched writes at once
        batch.commit()

        flash("Tomorrow's schedule created successfully!", 'success')
        return redirect(url_for('doctor_dashboard'))

    except Exception as e:
        flash(f"Error creating schedule: {e}", 'danger')
        return redirect(url_for('doctor_dashboard'))

def check_user_exists(user_id):
    """Check if the user exists in the Users collection."""
    user_ref = db.collection('Users').where('user_id', '==', int(user_id)).get()
    return user_ref[0] if user_ref else None

def add_medical_certificate(cert_data):
    """Add medical certificate data to Medical_Cert collection."""
    return db.collection('Medical_Cert').add(cert_data)

def add_user_history(history_data):
    """Add user history data to User_History collection."""
    return db.collection('User_History').add(history_data)


@app.route('/submit_doctor_form', methods=['POST'])
@performance_analysis
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

            # Step 1: Check if the user exists concurrently
            with ThreadPoolExecutor() as executor:
                user_future = executor.submit(check_user_exists, user_id)
                user = user_future.result()

                if not user:
                    flash(f"Error: User ID {user_id} does not exist.", 'danger')
                    return redirect(url_for('doctor_dashboard'))

                # Step 2: Prepare data for concurrent insertion
                MC_id = get_next_id('Medical_Cert')
                cert_data = {
                    'certificate_id': MC_id,
                    'user_id': user_id,
                    'doc_id': doctor_id,
                    'issue_date': issue_date,
                    'cert_details': cert_details
                }

                history_id = get_next_id('User_History')
                history_data = {
                    'history_id': history_id,
                    'user_id': user_id,
                    'doc_id': doctor_id,
                    'doc_notes': doc_notes,
                    'blood_pressure': blood_pressure,
                    'blood_sugar': blood_sugar,
                    'prescribed_med': med_name,
                    'visit_date': visit_date,
                    'certificate_id': MC_id  # Use the generated certificate ID
                }

                # Step 3: Insert the medical certificate and history concurrently
                cert_future = executor.submit(add_medical_certificate, cert_data)
                history_future = executor.submit(add_user_history, history_data)

                # Wait for both to complete
                cert_future.result()
                history_future.result()

            flash('Doctor form details submitted successfully.', 'success')

        except Exception as e:
            flash(f"Error submitting doctor form: {e}", 'danger')

        return redirect(url_for('doctor_dashboard'))


@app.route('/get_user_history/<user_id>', methods=['GET'])
@performance_analysis
def get_user_history(user_id):
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Ensure that user_id is a string
            user_id = str(user_id)
            print(f"Searching for history with user_id: {user_id}")

            # Fetch all history for the given user_id from Firestore
            user_history_ref = db.collection('User_History').where('user_id', '==', user_id).stream()

            # Convert to a list of dictionaries for JSON response
            history_list = [{'history_id': doc.id} for doc in user_history_ref]

            # Debugging print to check the length of results
            print(f"Found {len(history_list)} history records for user_id: {user_id}")

            if not history_list:
                return jsonify({"message": "No history records found for this user."})

            return jsonify(history_list)

        except Exception as e:
            print(f"Error fetching user history: {e}")
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Unauthorized'}), 401


@app.route('/get_user_history_top5/<user_id>', methods=['GET'])
@performance_analysis
def get_user_history_top5(user_id):
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Ensure that user_id is used as a string
            user_id = str(user_id)

            # Fetch the top 5 history records for the given user_id
            user_history_ref = db.collection('User_History') \
                .where('user_id', '==', user_id) \
                .limit(5).stream()

            history_records = [doc.to_dict() for doc in user_history_ref]

            # Sort history records by 'visit_date' in descending order (most recent first)
            sorted_history_records = sorted(history_records, key=lambda x: x['visit_date'], reverse=True)

            #print("History Records:", history_records)  # Add this line to print the results

            # Fetch doctor and patient names (from Users collection) by user_id field, not document ID
            doctor_name = None  # To store the doctor's name directly
            for history in sorted_history_records:
                doc_id = int(history['doc_id'])  # Ensure doc_id is treated as an integer

                try:
                    # Query Users by user_id field (as integer)
                    doctor_query = db.collection('Users').where('user_id', '==', doc_id).stream()
                    doctor_doc = next(doctor_query, None)
                    if doctor_doc:
                        doctor_data = doctor_doc.to_dict()
                        doctor_name = doctor_data['username']  # Store doctor's name directly
                    else:
                        print(f"No doctor found with doc_id {doc_id}")
                except Exception as e:
                    print(f"Error fetching doctor with doc_id {doc_id}: {str(e)}")

            # Fetch patient name based on user_id (as integer)
            try:
                # Ensure user_id is treated as an integer and match with the Firestore field
                patient_query = db.collection('Users').where('user_id', '==', int(user_id)).stream()
                patient_doc = next(patient_query, None)
                if patient_doc:
                    patient_data = patient_doc.to_dict()
                    patient_name = patient_data['username']
                else:
                    print(f"No patient found with user_id {user_id}")
                    patient_name = None
            except Exception as e:
                print(f"Error fetching patient with user_id {user_id}: {str(e)}")
                patient_name = None

            print("Doctor Names:", doctor_name)
            print("Patient Name:", patient_name)

            # Format the data for JSON response
            records = [
                {
                    'doc_notes': record['doc_notes'],
                    'blood_pressure': record['blood_pressure'],
                    'blood_sugar': record['blood_sugar'],
                    'visit_date': record['visit_date'],
                    'doctor_name': doctor_name,
                    'patient_name': patient_name,
                    'prescribed_med': record['prescribed_med']
                } for record in sorted_history_records
            ]

            return jsonify(records)

        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/get_medications/<med_type>', methods=['GET'])
@performance_analysis
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
@performance_analysis
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
@performance_analysis
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
@performance_analysis
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
@performance_analysis
def user_health():
    if 'username' in session:
        username = session['username']

        try:
            # Get user data from Firestore
            user_ref = db.collection('Users').where('username', '==', username).get()
            if user_ref:
                user_data = user_ref[0].to_dict()  # Get the actual document data
                user_id = user_data['user_id']  # Fetch the user_id from the document data

                blood_pressure = request.form.get('blood-pressure')
                blood_sugar = request.form.get('blood-sugar')

                if not blood_pressure or not blood_sugar:
                    flash('Please enter valid blood pressure and blood sugar values.', 'danger')
                    return redirect(url_for('user_health'))

                date_log = datetime.now().isoformat()

                health_id = get_next_id('user_health')

                # Insert health data into Firestore user_health collection
                db.collection('user_health').add({
                    'health_id': health_id,
                    'user_id': user_id,  # Use the user_id from the document data
                    'blood_sugar': blood_sugar,
                    'blood_pressure': blood_pressure,
                    'date_log': date_log
                })

                flash('Health data inserted successfully!', 'success')

        except Exception as e:
            flash(f"Error saving health data: {e}", 'danger')

    return redirect(url_for('user_dashboard'))



@app.route('/available-dates')
@performance_analysis
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
@performance_analysis
def book_appointment():
    date_str = request.form.get('date')
    time_slot = request.form.get('timeslot')
    user_id = session.get('user_id')

    try:
        # Format date for consistency
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

        # Get the 'schedule_id' from the document data, not the Firestore document ID
        schedule_doc_id = schedule_docs[0].id
        schedule_data = schedule_docs[0].to_dict()
        schedule_id = schedule_data.get('schedule_id')  # Extract the schedule_id field from the document data
        appt_id = get_next_id('appointments')

        # Update the clinic schedule status to 'booked'
        db.collection('Clinic_Schedule').document(schedule_doc_id).update({
            'status': 'booked'
        })

        # Insert a new appointment
        db.collection('appointments').add({
            'appointment_id': appt_id,
            'user_id': user_id,
            'schedule_id': schedule_id,
            'status': 'booked'
        })

        flash('Appointment booked successfully!', 'success')
    except Exception as e:
        flash(f'Error booking appointment: {e}', 'danger')

    return redirect(url_for('appointment'))


@app.route('/edit-appointment', methods=['POST'])
@performance_analysis
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

        print(
            f"Edit request for user_id: {user_id}, current_time: {current_time}, new_time: {new_time}, date: {formatted_date}")

        # Step 1: Find the current schedule_id for the user's existing appointment
        appointment_ref = db.collection('appointments').where('user_id', '==', user_id).stream()

        current_schedule_id = None
        for appointment in appointment_ref:
            schedule_id = appointment.to_dict().get('schedule_id')

            # Query Clinic_Schedule by schedule_id (field) rather than document ID
            schedule_ref = db.collection('Clinic_Schedule').where('schedule_id', '==', schedule_id).stream()
            schedule_docs = [doc for doc in schedule_ref]

            if schedule_docs and schedule_docs[0].to_dict()['date'] == formatted_date and schedule_docs[0].to_dict()[
                'time'] == current_time:
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
            new_schedule_id = schedule.to_dict().get('schedule_id')  # Get the new schedule_id field, not document ID
            break

        if not new_schedule_id:
            print("No available time slot for the selected time.")
            return jsonify({'error': 'No available time slot for the selected time.'}), 400

        # Step 3: Update the Clinic_Schedule collection
        # 1. Set the old time slot status back to 'available'
        # 2. Set the new time slot status to 'booked'
        old_schedule_ref = db.collection('Clinic_Schedule').where('schedule_id', '==', current_schedule_id).stream()
        for old_schedule in old_schedule_ref:
            db.collection('Clinic_Schedule').document(old_schedule.id).update({'status': 'available'})

        new_schedule_ref = db.collection('Clinic_Schedule').where('schedule_id', '==', new_schedule_id).stream()
        for new_schedule in new_schedule_ref:
            db.collection('Clinic_Schedule').document(new_schedule.id).update({'status': 'booked'})

        # Step 4: Update the appointment to the new schedule_id
        appointment_query = db.collection('appointments').where('user_id', '==', user_id).where('schedule_id', '==',
                                                                                                current_schedule_id).stream()
        for appointment in appointment_query:
            db.collection('appointments').document(appointment.id).update({'schedule_id': new_schedule_id})

        print("Appointment edited successfully.")
        return jsonify({'success': 'Appointment edited successfully.'})

    except Exception as e:
        print(f"Error editing appointment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/available_timeslots', methods=['GET'])
@performance_analysis
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
@performance_analysis
def check_appointment():
    try:
        date = request.args.get('date')
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401

        # Try to parse the date in the format '%Y-%m-%d'
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError as e:
            return jsonify({'error': f"Incorrect date format: {str(e)}"}), 400

        # Proceed with fetching appointments after date conversion
        appointment_ref = db.collection('appointments').where('user_id', '==', user_id).stream()
        appointments = [doc.to_dict() for doc in appointment_ref]

        for appointment in appointments:
            schedule_id = appointment.get('schedule_id')  # This is the `schedule_id` field, not Firestore document ID

            # Now we query the `Clinic_Schedule` collection using the `schedule_id` field, not Firestore doc ID
            schedule_ref = db.collection('Clinic_Schedule').where('schedule_id', '==', schedule_id).stream()
            schedule_docs = [doc for doc in schedule_ref]

            if schedule_docs and schedule_docs[0].to_dict()['date'] == parsed_date:
                return jsonify({
                    'hasAppointment': True,
                    'appointmentTime': schedule_docs[0].to_dict()['time'],
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
@performance_analysis
def cancel_appointment():
    data = request.json
    date = data.get('date')
    time = data.get('time')
    user_id = session.get('user_id')

    try:
        # Parse the date in the correct format
        formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')

        # Find the schedule in Firestore using the `date` and `time`
        schedule_ref = db.collection('Clinic_Schedule')\
                         .where('date', '==', formatted_date)\
                         .where('time', '==', time).stream()

        schedule_docs = [doc for doc in schedule_ref]
        if not schedule_docs:
            return jsonify({'error': 'No appointment found'}), 400

        # Get the `schedule_id` from the document data
        schedule_data = schedule_docs[0].to_dict()
        schedule_id = schedule_data.get('schedule_id')  # Get the `schedule_id` field, not the document ID

        # Find and delete the appointment from Firestore using `schedule_id`
        appointments_ref = db.collection('appointments')\
                            .where('user_id', '==', user_id)\
                            .where('schedule_id', '==', schedule_id).get()

        for appointment in appointments_ref:
            db.collection('appointments').document(appointment.id).delete()

        # Update the clinic schedule status back to 'available'
        clinic_schedule_ref = db.collection('Clinic_Schedule').where('schedule_id', '==', schedule_id).stream()
        for clinic_schedule in clinic_schedule_ref:
            db.collection('Clinic_Schedule').document(clinic_schedule.id).update({
                'status': 'available'
            })

        return jsonify({'success': 'Appointment canceled successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_today_appointments', methods=['GET'])
@performance_analysis
def get_today_appointments():
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Get today's date in the format 'YYYY-MM-DD'
            today = datetime.now().date().isoformat()
            print(f"Today's date: {today}")  # Debugging print

            # Query all appointments
            appointments_ref = db.collection('appointments').stream()
            appointments_list = []

            for appointment in appointments_ref:
                appointment_data = appointment.to_dict()

                # Fetch the schedule based on the `schedule_id` field, not the document ID
                schedule_query = db.collection('Clinic_Schedule').where('schedule_id', '==', appointment_data['schedule_id']).stream()
                schedule_ref = next(schedule_query, None)  # Get the first result
                if schedule_ref:
                    schedule_data = schedule_ref.to_dict()

                    # Check if the appointment is for today and its status is 'booked'
                    if schedule_data['date'] == today and schedule_data['status'] == 'booked':
                        print("Found a matching appointment!")  # Debugging print

                        try:
                            user_query = db.collection('Users').where('user_id', '==', appointment_data['user_id']).stream()
                            user_ref = next(user_query, None)
                            if user_ref:
                                user_data = user_ref.to_dict()

                                # Prepare the appointment details
                                appointment_entry = {
                                    'patient': user_data['username'],
                                    'date': schedule_data['date'],
                                    'time': schedule_data['time']
                                }
                                appointments_list.append(appointment_entry)
                            else:
                                print(f"User not found for user_id: {appointment_data['user_id']}")
                        except Exception as e:
                            print(f"Error fetching user data: {str(e)}")
                            return jsonify({'error': f"User data fetch error: {str(e)}"}), 500

                    else:
                        print(f"Schedule did not match today or status not booked.")


            if not appointments_list:
                return jsonify({"message": "No appointments booked for today."})

            return jsonify(appointments_list)

        except Exception as e:
            print(f"Error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Unauthorized'}), 401



@app.route('/mark_no_show', methods=['POST'])
@performance_analysis
def mark_no_show():
    if 'username' in session and session['user_role'] == 'doctor':
        data = request.get_json()
        date = data.get('date')
        time = data.get('time')

        try:
            # First, find the schedule document based on the date and time
            schedule_query = db.collection('Clinic_Schedule') \
                               .where('date', '==', date) \
                               .where('time', '==', time) \
                               .stream()

            schedule = next(schedule_query, None)

            if schedule:
                schedule_data = schedule.to_dict()
                schedule_id = schedule.id  # Use the document ID as the schedule_id

                # Update the status in the Appointments collection to 'No-Show'
                appointments_query = db.collection('appointments') \
                                      .where('schedule_id', '==', schedule_id) \
                                      .stream()

                for appointment in appointments_query:
                    db.collection('appointments').document(appointment.id).update({
                        'status': 'No-Show'
                    })

                # Update the status in the Clinic_Schedule collection
                db.collection('Clinic_Schedule').document(schedule_id).update({
                    'status': 'No-Show'
                })

                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'message': 'Schedule not found'})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': False, 'message': 'Unauthorized'}), 401

if __name__ == "__main__":
    app.run(debug=True)
