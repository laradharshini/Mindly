from flask import Blueprint, request, jsonify
from app.database import get_db
from app.routes.auth import token_required

counseling_bp = Blueprint('counseling', __name__)

@counseling_bp.route('/', methods=['POST'])
@token_required
def book_session(current_user):
    data = request.get_json()
    db = get_db()
    
    session = {
        'student_id': str(current_user['_id']),
        'counselor_name': 'Assigned Counselor',
        'date': data.get('date'),
        'status': 'Pending',
        'created_at': datetime.datetime.utcnow()
    }
    
    result = db.counseling_sessions.insert_one(session)
    session['_id'] = str(result.inserted_id)
    
    return jsonify(session), 201

@counseling_bp.route('/', methods=['GET'])
@token_required
def get_sessions(current_user):
    db = get_db()
    sessions = list(db.counseling_sessions.find({'student_id': str(current_user['_id'])}))
    for s in sessions:
        s['_id'] = str(s['_id'])
    return jsonify(sessions), 200
