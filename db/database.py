import os
import datetime
import logging
from pymongo import MongoClient

# Get MONGO_URI from env or default to 127.0.0.1 to avoid IPv6 localhost issues
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27018")

# Use a very short timeout so Streamlit starts up fast even if MongoDB isn't running
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)

db = client["codesage"]
history_collection = db["chat_history"]

# We remove the cached server_info check because Streamlit caches module states.
# PyMongo automatically manages connection pools and will reconnect when you query.

def save_chat_query(question: str, answer: str, model_used: str):
    """Saves the user's question and AI's answer into MongoDB for later retrieval."""
    try:
        history_collection.insert_one({
            "question": question,
            "answer": answer,
            "model_used": model_used,
            "timestamp": datetime.datetime.utcnow()
        })
    except Exception as e:
        print(f"Failed to record chat history to MongoDB: {e}")

def get_recent_chat_history(limit: int = 20):
    """Fetches the N most recent queries directly from the MongoDB database."""
    try:
        # Fetch, sort by newest time (descending), and restrict to a limit
        cursor = history_collection.find().sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        print(f"Failed to retrieve chat history from MongoDB: {e}")
        return []
