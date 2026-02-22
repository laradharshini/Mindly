from flask import Blueprint, request, jsonify
from app.config import Config
from app.services.whatsapp_service import classify_risk, generate_mindly_response, send_whatsapp_message

whatsapp_bp = Blueprint('whatsapp', __name__)

@whatsapp_bp.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Webhook verification for Meta WhatsApp Cloud API.
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == Config.WHATSAPP_VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            return "Verification failed", 403
    return "Verification failed", 400

@whatsapp_bp.route('/webhook', methods=['POST'])
def handle_message():
    """
    Handles incoming messages from WhatsApp.
    """
    data = request.get_json()
    print(f"Incoming WhatsApp data: {data}")

    try:
        # Check if it's a message event
        if data.get('object') == 'whatsapp_business_account':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    
                    if messages:
                        message = messages[0]
                        sender_id = message.get('from') # User's WhatsApp ID
                        
                        if message.get('type') == 'text':
                            user_text = message.get('text', {}).get('body')
                            
                            # 1. Classify Risk
                            risk_level = classify_risk(user_text)
                            print(f"Risk Level for {sender_id}: {risk_level}")
                            
                            # 2. Generate Mindly Response
                            # Note: n8n workflow had a condition: if risk is CRITICAL, 
                            # it sends the response. If not CRITICAL, it also sends the response.
                            # The logic in the JSON shows both paths lead to "Send message".
                            # One path (CRITICAL) goes directly to send message, 
                            # the other (ELSE) goes to AI Agent then send message.
                            # Actually, it looks like Mindly response is generated for both, 
                            # but the risk level is passed to it.
                            
                            ai_response = generate_mindly_response(user_text, risk_level)
                            
                            # 3. Send Message back to user
                            send_whatsapp_message(sender_id, ai_response)
                            
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "not a whatsapp event"}), 404

    except Exception as e:
        print(f"Error handling WhatsApp webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
