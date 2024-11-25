from pymongo import MongoClient


def create_mongo_connection():
    """Create a MongoDB connection"""
    try:
        # Adjust the connection string as per your MongoDB instance
        client = MongoClient('mongodb://localhost:27017/')
        db = client['INF2003_Proj_DB']
        print("Connected to MongoDB successfully")
        return db
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None