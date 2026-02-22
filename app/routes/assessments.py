from flask import Blueprint, request, jsonify
from app.database import get_db
from app.config import Config
import jwt
from functools import wraps
import datetime

assessments_bp = Blueprint('assessments', __name__)

from app.routes.auth import token_required

def calculate_stress_level(phq, gad, ghq):
    total_score = phq + gad + ghq
    average = total_score / 3
    if average < 5:
        return "Mild", average
    elif average < 10:
        return "Moderate", average
    else:
        return "Severe", average

@assessments_bp.route('/', methods=['POST'])
@token_required
def submit_assessment(current_user):
    data = request.get_json()
    db = get_db()
    
    phq = data.get('phq_score', 0)
    # ... (rest of logic uses current_user_id? wait I should check)
    gad = data.get('gad_score', 0)
    ghq = data.get('ghq_score', 0)
    
    stress_level, average = calculate_stress_level(phq, gad, ghq)
    
    assessment = {
        'user_id': str(current_user['_id']),
        'phq_score': phq,
        'gad_score': gad,
        'ghq_score': ghq,
        'assessment_average': average,
        'stress_level': stress_level,
        'created_at': datetime.datetime.utcnow()
    }
    
    result = db.assessments.insert_one(assessment)
    assessment['_id'] = str(result.inserted_id)
    
    return jsonify(assessment), 201

@assessments_bp.route('/history', methods=['GET'])
@token_required
def get_history(current_user):
    db = get_db()
    assessments = list(db.assessments.find({'user_id': str(current_user['_id'])}))
    for a in assessments:
        a['_id'] = str(a['_id'])
    return jsonify(assessments), 200
