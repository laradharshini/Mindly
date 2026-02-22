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
                # Real-time count of pending sessions
                pending_count = db.counseling_sessions.count_documents({"status": "Pending"})
                response = (f"Welcome back, Dr. {user['name']}! 🩺\n\n"
                            f"Your dashboard:\n"
                            f"• Pending Sessions: {pending_count}\n"
                            f"• Status: Active")
                
                buttons = []
                if pending_count > 0:
                    buttons.append({"id": "DR_VIEW_REQS", "title": "View Requests"})
                
                return response, "DOCTOR_DASHBOARD", {"role": "Doctor", "name": user["name"]}, buttons
            else:
                response = f"Welcome back to Mindly, {user['name']}! 🎓\nHow can I support you today?"
                buttons = [
                    {"id": "STUDENT_SUPPORT", "title": "Support Chat"},
                    {"id": "STUDENT_BOOK", "title": "Book Session"}
                ]
                return response, "STUDENT_MENU", {"role": "Student", "name": user["name"]}, buttons
        
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
        return response, "ROLE_SELECTION", {}, buttons

    # --- DOCTOR DASHBOARD & NAVIGATION ---
    elif state == "DOCTOR_DASHBOARD":
        if text == "DR_VIEW_REQS":
            # State: List pending requests
            pending_list = list(db.counseling_sessions.find({"status": "Pending"}).limit(3))
            if not pending_list:
                return "No pending requests at the moment. 🎉", "DOCTOR_DASHBOARD", data, None
            
            response = "Mindly - Pending Requests 🗓️\n\n"
            buttons = []
            for i, sess in enumerate(pending_list):
                student = db.users.find_one({"wa_id": sess["student_wa_id"]})
                name = student.get("name", "Unknown") if student else "Unknown"
                response += f"{i+1}️⃣ {name}\n📅 {sess['date']} @ {sess['time']}\n\n"
                buttons.append({"id": f"DR_MANAGE_{i}", "title": f"Manage #{i+1}"})
            
            buttons.append({"id": "DR_DASHBOARD", "title": "Dashboard"})
            
            # Store the current list IDs in session data for selection
            data["current_list_ids"] = [str(s["_id"]) for s in pending_list]
            return response, "DOCTOR_LIST_REQS", data, buttons
        
        elif text == "DR_DASHBOARD":
            return "Refreshing dashboard...", "START", data, None

    elif state == "DOCTOR_LIST_REQS":
        if text.startswith("DR_MANAGE_"):
            index = int(text.replace("DR_MANAGE_", ""))
            list_ids = data.get("current_list_ids", [])
            
            if index < len(list_ids):
                from bson import ObjectId
                session_id = list_ids[index]
                sess = db.counseling_sessions.find_one({"_id": ObjectId(session_id)})
                if sess:
                    student = db.users.find_one({"wa_id": sess["student_wa_id"]})
                    name = student.get("name", "Unknown") if student else "Unknown"
                    
                    response = (f"Managing Request for {name} 👤\n\n"
                                f"📅 Date: {sess['date']}\n"
                                f"🕒 Time: {sess['time']}\n"
                                f"💬 Concern: {sess['description']}\n\n"
                                "What would you like to do?")
                    
                    data["active_session_id"] = session_id
                    buttons = [
                        {"id": f"DR_APPROVE_{session_id}", "title": "Approve ✅"},
                        {"id": f"DR_DECLINE_{session_id}", "title": "Decline ❌"},
                        {"id": "DR_VIEW_REQS", "title": "Back to List ⬅️"}
                    ]
                    return response, "DOCTOR_MANAGE_REQ", data, buttons
            
            return "Request not found. Please try again.", "DOCTOR_LIST_REQS", data, None

        elif text == "DR_VIEW_REQS":
            # Re-trigger list logic
            return "Loading list...", "DOCTOR_DASHBOARD", data, None
        
        elif text == "DR_DASHBOARD":
            return "Returning to dashboard...", "START", data, None

    elif state == "DOCTOR_MANAGE_REQ":
        if text.startswith("DR_APPROVE_"):
            from bson import ObjectId
            session_id = text.replace("DR_APPROVE_", "")
            session_doc = db.counseling_sessions.find_one({"_id": ObjectId(session_id)})
            
            if session_doc:
                db.counseling_sessions.update_one(
                    {"_id": ObjectId(session_id)},
                    {"$set": {"status": "Approved", "approved_by": wa_id}}
                )
                # Notify Student
                notif_msg = (f"Your counselling session for {session_doc['date']} "
                             f"at {session_doc['time']} has been APPROVED. 🩺")
                send_whatsapp_message(session_doc["student_wa_id"], notif_msg)
                
                return "Session approved and student notified! ✅", "DOCTOR_DASHBOARD", data, [{"id": "DR_VIEW_REQS", "title": "View More"}]
            
        elif text.startswith("DR_DECLINE_"):
            from bson import ObjectId
            session_id = text.replace("DR_DECLINE_", "")
            session_doc = db.counseling_sessions.find_one({"_id": ObjectId(session_id)})
            
            if session_doc:
                db.counseling_sessions.update_one(
                    {"_id": ObjectId(session_id)},
                    {"$set": {"status": "Declined", "declined_by": wa_id}}
                )
                # Notify Student
                notif_msg = (f"We're sorry, your counselling session for {session_doc['date']} "
                             f"could not be approved at this time. 😔")
                send_whatsapp_message(session_doc["student_wa_id"], notif_msg)
                
                return "Session declined and student notified. ❌", "DOCTOR_DASHBOARD", data, [{"id": "DR_VIEW_REQS", "title": "View More"}]
        
        elif text == "DR_VIEW_REQS":
            # Go back to list
            return "Returning to list...", "DOCTOR_DASHBOARD", data, None

    elif state == "ROLE_SELECTION":
        if text == "ROLE_STUDENT":
            response = "Welcome! What's your name?"
            return response, "STUDENT_REG_NAME", {"role": "Student"}, None
        elif text == "ROLE_DOCTOR":
            return "Mindly - Doctor Registration 🩺\n\nWhat is your full name?", "DR_REG_NAME", {"role": "Doctor"}, None
        elif text == "ROLE_OTHER":
            return "Thank you! Please tell us how we can help you specifically.", "OTHER_FLOW", {"role": "Other"}, None

    # --- STUDENT REGISTRATION (Simplified for persistence) ---
    elif state == "STUDENT_REG_NAME":
        data["name"] = text
        # Auto-register student
        db.users.insert_one({
            "wa_id": wa_id,
            "name": text,
            "role": "student",
            "created_at": datetime.datetime.utcnow()
        })
        response = f"Nice to meet you, {text}! 🎓\nHow can I help you today?"
        buttons = [
            {"id": "STUDENT_SUPPORT", "title": "Support Chat"},
            {"id": "STUDENT_BOOK", "title": "Book Session"}
        ]
        return response, "STUDENT_MENU", data, buttons

    # --- DOCTOR REGISTRATION FLOW ---
    elif state == "DR_REG_NAME":
        data["name"] = text
        return "What is your qualification? (e.g., MD, PhD)", "DR_REG_QUAL", data, None
    elif state == "DR_REG_QUAL":
        data["qualification"] = text
        return "What is your medical license number?", "DR_REG_LICENSE", data, None
    elif state == "DR_REG_LICENSE":
        data["license"] = text
        return "What are your working days? (e.g., Mon-Fri)", "DR_REG_DAYS", data, None
    elif state == "DR_REG_DAYS":
        data["working_days"] = text
        return "What are your available time slots? (e.g., 9 AM - 5 PM)", "DR_REG_SLOTS", data, None
    elif state == "DR_REG_SLOTS":
        data["slots"] = text
        summary = (f"Confirm your registration details:\n"
                   f"• Name: {data['name']}\n"
                   f"• Qual: {data['qualification']}\n"
                   f"• License: {data['license']}\n"
                   f"• Days: {data['working_days']}\n"
                   f"• Slots: {data['slots']}\n\n"
                   "Is this correct?")
        buttons = [
            {"id": "DR_CONFIRM_YES", "title": "YES, Correct"},
            {"id": "DR_CONFIRM_NO", "title": "NO, Restart"}
        ]
        return summary, "DR_REG_CONFIRM", data, buttons
    
    elif state == "DR_REG_CONFIRM":
        if text == "DR_CONFIRM_YES":
            db.users.insert_one({
                "wa_id": wa_id,
                "name": data["name"],
                "role": "doctor",
                "qualification": data["qualification"],
                "license": data["license"],
                "working_days": data["working_days"],
                "available_slots": data["slots"],
                "status": "pending",
                "created_at": datetime.datetime.utcnow()
            })
            return ("Thank you! Your registration will be reviewed and approved before activation. "
                    "You will be notified once you are live."), "START", {}, None
        else:
            return "Let's start over. What is your full name?", "DR_REG_NAME", {"role": "Doctor"}, None

    # --- STUDENT FLOW ---
    elif state == "STUDENT_MENU":
        if text == "STUDENT_SUPPORT":
            return ("You are now in Emotional Support Mode. 💙\n"
                    "Tell me what's on your mind. (Type 'MENU' anytime to exit)"), "EMOTIONAL_SUPPORT", data, None
        elif text == "STUDENT_BOOK":
            return "Mindly - Session Booking 🗓️\n\nWhat is your preferred date? (e.g., 2024-05-20)", "BOOKING_DATE", data, None

    elif state == "EMOTIONAL_SUPPORT":
        if text.upper() == "MENU":
            response = "Back to Student Menu. What would you like to do?"
            buttons = [
                {"id": "STUDENT_SUPPORT", "title": "Support Chat"},
                {"id": "STUDENT_BOOK", "title": "Book Session"}
            ]
            return response, "STUDENT_MENU", data, buttons
        
        risk_level = classify_risk(text)
        ai_response = generate_mindly_response(text, risk_level)
        return ai_response, "EMOTIONAL_SUPPORT", data, None

    elif state == "BOOKING_DATE":
        data["booking_date"] = text
        return "What time slot would you prefer? (e.g., 2:00 PM)", "BOOKING_TIME", data, None
    elif state == "BOOKING_TIME":
        data["booking_time"] = text
        return "Please give a short description of your concern.", "BOOKING_CONCERN", data, None
    elif state == "BOOKING_CONCERN":
        data["concern"] = text
        summary = (f"Confirm Booking Request:\n"
                   f"• Date: {data['booking_date']}\n"
                   f"• Time: {data['booking_time']}\n"
                   f"• Concern: {data['concern']}")
        buttons = [{"id": "BOOK_CONFIRM_YES", "title": "Confirm Booking"}]
        return summary, "BOOKING_CONFIRM", data, buttons
    
    elif state == "BOOKING_CONFIRM":
        if text == "BOOK_CONFIRM_YES":
            # Save booking to DB
            db.counseling_sessions.insert_one({
                "student_wa_id": wa_id,
                "date": data["booking_date"],
                "time": data["booking_time"],
                "description": data["concern"],
                "status": "Pending",
                "created_at": datetime.datetime.utcnow()
            })
            return ("Your request has been sent to an available counsellor. "
                    "We will confirm shortly and send a video session link once approved. 💙"), "START", {}, None
        else:
            return "Booking cancelled. Back to Student Menu.", "STUDENT_MENU", data, None

    return "Hello! Type 'START' to welcome Mindly.", "START", {}, None

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
