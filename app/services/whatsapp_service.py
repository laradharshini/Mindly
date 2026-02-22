import google.generativeai as genai
import requests
import json
import datetime
from app.config import Config
from app.database import get_db

# Configure Gemini
genai.configure(api_key=Config.GEMINI_API_KEY)

# Risk Classification Model and Prompt
risk_model = genai.GenerativeModel('gemini-2.5-flash')

RISK_CLASSIFICATION_SYSTEM_PROMPT = """You are an emotional risk classification system for a student mental health support platform.

Your task is to analyze the user's message and classify their psychological risk level into ONLY ONE of the following categories:

LOW
MODERATE
HIGH
CRITICAL

Classification Rules:

LOW:
• Mild stress
• Normal frustration
• Everyday academic pressure
• No signs of emotional instability

MODERATE:
• Clear anxiety
• Feeling overwhelmed
• Academic burnout signs
• Emotional distress but still coping

HIGH:
• Severe distress
• Strong hopeless tone
• Emotional breakdown
• Statements like "I can't do this anymore"
• Feeling empty, worthless, or lost

CRITICAL:
• Suicidal thoughts (direct or indirect)
• Self-harm ideation
• Wanting to disappear permanently
• No reason to live
• Life is meaningless
• Giving up on existence
• Indirect phrases implying self-harm intent

IMPORTANT RULES:
• Consider tone, intent, and context — not just keywords.
• Even indirect suicidal hints must be classified as CRITICAL.
• Do not be conservative. If unsure between HIGH and CRITICAL, choose CRITICAL.
• Respond with ONLY ONE WORD from the four categories.
• Do NOT explain.
• Do NOT add punctuation.
• Do NOT add extra text.

Output must include the text message from the user and be exactly one of:
LOW
MODERATE
HIGH
CRITICAL"""

MINDLY_SYSTEM_PROMPT = """You are "Mindly", a compassionate AI mental health support assistant designed specifically for college and university students.

Your purpose is to:
• Identify early signs of academic stress, anxiety, burnout, and emotional distress.
• Provide empathetic, non-judgmental, and supportive responses.
• Offer simple, practical coping strategies tailored to student life.
• Encourage healthy academic habits and emotional well-being.

GUIDELINES:

1. Tone:
• Be warm, calm, and emotionally supportive.
• Use simple, human-like language.
• Avoid clinical or technical jargon.
• Do not sound robotic or overly formal.

2. Student Context Awareness:
• Consider common student challenges like exams, deadlines, peer pressure, career uncertainty, sleep issues, and academic burnout.
• Tailor advice specifically to academic situations.

3. Stress Identification:
• If the user expresses feeling overwhelmed, anxious, pressured, exhausted, hopeless, or unable to cope, recognize it as stress.
• Gently validate their emotions before giving suggestions.
Example: "That sounds really overwhelming. It's completely understandable to feel this way during exam time."

4. Provide Structured Support:
Offer:
• Breathing or grounding techniques
• Time management suggestions
• Study restructuring tips
• Short emotional reframing prompts
• Encouragement to take small achievable steps

5. Crisis Handling:
If a user expresses self-harm, suicidal thoughts, or severe hopelessness:
• Respond with care and seriousness.
• Encourage them to seek immediate professional help.
• Suggest contacting a trusted adult, campus counselor, or local emergency services.
• Do NOT attempt to replace professional help.

6. Boundaries:
• Do not diagnose mental health conditions.
• Do not provide medical advice.
• Do not act as a licensed therapist.
• Position yourself as supportive guidance, not a replacement for professional care.

7. Privacy and Safety:
• Reinforce that their feelings are valid.
• Encourage healthy coping.
• Avoid harmful or extreme suggestions.

SYSTEM INTERNAL CONTEXT (Not visible to user):

The user’s emotional risk level is: {risk_level}
This is confidential internal system metadata.
You must:
• Use it only to adjust empathy level and urgency.
• Never mention it.
• Never refer to risk levels.
• Never say LOW, MODERATE, HIGH, or CRITICAL.
• Never thank the user for their risk level.
• Respond naturally as if you do not know this label explicitly.
Your goal is to create a safe, confidential, and student-friendly space that supports early stress awareness and emotional balance. {risk_level}"""

