import google.generativeai as genai
import requests
import json
from app.config import Config

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

def handle_conversational_flow(wa_id, message_text, session):
    """
    Main state machine for Mindly WhatsApp conversations.
    Returns: (response_text, next_state, updated_data)
    """
    state = session.get("state", "START")
    data = session.get("data", {})
    text = message_text.strip()
    
    # Global Reset Command
    if text.upper() in ["RESET", "START", "HI", "HELLO"]:
        state = "START"
        data = {}

    if state == "START":
        response = ("Welcome to Mindly 💙\n"
                    "Please select your role:\n"
                    "1️⃣ Student\n"
                    "2️⃣ Doctor\n"
                    "3️⃣ Other")
        return response, "ROLE_SELECTION", {}

    elif state == "ROLE_SELECTION":
        if text == "1":
            response = ("Mindly - Student Menu 🎓\n"
                        "Please select an option:\n"
                        "1️⃣ Emotional Support Chat\n"
                        "2️⃣ Book Counselling Session")
            return response, "STUDENT_MENU", {"role": "Student"}
        elif text == "2":
            return "Mindly - Doctor Registration 🩺\n\nWhat is your full name?", "DR_REG_NAME", {"role": "Doctor"}
        elif text == "3":
            return "Thank you for reaching out. Please tell us how we can help you specifically.", "OTHER_FLOW", {"role": "Other"}
        else:
            return "Invalid selection. Please choose 1, 2, or 3.", "ROLE_SELECTION", data

    # --- DOCTOR REGISTRATION FLOW ---
    elif state == "DR_REG_NAME":
        data["name"] = text
        return "What is your qualification? (e.g., MD, PhD)", "DR_REG_QUAL", data
    elif state == "DR_REG_QUAL":
        data["qualification"] = text
        return "What is your medical license number?", "DR_REG_LICENSE", data
    elif state == "DR_REG_LICENSE":
        data["license"] = text
        return "What are your working days? (e.g., Mon-Fri)", "DR_REG_DAYS", data
    elif state == "DR_REG_DAYS":
        data["working_days"] = text
        return "What are your available time slots? (e.g., 9 AM - 5 PM)", "DR_REG_SLOTS", data
    elif state == "DR_REG_SLOTS":
        data["slots"] = text
        summary = (f"Confirm your registration details:\n"
                   f"• Name: {data['name']}\n"
                   f"• Qual: {data['qualification']}\n"
                   f"• License: {data['license']}\n"
                   f"• Days: {data['working_days']}\n"
                   f"• Slots: {data['slots']}\n\n"
                   "Is this correct? Reply YES to submit or NO to restart.")
        return summary, "DR_REG_CONFIRM", data
    elif state == "DR_REG_CONFIRM":
        if text.upper() == "YES":
            return ("Thank you! Your registration will be reviewed and approved before activation. "
                    "You will be notified once you are live."), "START", {}
        else:
            return "Let's start over. What is your full name?", "DR_REG_NAME", {"role": "Doctor"}

    # --- STUDENT FLOW ---
    elif state == "STUDENT_MENU":
        if text == "1":
            return ("You are now in Emotional Support Mode. 💙\n"
                    "Tell me what's on your mind. (Type 'MENU' anytime to exit)"), "EMOTIONAL_SUPPORT", data
        elif text == "2":
            return "Mindly - Session Booking 🗓️\n\nWhat is your preferred date? (e.g., 2024-05-20)", "BOOKING_DATE", data
        else:
            return "Invalid selection. Choose 1 for Support or 2 for Booking.", "STUDENT_MENU", data

    elif state == "EMOTIONAL_SUPPORT":
        if text.upper() == "MENU":
            return "Back to Student Menu:\n1️⃣ Support Chat\n2️⃣ Book Session", "STUDENT_MENU", data
        
        # Integrate Gemini Logic
        risk_level = classify_risk(text)
        ai_response = generate_mindly_response(text, risk_level)
        return ai_response, "EMOTIONAL_SUPPORT", data

    elif state == "BOOKING_DATE":
        data["booking_date"] = text
        return "What time slot would you prefer? (e.g., 2:00 PM)", "BOOKING_TIME", data
    elif state == "BOOKING_TIME":
        data["booking_time"] = text
        return "Please give a short description of your concern.", "BOOKING_CONCERN", data
    elif state == "BOOKING_CONCERN":
        data["concern"] = text
        summary = (f"Confirm Booking Request:\n"
                   f"• Date: {data['booking_date']}\n"
                   f"• Time: {data['booking_time']}\n"
                   f"• Concern: {data['concern']}\n\n"
                   "Reply YES to send to a counsellor.")
        return summary, "BOOKING_CONFIRM", data
    elif state == "BOOKING_CONFIRM":
        if text.upper() == "YES":
            # Assume success for now
            return ("Your request has been sent to an available counsellor. "
                    "We will confirm shortly and send a video session link once approved. 💙"), "START", {}
        else:
            return "Booking cancelled. Back to Student Menu.", "STUDENT_MENU", data

    return "Hello! Type 'START' to welcome Mindly.", "START", {}

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
