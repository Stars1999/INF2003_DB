from pymongo import MongoClient
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
import bcrypt
from datetime import datetime, timedelta # For handling dates and times
import matplotlib
import time
import psutil
import functools
import sqlite3

matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# Required for flash messages and session management
app.secret_key = 'your_secret_key'

# Replace the placeholder with your actual connection string
client = MongoClient("mongodb+srv://2301772:Pa55w0rd@inf2003.n4h2o.mongodb.net/?retryWrites=true&w=majority")

# Specify the database you want to use
db = client.INF2003

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
        # Use MongoDB's atomic `$inc` operation to increment the `current_id`
        counter = db['Counters'].find_one_and_update(
            {'_id': collection_name},
            {'$inc': {'current_id': 1}},
            upsert=True,  # Create the document if it doesn't exist
            return_document=True  # Return the updated document
        )

        # If the counter document is found or created, retrieve the new ID
        new_id = counter['current_id']
        return new_id

    except Exception as e:
        raise Exception(f"Error generating new ID: {e}")


@app.route('/register', methods=['GET', 'POST'])
@performance_analysis
# Assuming `db` is the MongoDB database instance
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

        # Prepare the user data for insertion
        user_data = {
            'user_id': user_id,  # Auto-incremented user_id
            'username': username,
            'password': hashed_password.decode('utf-8'),  # Convert hash to string
            'email_add': email,
            'phone_number': phone_number,
            'address': address,
            'user_role': user_role,
            'acc_status': 'enabled'
        }

        # Insert the user data into MongoDB
        try:
            db['Users'].insert_one(user_data)
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

        # Get the user from MongoDB
        user_data = db['Users'].find_one({'username': username})

        if user_data:
            # Check if the password matches
            if bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
                # Store the correct user_id in the session
                session['user_id'] = user_data['user_id']
                session['username'] = user_data['username']
                session['user_role'] = user_data['user_role']

                # Redirect based on user role
                if user_data['user_role'] == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Incorrect password.', 'danger')
        else:
            flash('User not found.', 'danger')

    return redirect(url_for('home'))


@app.route('/user_dashboard')
@performance_analysis
def user_dashboard():
    if 'username' in session and session['user_role'] == 'user':
        user_id = session['user_id']  # Assume user_id is stored in the session after login

        try:
            # Fetch user health data from MongoDB
            user_health_data = list(db['user_health'].find({'user_id': user_id}))

            if user_health_data:
                bp = [float(record['blood_pressure']) for record in user_health_data]
                bs = [float(record['blood_sugar']) for record in user_health_data]
                date = [record['date_log'] for record in user_health_data]  # Ensure 'date_log' is in a displayable format

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
@performance_analysis
def doctor_dashboard():
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Fetch distinct medication types from MongoDB
            medications = db['Medications'].distinct('med_type')  # Get unique medication types

            # Convert the list of distinct medication types
            med_types = list(medications)

            # Get the doctor ID (user_id) from the session
            doctor_id = session['user_id']

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

        # Check if there's already a schedule for tomorrow
        existing_rows = list(db['Clinic_Schedule'].find({'date': tomorrow}))

        if existing_rows:
            flash("Tomorrow's schedule already exists.", 'info')
            return redirect(url_for('doctor_dashboard'))

        # Define the time slots
        time_slots = [('10:00', '12:00'), ('14:00', '17:00')]

        # Add time slots to MongoDB
        for time_range in time_slots:
            start_time = datetime.strptime(time_range[0], '%H:%M')
            end_time = datetime.strptime(time_range[1], '%H:%M')

            while start_time < end_time:
                schedule_id = get_next_id('Clinic_Schedule')  # Auto-increment ID function for MongoDB

                # Insert a 30-minute interval into MongoDB
                db['Clinic_Schedule'].insert_one({
                    'schedule_id': schedule_id,
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
@performance_analysis
def submit_doctor_form():
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Retrieve form data
            user_id = int(request.form['user_id'])
            doctor_id = request.form['doc_id']
            doc_notes = request.form['doc_notes']
            blood_pressure = request.form['blood_pressure']
            blood_sugar = request.form['blood_sugar']
            med_name = request.form['med_name']
            issue_date = request.form['issue_date']
            visit_date = request.form['visit_date']
            cert_details = request.form['cert_details']

            # Step 1: Check if the user ID exists in the Users collection
            user = db['Users'].find_one({'user_id': user_id})

            if not user:
                flash(f"Error: User ID {user_id} does not exist.", 'danger')
                return redirect(url_for('doctor_dashboard'))

            # Generate IDs for the new documents
            MC_id = get_next_id('Medical_Cert')
            history_id = get_next_id('User_History')

            # Step 2: Insert medical certificate data into Medical_Cert collection
            cert_data = {
                'certificate_id': MC_id,
                'user_id': user_id,
                'doc_id': doctor_id,
                'issue_date': issue_date,
                'cert_details': cert_details
            }
            db['Medical_Cert'].insert_one(cert_data)
            cert_id = MC_id  # Certificate ID to link with User_History

            # Step 3: Insert health tracking data into User_History collection with the retrieved certificate_id
            history_data = {
                'history_id': history_id,
                'user_id': user_id,
                'doc_id': doctor_id,
                'doc_notes': doc_notes,
                'blood_pressure': blood_pressure,
                'blood_sugar': blood_sugar,
                'prescribed_med': med_name,
                'visit_date': visit_date,
                'certificate_id': cert_id
            }
            db['User_History'].insert_one(history_data)

            # Flash a success message
            flash('Doctor form details submitted successfully.', 'success')

        except Exception as e:
            # Flash an error message
            flash(f"Error submitting doctor form: {e}", 'danger')

        return redirect(url_for('doctor_dashboard'))


@app.route('/get_user_history/<user_id>', methods=['GET'])
@performance_analysis
def get_user_history(user_id):
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Ensure that user_id is an integer
            user_id = int(user_id)
            print(f"Searching for history with user_id: {user_id}")

            # Fetch all history for the given user_id from MongoDB
            user_history = list(db['User_History'].find({'user_id': user_id}))

            # Convert to a list of dictionaries for JSON response
            history_list = [{'history_id': record['history_id']} for record in user_history]

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
            # Ensure user_id is treated as an integer
            user_id = int(user_id)

            # Fetch and sort the top 5 history records for the given user_id by 'visit_date' in descending order
            user_history = list(
                db['User_History'].find({'user_id': user_id}).sort('visit_date', -1).limit(5)
            )

            # Fetch doctor name based on doc_id for each record
            doctor_name = None
            if user_history:
                doc_id = int(user_history[0]['doc_id'])  # Assuming doc_id is consistent across the top 5 entries
                doctor_data = db['Users'].find_one({'user_id': doc_id})
                doctor_name = doctor_data['username'] if doctor_data else None

            # Fetch patient name based on user_id
            patient_data = db['Users'].find_one({'user_id': user_id})
            patient_name = patient_data['username'] if patient_data else None

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
                } for record in user_history
            ]

            return jsonify(records)

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Unauthorized'}), 401