def classify_risk(user_message):
    """
    Classifies the user's emotional risk level.
    """
    try:
        chat = risk_model.start_chat()
        response = chat.send_message(f"{RISK_CLASSIFICATION_SYSTEM_PROMPT}\n\nUser message: {user_message}")
        risk_level = response.text.strip().upper()
        # Ensure it's one of the valid categories
        if risk_level not in ["LOW", "MODERATE", "HIGH", "CRITICAL"]:
            # Fallback logic if Gemini persists with extra text
            for level in ["CRITICAL", "HIGH", "MODERATE", "LOW"]:
                if level in risk_level:
                    return level
            return "LOW"
        return risk_level
    except Exception as e:
        print(f"Error in risk classification: {e}")
        return "LOW"

def generate_mindly_response(user_message, risk_level):
    """
    Generates a Mindly response based on user message and risk level.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = MINDLY_SYSTEM_PROMPT.format(risk_level=risk_level)
        response = model.generate_content(f"{prompt}\n\nUser message: {user_message}")
        return response.text
    except Exception as e:
        print(f"Error in Mindly response generation: {e}")
        return "I'm here for you and I want to help. Would you like to tell me more about what's on your mind?"

def handle_conversational_flow(wa_id, message_text, session, is_button=False):
    """
    Main state machine for Mindly WhatsApp conversations.
    """
    state = session.get("state", "START")
    data = session.get("data", {})
    text = message_text.strip()
    
    db = get_db()
    
    # Global Reset Command
    if text.upper() in ["RESET", "START", "HI", "HELLO"]:
        # 1. Check if user already exists in DB
        user = db.users.find_one({"wa_id": wa_id})
        if user:
            role = user.get("role", "student").capitalize()
            if role == "Doctor":
                pending_count = db.counseling_sessions.count_documents({"status": "Pending"})
                response = (f"Welcome back, Dr. {user['name']}! 🩺\n\n"
                            f"Your dashboard:\n"
                            f"• Pending Sessions: {pending_count}\n"
                            f"• Status: Active")
                
                buttons = [{"id": "DR_VIEW_REQS", "title": "View Requests"}]
                
                return response, "DOCTOR_DASHBOARD", {"role": "Doctor", "name": user["name"]}, buttons, None
            else:
                response = f"Welcome back to Mindly, {user['name']}! 🎓\nHow can I support you today?"
                buttons = [
                    {"id": "STUDENT_SUPPORT", "title": "Support Chat"},
                    {"id": "STUDENT_BOOK", "title": "Book Session"},
                    {"id": "STUDENT_MY_SESSIONS", "title": "My Sessions"}
                ]
                return response, "STUDENT_MENU", {"role": "Student", "name": user["name"]}, buttons, None
        
        # New User Flow
        state = "START"
        data = {}

    if state == "START":
        # ... (rest of the code remains similar)
        response = "Welcome to Mindly 💙\nYour mental health companion. Please select your role to get started:"
        buttons = [
            {"id": "ROLE_STUDENT", "title": "I'm a Student"},
            {"id": "ROLE_DOCTOR", "title": "I'm a Doctor"},
            {"id": "ROLE_OTHER", "title": "Other"}
        ]
        return response, "ROLE_SELECTION", {}, buttons, None

    # --- DOCTOR DASHBOARD & 2-STEP MGMT ---
    elif state == "DOCTOR_DASHBOARD":
        if text == "DR_VIEW_REQS":
            pending_list = list(db.counseling_sessions.find({"status": "Pending"}).limit(10))
            if not pending_list:
                return "*No pending requests at the moment.*", "DOCTOR_DASHBOARD", data, None, None
            
            rows = []
            for i, sess in enumerate(pending_list):
                student = db.users.find_one({"wa_id": sess["student_wa_id"]})
                name = student.get("name", "Unknown") if student else "Unknown"
                display_name = (name[:20] + '..') if len(name) > 20 else name
                rows.append({
                    "id": f"DR_SEL_REQ_{sess['_id']}",
                    "title": f"{i+1}. {display_name}",
                    "description": f"{sess['date']} @ {sess['time']}"
                })
            
            # Action Rows for Step 1
            action_rows = [
                {"id": "DR_BULK_APPROVE_ALL", "title": "Approve All ✅", "description": "Approve all current requests"},
                {"id": "DR_BULK_DECLINE_ALL", "title": "Decline All ❌", "description": "Decline all current requests"},
                {"id": "DR_MODE_MULTI_SELECT", "title": "Select Multiple 📋", "description": "Pick specific students to approve"}
            ]
            
            list_data = {
                "button": "View/Manage",
                "sections": [
                    {"title": "Student List", "rows": rows},
                    {"title": "Bulk Actions", "rows": action_rows}
                ]
            }
            return "*Manage Requests*\nSelect a student to view details, or choose a bulk action below:", "DOCTOR_LIST_REQS", data, None, list_data
        
        elif text == "DR_DASHBOARD":
            return "*Refreshing dashboard...*", "START", data, None, None

    elif state == "DOCTOR_LIST_REQS":
        # Handle Single Selection Mode
        if text.startswith("DR_SEL_REQ_"):
            from bson import ObjectId
            session_id = text.replace("DR_SEL_REQ_", "")
            sess = db.counseling_sessions.find_one({"_id": ObjectId(session_id)})
            if sess:
                student = db.users.find_one({"wa_id": sess["student_wa_id"]})
                name = student.get("name", "Unknown") if student else "Unknown"
                response = (f"*Managing Request for:* {name}\n\n"
                            f"*Date:* {sess['date']}\n"
                            f"*Time:* {sess['time']}\n"
                            f"*Concern:* {sess['description']}\n\n"
                            "What would you like to do?")
                buttons = [
                    {"id": f"DR_APPROVE_{session_id}", "title": "Approve"},
                    {"id": f"DR_DECLINE_{session_id}", "title": "Decline"},
                    {"id": "DR_VIEW_REQS", "title": "Back to List"}
                ]
                return response, "DOCTOR_MANAGE_REQ", data, buttons, None

        # Bulk All Actions
        elif text == "DR_BULK_APPROVE_ALL":
            pending_list = list(db.counseling_sessions.find({"status": "Pending"}))
            for sess in pending_list:
                db.counseling_sessions.update_one({"_id": sess["_id"]}, {"$set": {"status": "Approved", "approved_by": wa_id}})
                send_whatsapp_message(sess["student_wa_id"], f"*Approved:* Your session for {sess['date']} @ {sess['time']} is confirmed! 🩺")
            return f"*Bulk Success:* {len(pending_list)} students approved!", "DOCTOR_DASHBOARD", data, [{"id": "DR_VIEW_REQS", "title": "View More"}], None

        elif text == "DR_BULK_DECLINE_ALL":
            res = db.counseling_sessions.update_many({"status": "Pending"}, {"$set": {"status": "Declined", "declined_by": wa_id}})
            return f"*Bulk Success:* {res.modified_count} students declined.", "DOCTOR_DASHBOARD", data, [{"id": "DR_VIEW_REQS", "title": "View More"}], None

        # --- STEP 2: MULTI-SELECT MODE (Checkbox Style) ---
        elif text == "DR_MODE_MULTI_SELECT" or text.startswith("DR_TOGGLE_"):
            if text.startswith("DR_TOGGLE_"):
                session_id = text.replace("DR_TOGGLE_", "")
                selected_ids = data.get("selected_ids", [])
                if session_id in selected_ids: selected_ids.remove(session_id)
                else: selected_ids.append(session_id)
                data["selected_ids"] = selected_ids

            pending_list = list(db.counseling_sessions.find({"status": "Pending"}).limit(10))
            selected_ids = data.get("selected_ids", [])
            rows = []
            for i, sess in enumerate(pending_list):
                student = db.users.find_one({"wa_id": sess["student_wa_id"]})
                name = student.get("name", "Unknown") if student else "Unknown"
                status_box = "☑️" if str(sess["_id"]) in selected_ids else "⬜"
                rows.append({"id": f"DR_TOGGLE_{sess['_id']}", "title": f"{status_box} {name}", "description": f"{sess['date']} @ {sess['time']}"})
            
            actions = []
            if selected_ids:
                actions.append({"id": "DR_BULK_SEL_APPROVE", "title": f"Approve Selected ({len(selected_ids)}) ✅", "description": "Approve all checked items"})
            actions.append({"id": "DR_VIEW_REQS", "title": "Back to Main Menu ⬅️", "description": "Exit Multi-Select"})

            list_data = {"button": "Select Students", "sections": [{"title": "Toggle selection", "rows": rows}, {"title": "Action", "rows": actions}]}
            
            prompt = ("*Select Multiple Mode*\n"
                      "Due to WhatsApp limits, you can pick one student at a time in the menu below. "
                      "It will re-open with your update.\n\n"
                      "🚀 *Turbo Tip:* Just *type* the numbers (e.g. `1,2,4`) to select many students at once!")
            
            return prompt, "DOCTOR_LIST_REQS", data, None, list_data

        # Handle Numeric Selection (Turbo Mode)
        elif any(char.isdigit() for char in (text if len(text) < 10 else "")): # Basic check for numbers in short messages
            pending_list = list(db.counseling_sessions.find({"status": "Pending"}).limit(10))
            selected_ids = data.get("selected_ids", [])
            import re
            numbers = re.findall(r'\d+', text)
            
            toggled_count = 0
            for num_str in numbers:
                try:
                    idx = int(num_str) - 1
                    if 0 <= idx < len(pending_list):
                        sid = str(pending_list[idx]["_id"])
                        if sid in selected_ids: selected_ids.remove(sid)
                        else: selected_ids.append(sid)
                        toggled_count += 1
                except: continue
            
            data["selected_ids"] = selected_ids
            # Re-trigger the same state handler to show the updated menu
            # Pass the full session object (state + data) for the recursive call
            return handle_conversational_flow(wa_id, "DR_MODE_MULTI_SELECT", {"state": "DOCTOR_LIST_REQS", "data": data}, is_button=True)

        # Final Approval for Selective Multi
        elif text == "DR_BULK_SEL_APPROVE":
            selected_ids = data.get("selected_ids", [])
            from bson import ObjectId
            for sid in selected_ids:
                sess = db.counseling_sessions.find_one({"_id": ObjectId(sid)})
                if sess:
                    db.counseling_sessions.update_one({"_id": ObjectId(sid)}, {"$set": {"status": "Approved", "approved_by": wa_id}})
                    send_whatsapp_message(sess["student_wa_id"], f"*Approved:* Your session for {sess['date']} @ {sess['time']} is confirmed! 🩺")
            data["selected_ids"] = []
            return f"*Success:* {len(selected_ids)} students approved & notified!", "DOCTOR_DASHBOARD", data, [{"id": "DR_VIEW_REQS", "title": "View More"}], None

    elif state == "DOCTOR_MANAGE_REQ":
        # Handle single approval/decline (kept stable)
        if text.startswith("DR_APPROVE_"):
            from bson import ObjectId
            session_id = text.replace("DR_APPROVE_", "")
            sess = db.counseling_sessions.find_one({"_id": ObjectId(session_id)})
            if sess:
                db.counseling_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"status": "Approved", "approved_by": wa_id}})
                send_whatsapp_message(sess["student_wa_id"], f"*Approved:* Your session for {sess['date']} @ {sess['time']} is confirmed! 🩺")
                return "*Session approved!*", "DOCTOR_DASHBOARD", data, [{"id": "DR_VIEW_REQS", "title": "View More"}], None
        elif text.startswith("DR_DECLINE_"):
            from bson import ObjectId
            session_id = text.replace("DR_DECLINE_", "")
            db.counseling_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"status": "Declined", "declined_by": wa_id}})
            return "*Session declined.*", "DOCTOR_DASHBOARD", data, [{"id": "DR_VIEW_REQS", "title": "View More"}], None
        elif text == "DR_VIEW_REQS":
            return "*Returning to list...*", "DOCTOR_DASHBOARD", data, [{"id": "DR_VIEW_REQS", "title": "Click to Reload"}], None

    # --- STUDENT FLOW & SESSION MGMT ---
    elif state == "STUDENT_MENU":
        if text == "STUDENT_SUPPORT":
            return ("*Emotional Support Mode* 💙\n"
                    "Tell me what's on your mind. (Type 'MENU' anytime to exit)"), "EMOTIONAL_SUPPORT", data, None, None
        elif text == "STUDENT_BOOK":
            return "*Session Booking*\n\nPlease type your preferred date (e.g., 2024-05-20):", "BOOKING_DATE", data, None, None
        elif text == "STUDENT_MY_SESSIONS":
            my_sessions = list(db.counseling_sessions.find({
                "student_wa_id": wa_id,
                "status": {"$in": ["Pending", "Approved"]}
            }).limit(10))
            
            if not my_sessions:
                return "*No active sessions found.*", "STUDENT_MENU", data, [{"id": "STUDENT_BOOK", "title": "Book One Now"}], None
            
            rows = []
            for i, sess in enumerate(my_sessions):
                rows.append({
                    "id": f"STUDENT_SEL_SESS_{sess['_id']}",
                    "title": f"{sess['date']} @ {sess['time']}",
                    "description": f"Status: {sess['status']}"
                })
            
            list_data = {
                "button": "View Session",
                "sections": [{"title": "Your Sessions", "rows": rows}]
            }
            return "*Your Sessions:*\nSelect one below to view details or cancel:", "STUDENT_MY_SESSIONS", data, None, list_data

    elif state == "STUDENT_MY_SESSIONS":
        if text.startswith("STUDENT_SEL_SESS_"):
            from bson import ObjectId
            session_id = text.replace("STUDENT_SEL_SESS_", "")
            sess = db.counseling_sessions.find_one({"_id": ObjectId(session_id)})
            if sess:
                response = (f"*Session Details*\n\n"
                            f"• *Date:* {sess['date']}\n"
                            f"• *Time:* {sess['time']}\n"
                            f"• *Status:* {sess['status']}\n"
                            f"• *Concern:* {sess['description']}\n\n"
                            "What would you like to do?")
                buttons = [
                    {"id": f"STUDENT_CANCEL_{session_id}", "title": "Cancel Session"},
                    {"id": "STUDENT_MY_SESSIONS", "title": "Back to List"}
                ]
                return response, "STUDENT_MANAGE_SESS", data, buttons, None
        return "*Back to Student Menu.*", "START", data, None, None

    elif state == "STUDENT_MANAGE_SESS":
        if text.startswith("STUDENT_CANCEL_"):
            from bson import ObjectId
            session_id = text.replace("STUDENT_CANCEL_", "")
            db.counseling_sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"status": "Cancelled", "cancelled_by": "student"}}
            )
            return "*Session successfully cancelled.*", "START", data, None, None
        elif text == "STUDENT_MY_SESSIONS":
            return "*Loading sessions...*", "STUDENT_MENU", {"button_click": "STUDENT_MY_SESSIONS"}, [{"id": "STUDENT_MY_SESSIONS", "title": "View Again"}], None

    elif state == "STUDENT_REG_NAME":
        data["name"] = text
        wa_id = data.get("wa_id")
        db.users.update_one({"wa_id": wa_id}, {"$set": {"name": text, "role": "Student"}}, upsert=True)
        return f"Nice to meet you, {text}! 🎓\nHow can I support you today?", "STUDENT_MENU", data, [
            {"id": "STUDENT_SUPPORT", "title": "Support Chat"},
            {"id": "STUDENT_BOOK", "title": "Book Session"},
            {"id": "STUDENT_MY_SESSIONS", "title": "My Sessions"}
        ], None

    elif state == "BOOKING_DATE":
        data["booking_date"] = text
        return "Got it! 🗓️ What *time* would you prefer? (e.g., 2:00 PM)", "BOOKING_TIME", data, None, None

    elif state == "BOOKING_TIME":
        data["booking_time"] = text
        return "Understood. 🧠 Briefly describe your *concern* or what you'd like to talk about:", "BOOKING_DESC", data, None, None

    elif state == "BOOKING_DESC":
        from datetime import datetime
        new_session = {
            "student_wa_id": wa_id,
            "date": data["booking_date"],
            "time": data["booking_time"],
            "description": text,
            "status": "Pending",
            "created_at": datetime.utcnow()
        }
        db.counseling_sessions.insert_one(new_session)
        # Notify Doctors (Optional but good)
        return ("✅ *Booking Request Sent!* 🚀\n\nA doctor will review your request soon. You'll be notified once it's approved."), "STUDENT_MENU", data, [
            {"id": "STUDENT_SUPPORT", "title": "Support Chat"},
            {"id": "STUDENT_BOOK", "title": "Book Another"},
            {"id": "STUDENT_MY_SESSIONS", "title": "My Sessions"}
        ], None

    elif state == "DR_REG_NAME":
        db.users.update_one({"wa_id": wa_id}, {"$set": {"name": text, "role": "Doctor", "status": "Active"}}, upsert=True)
        return f"Welcome, Dr. {text}! 🩺\nYour dashboard is ready.", "START", data, None, None

    elif state == "ROLE_SELECTION":
        if text == "ROLE_STUDENT":
            return "Welcome! What's your name?", "STUDENT_REG_NAME", {"role": "Student"}, None, None
        elif text == "ROLE_DOCTOR":
            return "Mindly - Doctor Registration 🩺\n\nWhat is your full name?", "DR_REG_NAME", {"role": "Doctor"}, None, None
        elif text == "ROLE_OTHER":
            return "Thank you! Please tell us how we can help you specifically.", "OTHER_FLOW", {"role": "Other"}, None, None

    elif state == "OTHER_FLOW":
        return "Thank you for sharing. We will get back to you soon.", "START", {}, None, None

    # --- Catch All ---
    return "Hello! Type 'START' to welcome Mindly.", "START", {}, None, None

def send_whatsapp_list_message(recipient_id, text, list_data):
    """
    Sends a native WhatsApp List Message (Selection Menu).
    """
    url = f"https://graph.facebook.com/v18.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    formatted_sections = []
    for section in list_data["sections"]:
        formatted_rows = []
        for row in section["rows"]:
            formatted_rows.append({
                "id": row["id"],
                "title": row["title"],
                "description": row.get("description", "")
            })
        formatted_sections.append({
            "title": section["title"],
            "rows": formatted_rows
        })
        
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": text},
            "footer": {"text": "Mindly - Mental Health Support"},
            "action": {
                "button": list_data["button"],
                "sections": formatted_sections
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error sending WhatsApp list message: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.text}")
        return None

def send_whatsapp_button_message(recipient_id, text, buttons):
    """
    Sends a message with native WhatsApp buttons (Quick Replies).
    Maximum 3 buttons allowed for Quick Replies.
    """
    url = f"https://graph.facebook.com/v18.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    formatted_buttons = []
    for btn in buttons[:3]: # Meta limit is 3 buttons for quick_reply
        formatted_buttons.append({
            "type": "reply",
            "reply": {
                "id": btn["id"],
                "title": btn["title"]
            }
        })
        
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {"buttons": formatted_buttons}
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error sending WhatsApp button message: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.text}")
        return None

def send_whatsapp_message(recipient_id, message_text):
    """
    Sends a message via the WhatsApp Cloud API.
    """
    url = f"https://graph.facebook.com/v18.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": message_text}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.text}")
        return None
