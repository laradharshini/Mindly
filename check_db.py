from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client.get_database()

sessions = list(db.counseling_sessions.find())
print(f"Total Sessions: {len(sessions)}")
for s in sessions:
    print(f"ID: {s['_id']}, Status: {s.get('status')}, Student: {s.get('student_wa_id')}")
