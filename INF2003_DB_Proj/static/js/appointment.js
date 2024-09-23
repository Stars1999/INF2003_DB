window.addEventListener('load', function() {
      let availabilityData = {};  // To store availability data

      fetch('/available-dates')
        .then(response => response.json())
        .then(data => {
          availabilityData = data;  // Store the availability data

          // Initialize the Pikaday calendar
          var picker = new Pikaday({
            field: document.getElementById('calendar-container'), // Attach to the container
            bound: false, // Display inline instead of as a dropdown
            container: document.getElementById('calendar-container'), // Specify the container for inline display
            onDraw: function() {
              updateDateColors(availabilityData);  // Update date colors
            },
            format: 'YYYY-MM-DD',  // Force the format to yyyy-mm-dd
            onSelect: function(date) {
              var selectedDate = picker.toString('YYYY-MM-DD');  // Format the date as yyyy-mm-dd
              console.log(`Selected Date: ${selectedDate}`);  // Log the selected date
              checkAppointment(selectedDate);  // Use the formatted date
            }
          });
        })
        .catch(error => console.error('Error fetching available dates:', error));


      // Function to update calendar date colors
      function updateDateColors(availabilityData) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);  // Normalize today's date

        const allDateCells = document.querySelectorAll('.pika-day');
        allDateCells.forEach(cell => {
          const year = cell.getAttribute('data-pika-year');
          const month = parseInt(cell.getAttribute('data-pika-month'));
          const day = parseInt(cell.getAttribute('data-pika-day'));
          const cellDate = new Date(year, month, day);

          // Disable past dates by adding the "disabled" class
          if (cellDate < today) {
            cell.classList.add('disabled');
          }

          // Color future dates based on availability
          const formattedDate = `${year}-${(month + 1).toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
          if (availabilityData[formattedDate]) {
            if (availabilityData[formattedDate].fullyBooked) {
              cell.classList.add('fully-booked');  // Mark as fully booked
            } else {
              cell.classList.add('available');  // Mark as available
            }

            // Add appointment label inside the calendar cell
            if (availabilityData[formattedDate].appointments.length > 0) {
              let appointmentLabel = document.createElement('div');
              appointmentLabel.classList.add('appointment-label');

              // Add each appointment time as a label
              availabilityData[formattedDate].appointments.forEach(time => {
                const appointmentTime = document.createElement('span');
                appointmentTime.textContent = `Appointment @ ${time}`;
                appointmentLabel.appendChild(appointmentTime);
              });

              // Insert the label into the cell
              cell.appendChild(appointmentLabel);
            }
          }
        });
      }

      // Function to check if the user has an appointment on the selected date
        function checkAppointment(date) {
          fetch(`/check-appointment?date=${date}`)
            .then(response => response.json())
            .then(data => {
              let appointmentDetailsHTML = `<h3></h3>`;

              if (data.hasAppointment) {
                // User already has an appointment, show appointment details
                appointmentDetailsHTML += `<p>Current Appointment @ ${data.appointmentTime}</p>`;
                appointmentDetailsHTML += `<p>You already have an appointment for today.</p>`;

                // Display the Edit and Cancel buttons
                appointmentDetailsHTML += `
                  <div class="button-container">
                    <button id="edit-appointment-btn" class="edit-appointment">Edit Appointment</button>
                    <button id="cancel-appointment-btn" class="cancel-appointment">Cancel Appointment</button>
                  </div>
                `;

                // Render the appointment details
                document.getElementById('appointment-details').innerHTML = appointmentDetailsHTML;

                // Attach event listeners to the buttons
                document.getElementById('cancel-appointment-btn').addEventListener('click', function() {
                  cancelAppointment(date, data.appointmentTime);  // Directly passing the actual variables
                });

                document.getElementById('edit-appointment-btn').addEventListener('click', function() {
                  editAppointment(date, data.appointmentTime);  // Directly passing the actual variables
                });
              } else {
                // No appointment for this date
                appointmentDetailsHTML += `<p>No appointment for this date. Select an available time slot to book an appointment.</p>`;
                loadTimeSlots(date, data.availableTimeSlots); // Load available time slots for booking
              }
            })
            .catch(error => {
              console.error('Error checking appointment:', error);
              document.getElementById('appointment-details').innerHTML = `<p>Error fetching appointment details. Please try again later.</p>`;
            });
        }

      // Function to load available time slots and render dropdown
      function loadTimeSlots(date) {
        fetch(`/available_timeslots?date=${date}`)
          .then(response => response.json())
          .then(data => {
            let timeslotsHTML = '<h3>Available Time Slots</h3><form action="/book-appointment" method="POST">';
            timeslotsHTML += `<input type="hidden" name="date" id="date" value="${date}">`;

            if (data.timeslots.length > 0) {
              timeslotsHTML += '<div><label for="timeslot">Select a time slot: </label>';
              timeslotsHTML += '<select name="timeslot" id="timeslot" required>';
              data.timeslots.forEach(slot => {
                timeslotsHTML += `<option value="${slot}">${slot}</option>`;
              });
              timeslotsHTML += '</select></div>';
              timeslotsHTML += '<button type="submit">Book Appointment</button>';
            } else {
              timeslotsHTML += '<p>No available time slots for this date.</p>';
            }
            timeslotsHTML += '</form>';
            document.getElementById('appointment-details').innerHTML = timeslotsHTML;
          })
          .catch(error => console.error('Error fetching time slots:', error));
      }

      // Global cancelAppointment function
      function cancelAppointment(date, currentTime) {
        console.log("Cancel appointment function called");  // Debugging step

        if (confirm('Are you sure you want to cancel this appointment?')) {
          fetch(`/cancel-appointment`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ date: date, time: currentTime })
          })
          .then(response => response.json())
          .then(data => {
            if (data.error) {
              console.error("Error canceling appointment:", data.error);
              alert(`Error: ${data.error}`);
            } else {
              alert('Appointment canceled successfully');
              // Reload or update the calendar to reflect the changes
              location.reload();
            }
          })
          .catch(error => {
            console.error('Error canceling appointment (catch):', error);
            alert('Error canceling appointment. Please check console for details.');
          });
        }
      }

      // Global editAppointment function
      function editAppointment(date, currentTime) {
        fetch(`/available_timeslots?date=${date}`)
          .then(response => response.json())
          .then(data => {
            let editFormHTML = `
              <h3>Edit Appointment</h3>
              <form id="edit-appointment-form">
                <input type="hidden" name="date" value="${date}">
                <input type="hidden" name="currentTime" value="${currentTime}">
                <label for="newTime">Select a new time slot:</label>
                <select name="newTime" id="newTime" required>
            `;

            data.timeslots.forEach(slot => {
              editFormHTML += `<option value="${slot}">${slot}</option>`;
            });

            editFormHTML += `</select><button type="submit">Submit</button></form>`;

            document.getElementById('appointment-details').innerHTML = editFormHTML;

            // Handle form submission via fetch
            document.getElementById('edit-appointment-form').addEventListener('submit', function(event) {
              event.preventDefault();

              const newTime = document.getElementById('newTime').value;

              if (confirm('Are you sure you want to edit this appointment?')) {
                fetch(`/edit-appointment`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify({
                    date: date,
                    currentTime: currentTime,
                    newTime: newTime
                  })
                })
                .then(response => response.json())
                .then(data => {
                  if (data.error) {
                    console.error("Error editing appointment:", data.error);
                    alert(`Error: ${data.error}`);
                  } else {
                    alert('Appointment edited successfully');
                    location.reload();
                  }
                })
                .catch(error => {
                  console.error('Error editing appointment:', error);
                  alert('Error editing appointment. Please check console for details.');
                });
              }
            });
          })
          .catch(error => console.error('Error fetching available time slots for editing:', error));
      }

    });