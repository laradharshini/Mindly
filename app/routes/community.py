from flask import Blueprint, request, jsonify
from app.database import get_db
from app.routes.auth import token_required

community_bp = Blueprint('community', __name__)

@community_bp.route('/', methods=['POST'])
@token_required
def create_post(current_user):
    data = request.get_json()
    db = get_db()
    users = db.users
    
    post = {
        'user_id': str(current_user['_id']),
        'user_name': 'Anonymous' if data.get('anonymous') else current_user.get('name', 'Student'),
        'content': data.get('content'),
        'flagged': False,
        'created_at': datetime.datetime.utcnow(),
        'comments': []
    }
    
    result = db.posts.insert_one(post)
    post['_id'] = str(result.inserted_id)
    
    return jsonify(post), 201

@community_bp.route('/', methods=['GET'])
def get_posts():
    db = get_db()
    posts = list(db.posts.find().sort('created_at', -1))
    for p in posts:
        p['_id'] = str(p['_id'])
    return jsonify(posts), 200
