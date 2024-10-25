import firebase_admin
from firebase_admin import credentials, firestore

# Firebase initialization
cred = credentials.Certificate("inf2003-2ba47-firebase-adminsdk-kwxph-97051cd15f.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Medication data
medications = [
    {"medication_id": "1", "med_name": "Benylin Cough Syrup", "med_description": "Used for the temporary relief of coughs.", "med_type": "Cough", "med_quantity": 100},
    {"medication_id": "2", "med_name": "Robitussin CoughGels", "med_description": "Cough suppressant in gel form.", "med_type": "Cough", "med_quantity": 100},
    {"medication_id": "3", "med_name": "Tamiflu", "med_description": "An antiviral medication used for treating flu.", "med_type": "Flu", "med_quantity": 100},
    {"medication_id": "4", "med_name": "Theraflu", "med_description": "A combination medication that treats flu symptoms.", "med_type": "Flu", "med_quantity": 100},
    {"medication_id": "5", "med_name": "Tylenol", "med_description": "Pain reliever and a fever reducer.", "med_type": "Fever", "med_quantity": 100},
    {"medication_id": "6", "med_name": "Advil", "med_description": "Ibuprofen-based medication used for fever and pain.", "med_type": "Fever", "med_quantity": 100}
]

# Function to upload medication data to Firestore
def upload_data():
    try:
        # Add medications to Firestore
        for med in medications:
            db.collection('Medications').add(med)
        print("Medications uploaded successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    upload_data()
