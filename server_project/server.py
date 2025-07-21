from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
import jwt
import datetime
import os

app = Flask(__name__, template_folder='templates')
CORS(app)

# JWT 비밀키 설정
SECRET_KEY = 'secret-key'

# MongoDB 설정
MONGODB_URI = os.environ.get('MONGODB_URI', 'your_mongodb_uri')  # 실제 배포 시 환경변수 사용 권장
client = MongoClient(MONGODB_URI)
db = client['kream_auth']
users_collection = db['users']

@app.route('/')
def index():
    return "Server is running"

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if users_collection.find_one({'username': username}):
        return jsonify({'message': 'Username already exists'}), 409

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users_collection.insert_one({
        'username': username,
        'password': hashed_pw,
        'approved': False
    })
    return jsonify({'message': 'User registered. Awaiting admin approval.'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = users_collection.find_one({'username': username})
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if not user.get('approved', False):
        return jsonify({'message': 'User not approved by admin'}), 403

    if bcrypt.checkpw(password.encode('utf-8'), user['password']):
        token = jwt.encode({
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        }, SECRET_KEY, algorithm='HS256')
        return jsonify({'token': token})
    else:
        return jsonify({'message': 'Incorrect password'}), 401

@app.route('/admin', methods=['GET'])
def admin_panel():
    users = list(users_collection.find())
    return render_template('admin.html', users=users)

@app.route('/admin/approve/<username>', methods=['POST'])
def approve_user(username):
    result = users_collection.update_one({'username': username}, {'$set': {'approved': True}})
    if result.modified_count:
        return jsonify({'message': f'{username} approved'}), 200
    return jsonify({'message': 'No user updated'}), 400

@app.route('/admin/reject/<username>', methods=['POST'])
def reject_user(username):
    result = users_collection.delete_one({'username': username})
    if result.deleted_count:
        return jsonify({'message': f'{username} rejected and deleted'}), 200
    return jsonify({'message': 'No user deleted'}), 400

if __name__ == '__main__':
    app.run(debug=True)
