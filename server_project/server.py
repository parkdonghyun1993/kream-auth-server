from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__, template_folder='templates')
CORS(app)

# 한국 시간 (KST) 설정
kst = pytz.timezone("Asia/Seoul")

# MongoDB 연결
MONGO_URI = os.environ.get("MONGO_URI") or "your_mongo_uri_here"
client = MongoClient(MONGO_URI)
db = client["kream_auth"]
users_collection = db["users"]

@app.route('/')
def index():
    return 'Server is running'

# ✅ 사용자 회원가입
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if users_collection.find_one({'username': username}):
        return jsonify({'message': 'Username already exists'}), 400

    now = datetime.now(kst)
    users_collection.insert_one({
        'username': username,
        'password': password,
        'created_at': now.strftime("%Y-%m-%d %H:%M:%S"),
        'approved': False,
        'access_start': None,
        'access_expire': None,
        'extended_days': 0
    })
    return jsonify({'message': 'Signup request submitted'}), 200

# ✅ 사용자 로그인
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = users_collection.find_one({'username': username, 'password': password})
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401
    if not user.get('approved'):
        return jsonify({'message': 'Not approved yet'}), 403

    now = datetime.now(kst)
    expire_str = user.get('access_expire')
    expire_time = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S") if expire_str else None

    if expire_time and now > expire_time:
        return jsonify({'message': 'Access expired'}), 403

    return jsonify({'message': 'Login successful'}), 200

# ✅ 관리자 페이지
@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# ✅ 관리자용 유저 목록 조회 (미승인 또는 승인된 전체)
@app.route('/admin/users')
def admin_users():
    users = list(users_collection.find())
    for user in users:
        user['_id'] = str(user['_id'])
    return jsonify(users)

# ✅ 관리자 승인
@app.route('/admin/approve/<username>', methods=['POST'])
def approve_user(username):
    now = datetime.now(kst)
    days = 30  # 기본 승인 기간
    expire_date = now + timedelta(days=days)

    result = users_collection.update_one(
        {'username': username},
        {'$set': {
            'approved': True,
            'access_start': now.strftime("%Y-%m-%d %H:%M:%S"),
            'access_expire': expire_date.strftime("%Y-%m-%d %H:%M:%S"),
            'granted_days': days
        }}
    )
    if result.modified_count:
        return jsonify({'message': f'{username} approved'}), 200
    return jsonify({'message': 'No user updated'}), 400

# ✅ 관리자 거절 및 삭제
@app.route('/admin/reject/<username>', methods=['POST'])
def reject_user(username):
    result = users_collection.delete_one({'username': username})
    if result.deleted_count:
        return jsonify({'message': f'{username} rejected and deleted'}), 200
    return jsonify({'message': 'No user deleted'}), 400

# ✅ 관리자 기간 연장
@app.route('/admin/extend/<username>', methods=['POST'])
def extend_user(username):
    data = request.json
    days = data.get('days', 0)
    if days < 1 or days > 90:
        return jsonify({'message': 'Invalid extension period'}), 400

    user = users_collection.find_one({'username': username})
    if not user or not user.get('access_expire'):
        return jsonify({'message': 'User not found or not yet approved'}), 404

    current_expire = datetime.strptime(user['access_expire'], "%Y-%m-%d %H:%M:%S")
    new_expire = current_expire + timedelta(days=days)

    users_collection.update_one(
        {'username': username},
        {'$set': {
            'access_expire': new_expire.strftime("%Y-%m-%d %H:%M:%S")
        }, '$inc': {
            'extended_days': days
        }}
    )
    return jsonify({'message': f'{username} extended by {days} days'}), 200

# 서버 실행용 (개발용으로만 사용)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