@app.route('/get_medications/<med_type>', methods=['GET'])
@performance_analysis
def get_medications(med_type):
    if 'username' in session and session['user_role'] == 'doctor':
        try:
            # Fetch medications based on the selected type from MongoDB
            meds = db['Medications'].find({'med_type': med_type})

            # Convert MongoDB documents to a list of dictionaries for JSON response
            med_list = [{'med_name': med['med_name']} for med in meds]

            return jsonify(med_list)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Unauthorized'}), 401


@app.route('/settings')
@performance_analysis
def settings():
    if 'username' in session and (session['user_role'] == 'user' or session['user_role'] == 'doctor'):
        try:
            # Fetch user details by username from MongoDB
            user_data = db['Users'].find_one({'username': session['username']})

            if user_data:
                email = user_data.get('email_add')
                phone_number = user_data.get('phone_number')
                address = user_data.get('address')

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
        # Update email, phone number, and address in MongoDB
        update_data = {
            'email_add': email,
            'phone_number': phone_number,
            'address': address
        }

        # Add hashed password to update data if provided
        if password:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            update_data['password'] = hashed_password

        # Perform the update in MongoDB
        db['Users'].update_one({'username': username}, {'$set': update_data})

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
            # Delete user document from MongoDB
            db['Users'].delete_one({'username': username})

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
            # Get user data from MongoDB
            user_data = db['Users'].find_one({'username': username})
            if user_data:
                user_id = user_data['user_id']  # Fetch the user_id from the document data

                blood_pressure = request.form.get('blood-pressure')
                blood_sugar = request.form.get('blood-sugar')

                if not blood_pressure or not blood_sugar:
                    flash('Please enter valid blood pressure and blood sugar values.', 'danger')
                    return redirect(url_for('user_health'))

                date_log = datetime.now().isoformat()

                health_id = get_next_id('user_health')

                # Insert health data into MongoDB user_health collection
                db['user_health'].insert_one({
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

        # Fetch clinic schedule from MongoDB
        clinic_schedule = db['Clinic_Schedule'].find()

        for schedule in clinic_schedule:
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
        formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        flash('Invalid date format. Please try again.', 'danger')
        return redirect(url_for('appointment'))

    try:
        # Fetch the schedule document based on date and time from MongoDB
        schedule = db['Clinic_Schedule'].find_one({
            'date': formatted_date,
            'time': time_slot
        })

        if not schedule:
            flash('No valid schedule found for the selected date and time.', 'danger')
            return redirect(url_for('appointment'))

        # Get the 'schedule_id' from the schedule data
        schedule_id = schedule.get('schedule_id')
        appt_id = get_next_id('appointments')

        # Update the clinic schedule status to 'booked'
        db['Clinic_Schedule'].update_one(
            {'schedule_id': schedule_id},
            {'$set': {'status': 'booked'}}
        )

        # Insert a new appointment
        db['appointments'].insert_one({
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

        print(f"Edit request for user_id: {user_id}, current_time: {current_time}, new_time: {new_time}, date: {formatted_date}")

        # Step 1: Find the current schedule_id for the user's existing appointment
        current_appointment = db['appointments'].find_one({'user_id': user_id})
        if not current_appointment:
            print("No appointment found for the provided date and current time.")
            return jsonify({'error': 'No appointment found to edit.'}), 400

        current_schedule_id = current_appointment['schedule_id']

        # Verify if the appointment date and time match the provided data
        current_schedule = db['Clinic_Schedule'].find_one({
            'schedule_id': current_schedule_id,
            'date': formatted_date,
            'time': current_time
        })
        if not current_schedule:
            print("No matching appointment found for the provided date and time.")
            return jsonify({'error': 'No matching appointment found for the provided date and time.'}), 400

        # Step 2: Find the new schedule_id for the selected new time
        new_schedule = db['Clinic_Schedule'].find_one({
            'date': formatted_date,
            'time': new_time,
            'status': 'available'
        })
        if not new_schedule:
            print("No available time slot for the selected time.")
            return jsonify({'error': 'No available time slot for the selected time.'}), 400

        new_schedule_id = new_schedule['schedule_id']

        # Step 3: Update the Clinic_Schedule collection
        # 1. Set the old time slot status back to 'available'
        # 2. Set the new time slot status to 'booked'
        db['Clinic_Schedule'].update_one(
            {'schedule_id': current_schedule_id},
            {'$set': {'status': 'available'}}
        )
        db['Clinic_Schedule'].update_one(
            {'schedule_id': new_schedule_id},
            {'$set': {'status': 'booked'}}
        )

        # Step 4: Update the appointment to the new schedule_id
        db['appointments'].update_one(
            {'user_id': user_id, 'schedule_id': current_schedule_id},
            {'$set': {'schedule_id': new_schedule_id}}
        )

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

        # Query MongoDB for available slots on the selected date
        results = db['Clinic_Schedule'].find({
            'date': formatted_date,
            'status': 'available'
        })

        # Extract available time slots
        available_time_slots = [doc['time'] for doc in results]

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

        # Fetch user's appointments from MongoDB
        appointments = list(db['appointments'].find({'user_id': user_id}))

        for appointment in appointments:
            schedule_id = appointment.get('schedule_id')

            # Query `Clinic_Schedule` using the `schedule_id` field
            schedule = db['Clinic_Schedule'].find_one({'schedule_id': schedule_id})

            if schedule and schedule['date'] == parsed_date:
                return jsonify({
                    'hasAppointment': True,
                    'appointmentTime': schedule['time'],
                    'message': 'You already have an appointment for today.'
                })

        # If no appointments, get available slots for that date
        available_slots = db['Clinic_Schedule'].find({
            'date': parsed_date,
            'status': 'available'
        })

        available_time_slots = [slot['time'] for slot in available_slots]
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

        # Find the schedule in MongoDB using the `date` and `time`
        schedule = db['Clinic_Schedule'].find_one({
            'date': formatted_date,
            'time': time
        })

        if not schedule:
            return jsonify({'error': 'No appointment found'}), 400

        # Get the `schedule_id` from the document data
        schedule_id = schedule.get('schedule_id')

        # Find and delete the appointment from MongoDB using `schedule_id` and `user_id`
        result = db['appointments'].delete_one({
            'user_id': user_id,
            'schedule_id': schedule_id
        })

        if result.deleted_count == 0:
            return jsonify({'error': 'No appointment found to cancel'}), 400

        # Update the clinic schedule status back to 'available'
        db['Clinic_Schedule'].update_one(
            {'schedule_id': schedule_id},
            {'$set': {'status': 'available'}}
        )

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
            appointments = db['appointments'].find()
            appointments_list = []

            for appointment in appointments:
                schedule = db['Clinic_Schedule'].find_one({'schedule_id': appointment['schedule_id']})

                # Check if the appointment is for today and its status is 'booked'
                if schedule and schedule['date'] == today and schedule['status'] == 'booked':
                    print("Found a matching appointment!")  # Debugging print

                    try:
                        user = db['Users'].find_one({'user_id': appointment['user_id']})

                        if user:
                            # Prepare the appointment details
                            appointment_entry = {
                                'patient': user['username'],
                                'date': schedule['date'],
                                'time': schedule['time']
                            }
                            appointments_list.append(appointment_entry)
                        else:
                            print(f"User not found for user_id: {appointment['user_id']}")
                    except Exception as e:
                        print(f"Error fetching user data: {str(e)}")
                        return jsonify({'error': f"User data fetch error: {str(e)}"}), 500

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
            # Find the schedule document based on the date and time
            schedule = db['Clinic_Schedule'].find_one({
                'date': date,
                'time': time
            })

            if schedule:
                schedule_id = schedule['schedule_id']

                # Update the status in the Appointments collection to 'No-Show'
                db['appointments'].update_many(
                    {'schedule_id': schedule_id},
                    {'$set': {'status': 'No-Show'}}
                )

                # Update the status in the Clinic_Schedule collection
                db['Clinic_Schedule'].update_one(
                    {'schedule_id': schedule_id},
                    {'$set': {'status': 'No-Show'}}
                )

                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'message': 'Schedule not found'})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': False, 'message': 'Unauthorized'}), 401

if __name__ == "__main__":
    app.run(debug=True)