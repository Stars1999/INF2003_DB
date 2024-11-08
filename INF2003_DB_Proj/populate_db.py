from pymongo import MongoClient

# MongoDB connection string
client = MongoClient("mongodb+srv://2301772:Pa55w0rd@inf2003.n4h2o.mongodb.net/?retryWrites=true&w=majority")

# Specify the database and collection
db = client['INF2003']
medications_collection = db['Medications']

# Medication data
medications = [
    {"medication_id": "1", "med_name": "Benylin Cough Syrup", "med_description": "Used for the temporary relief of coughs.", "med_type": "Cough", "med_quantity": 100},
    {"medication_id": "2", "med_name": "Robitussin CoughGels", "med_description": "Cough suppressant in gel form.", "med_type": "Cough", "med_quantity": 100},
    {"medication_id": "3", "med_name": "Tamiflu", "med_description": "An antiviral medication used for treating flu.", "med_type": "Flu", "med_quantity": 100},
    {"medication_id": "4", "med_name": "Theraflu", "med_description": "A combination medication that treats flu symptoms.", "med_type": "Flu", "med_quantity": 100},
    {"medication_id": "5", "med_name": "Tylenol", "med_description": "Pain reliever and a fever reducer.", "med_type": "Fever", "med_quantity": 100},
    {"medication_id": "6", "med_name": "Advil", "med_description": "Ibuprofen-based medication used for fever and pain.", "med_type": "Fever", "med_quantity": 100}
]

# Function to upload medication data to MongoDB
def upload_data():
    try:
        # Insert medications into MongoDB collection
        medications_collection.insert_many(medications)
        print("Medications uploaded successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    upload_data()
