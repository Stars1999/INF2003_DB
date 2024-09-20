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

