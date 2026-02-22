from flask import Blueprint, request, jsonify
from app.extensions import mongo
from app.routes.auth import token_required
from datetime import datetime
from bson import ObjectId

wellness_bp = Blueprint('wellness', __name__)

@wellness_bp.route('/mood', methods=['POST'])
@token_required
def log_mood(current_user):
    data = request.get_json()
    mood = data.get('mood')
    
    if not mood:
        return jsonify({"message": "Mood is required"}), 400
        
    mood_log = {
        "user_id": current_user['_id'],
        "mood": mood,
        "timestamp": datetime.utcnow()
    }
    
    mongo.db.mood_logs.insert_one(mood_log)
    return jsonify({"message": "Mood logged successfully"}), 201

@wellness_bp.route('/journal', methods=['POST'])
@token_required
def create_journal_entry(current_user):
    data = request.get_json()
    title = data.get('title', 'Untitled Reflection')
    content = data.get('content')
    
    if not content:
        return jsonify({"message": "Journal content is required"}), 400
        
    entry = {
        "user_id": current_user['_id'],
        "title": title,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    
    mongo.db.journal_entries.insert_one(entry)
    return jsonify({"message": "Journal entry saved"}), 201

@wellness_bp.route('/journal', methods=['GET'])
@token_required
def get_journal_entries(current_user):
    entries = list(mongo.db.journal_entries.find({"user_id": current_user['_id']}).sort("timestamp", -1))
    
    for entry in entries:
        entry['_id'] = str(entry['_id'])
        entry['user_id'] = str(entry['user_id'])
        
    return jsonify(entries), 200
