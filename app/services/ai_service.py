import google.generativeai as genai
from app.config import Config

genai.configure(api_key=Config.GEMINI_API_KEY)

# Safety settings
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(model_name="gemini-pro", safety_settings=safety_settings)

def generate_response(user_message):
    system_prompt = """
    You are Mindly, an AI mental health support assistant for a university student.
    Your goal is to provide empathetic, non-judgmental, and practical support.
    
    Guidelines:
    - Listen actively and validate feelings.
    - Ask open-ended questions.
    - Suggest healthy coping mechanisms.
    - Detect crisis keywords (suicide, self-harm) and suggest professional help immediately.
    - Do NOT diagnose.
    
    User says: 
    """
    try:
        response = model.generate_content(system_prompt + user_message)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "I'm having trouble connecting right now, but I'm here for you."
