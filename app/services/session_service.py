from app.database import get_db
import datetime

def get_user_session(wa_id):
    """
    Retrieves or creates a session for a WhatsApp ID.
    """
    db = get_db()
    session = db.chat_sessions.find_one({"wa_id": wa_id})
    
    if not session:
        session = {
            "wa_id": wa_id,
            "state": "START",
            "data": {},
            "updated_at": datetime.datetime.utcnow()
        }
        db.chat_sessions.insert_one(session)
    
    return session

def update_user_session(wa_id, state=None, data=None):
    """
    Updates the session state and/or temp data for a user.
    """
    db = get_db()
    updates = {"updated_at": datetime.datetime.utcnow()}
    
    if state:
        updates["state"] = state
    if data is not None:
        updates["data"] = data
        
    db.chat_sessions.update_one(
        {"wa_id": wa_id},
        {"$set": updates}
    )

def clear_user_session(wa_id):
    """
    Resets the session to the START state.
    """
    update_user_session(wa_id, state="START", data={})
