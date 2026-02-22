from app.database import get_db
import sys

db = get_db()
wa_id = sys.argv[1] if len(sys.argv) > 1 else None

if not wa_id:
    print("Usage: python check_session.py <wa_id>")
    sys.exit(1)

session = db.chat_sessions.find_one({"wa_id": wa_id})
if session:
    print(f"Session for {wa_id}:")
    print(f"  State: {session.get('state')}")
    print(f"  Data: {session.get('data')}")
else:
    print(f"No session found for {wa_id}")
