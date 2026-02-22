from flask import Blueprint, request, jsonify
from app.database import get_db
from app.config import Config
import bcrypt
import jwt
import datetime

from functools import wraps
from app.extensions import mongo

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if " " in auth_header:
                token = auth_header.split(" ")[1]
            else:
                token = auth_header
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            from bson import ObjectId
            data = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            db = get_db()
            current_user = db.users.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                 return jsonify({'message': 'User not found!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    db = get_db()
    users = db.users

    if users.find_one({'email': data['email']}):
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    
    new_user = {
        'name': data['name'],
        'email': data['email'],
        'password': hashed_password,
        'role': 'student',
        'created_at': datetime.datetime.utcnow()
    }
    
    users.insert_one(new_user)
    
    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    db = get_db()
    users = db.users
    
    # Check if login uses 'username' (OAuth2 form) or 'email' (JSON body)
    email = data.get('email') or data.get('username')
    password = data.get('password')

    user = users.find_one({'email': email})

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        token = jwt.encode({
            'user_id': str(user['_id']),
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, Config.JWT_SECRET, algorithm="HS256")

        return jsonify({'access_token': token, 'token_type': 'bearer'})

    return jsonify({'message': 'Invalid credentials'}), 401
