// JS to handle dynamic loading of medication names based on selected type
function loadMedicationNames() {
  const medType = document.getElementById('med_type').value;
  // Fetch and update the medication names dropdown based on the selected type
}

// Auto-fill today's date for the issue date
window.onload = function() {
  const today = new Date().toISOString().split('T')[0];
  document.getElementById("visit_date").value = today;
  document.getElementById("issue_date").value = today;
  loadMedicationNames();
  loadTodayAppointments();
};

// JavaScript function to dynamically load medication names based on selected type
function loadMedicationNames() {
  const medType = document.getElementById('med_type').value;

  fetch(`/get_medications/${medType}`)
    .then(response => response.json())
    .then(data => {
      const medNameSelect = document.getElementById('med_name');
      medNameSelect.innerHTML = '';

      data.forEach(med => {
        const option = document.createElement('option');
        option.value = med.med_name;
        option.text = med.med_name;
        medNameSelect.appendChild(option);
      });
    })
    .catch(error => console.error('Error fetching medication names:', error));
}

// Function to generate and display the next queue number
function generateNextQueueNumber() {
  // Generate a random queue number between 1 and 100
  const nextQueueNumber = Math.floor(Math.random() * 100) + 1;

  // Update the queue number display in the card
  document.getElementById('queue-number').querySelector('span').textContent = nextQueueNumber;
}

// Function to search for user history by User ID and show the top 5 records
function searchUserHistory() {
  const userID = document.getElementById('search_user_id').value;

  // Fetch the top 5 user history from the server
  fetch(`/get_user_history_top5/${userID}`)
    .then(response => response.json())
    .then(data => {
      if (data.length > 0) {
        console.log('Received data:', data);  // Debugging

        // Get the history details container
        const historyDetailsContainer = document.getElementById('history-details');

        // Clear any previous details
        historyDetailsContainer.innerHTML = '';

        // Show the history details section
        historyDetailsContainer.style.display = 'block';

        // Create and append new elements for the top 5 records
        data.forEach((history, index) => {
          const historyElement = document.createElement('div');
          historyElement.classList.add('history-record');

          // Display each history record
          historyElement.innerHTML = `
            <h4>Record ${index + 1}</h4>
            <p><strong>Doctor Notes:</strong> ${history.doc_notes || 'N/A'}</p>
            <p><strong>Blood Pressure:</strong> ${history.blood_pressure || 'N/A'}</p>
            <p><strong>Blood Sugar:</strong> ${history.blood_sugar || 'N/A'}</p>
            <p><strong>Visit Date:</strong> ${history.visit_date || 'N/A'}</p>
            <p><strong>Prescribed Med:</strong> ${history.prescribed_med || 'N/A'}</p>
            <p><strong>Patient Name:</strong> ${history.patient_name || 'N/A'}</p>
            <p><strong>Doctor Name:</strong> ${history.doctor_name || 'N/A'}</p>
            <hr>
          `;

          // Append each record to the history details container
          historyDetailsContainer.appendChild(historyElement);
        });
      } else {
        alert('No history records found for this user.');
      }
    })
    .catch(error => {
      console.error('Error fetching user history:', error);
      alert('Failed to retrieve user history. Please try again.');
    });
}

// Automatically hide flash messages after 5 seconds
setTimeout(function() {
const flashMessage = document.getElementById('flash-message');
if (flashMessage) {
  flashMessage.style.display = 'none';
}
}, 5000); // 5000ms = 5 seconds

// Function to fetch today's appointments and display them in the card
function loadTodayAppointments() {
  fetch('/get_today_appointments')
    .then(response => response.json())
    .then(data => {
      const appointmentList = document.getElementById('appointment-list');
      appointmentList.innerHTML = '';  // Clear any previous content

      if (data.length > 0) {
        data.forEach(appointment => {
          const card = document.createElement('div');
          card.classList.add('appointment-card');

          card.innerHTML = `
            <div class="appointment-header">
              <h4>Patient Name: ${appointment.patient}</h4>
            </div>
            <div class="appointment-details">
              <p><strong>Timeslot:</strong> ${appointment.time}</p>
            </div>
            <button class="no-show-button" onclick="markNoShow(${appointment.user_id}, '${appointment.date}', '${appointment.time}')">Mark No-Show</button>
          `;
          appointmentList.appendChild(card);
        });
      } else {
        // If no appointments for today, display a message
        const noAppointments = document.createElement('div');
        noAppointments.classList.add('no-appointments');
        noAppointments.textContent = 'No appointments booked for today.';
        appointmentList.appendChild(noAppointments);
      }
    })
    .catch(error => {
      console.error('Error fetching today\'s appointments:', error);
    });
}

// Function to mark an appointment as No-Show
function markNoShow(user_id, date, time) {
  fetch('/mark_no_show', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: user_id,
      date: date,
      time: time
    }),
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert('Appointment marked as No-Show successfully!');
      loadTodayAppointments();  // Reload the appointments list after update
    } else {
      alert('Failed to mark No-Show.');
    }
  })
  .catch(error => {
    console.error('Error:', error);
  });
}





