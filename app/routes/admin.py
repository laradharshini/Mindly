from flask import Blueprint, jsonify
from app.database import get_db

from app.routes.auth import token_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/stats', methods=['GET'])
@token_required
def get_stats(current_user):
    # For now, allow all logged in users to see stats for demo, or uncomment below for strict:
    # if current_user.get('role') != 'admin':
    #     return jsonify({'message': 'Admin access required'}), 403
    db = get_db()
    total_users = db.users.count_documents({'role': 'student'})
    
    pipeline = [
        {"$group": {"_id": "$stress_level", "count": {"$sum": 1}}}
    ]
    stress_counts = list(db.assessments.aggregate(pipeline))
    stress_dist = {item["_id"]: item["count"] for item in stress_counts}
    
    pending_sessions = db.counseling_sessions.count_documents({'status': 'Pending'})
    
    return jsonify({
        "total_users": total_users,
        "stress_distribution": stress_dist,
        "pending_counseling": pending_sessions
    })
