from flask import Blueprint, request, jsonify
from app.services.ai_service import generate_response
from app.routes.assessments import token_required

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user_id):
    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'message': 'Message is required'}), 400
        
    response = generate_response(user_message)
    return jsonify({'response': response})
