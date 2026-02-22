from flask import Blueprint, request, jsonify
from app.config import Config
from app.services.whatsapp_service import handle_conversational_flow, send_whatsapp_message, send_whatsapp_button_message, send_whatsapp_list_message
from app.services.session_service import get_user_session, update_user_session

whatsapp_bp = Blueprint('whatsapp', __name__)

@whatsapp_bp.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Webhook verification for Meta WhatsApp Cloud API.
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # If this is a manual browser visit (no mode), return a success message
    if not mode:
        return "Webhook active and listening.", 200

    if mode == 'subscribe' and token == Config.WHATSAPP_VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        return challenge, 200
    else:
        return "Verification failed", 403

@whatsapp_bp.route('/webhook', methods=['POST'])
def handle_message():
    """
    Handles incoming messages (text, buttons, and lists) from WhatsApp.
    """
    data = request.get_json()
    
    try:
        if data.get('object') == 'whatsapp_business_account':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    
                    if messages:
                        message = messages[0]
                        sender_id = message.get('from')
                        user_text = ""
                        is_button = False
                        
                        # Handle Text Messages
                        if message.get('type') == 'text':
                            user_text = message.get('text', {}).get('body')
                        
                        # Handle Button Replies
                        elif message.get('type') == 'interactive':
                            interactive = message.get('interactive', {})
                            if interactive.get('type') == 'button_reply':
                                user_text = interactive.get('button_reply', {}).get('id')
                                is_button = True
                            # Handle List Replies
                            elif interactive.get('type') == 'list_reply':
                                user_text = interactive.get('list_reply', {}).get('id')
                                is_button = True # Treat list selection as a button/id interaction
                        
                        if user_text:
                            # 1. Get current session
                            session = get_user_session(sender_id)
                            
                            # 2. Process conversation flow
                            response_text, next_state, updated_data, buttons, list_data = handle_conversational_flow(
                                sender_id, user_text, session, is_button=is_button
                            )
                            
                            # 3. Update session in DB
                            update_user_session(sender_id, state=next_state, data=updated_data)
                            
                            # 4. Send response (List, Button or Text)
                            if list_data:
                                send_whatsapp_list_message(sender_id, response_text, list_data)
                            elif buttons:
                                send_whatsapp_button_message(sender_id, response_text, buttons)
                            else:
                                send_whatsapp_message(sender_id, response_text)
                            
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "not a whatsapp event"}), 404

    except Exception as e:
        print(f"Error handling WhatsApp webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
