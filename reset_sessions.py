from app.database import get_db

db = get_db()
res = db.chat_sessions.delete_many({})
print(f"🗑️ Deleted {res.deleted_count} sessions.")
