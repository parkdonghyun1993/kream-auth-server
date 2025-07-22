from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import pytz
import os

app = Flask(__name__)
client = MongoClient(os.environ.get("MONGODB_URI"))
db = client["kream_auth"]
users_collection = db["users"]

KST = pytz.timezone('Asia/Seoul')

@app.route('/')
def index():
    return "Server is running"

if __name__ == '__main__':
    app.run()
    
@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/admin/users')
def get_pending_users():
    users = list(users_collection.find({"approved": {"$ne": True}}, {"_id": 0, "username": 1, "created_at": 1, "access_expire": 1, "approved": 1}))
    for user in users:
        if user.get("created_at"):
            user["created_at"] = user["created_at"].astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")
        if user.get("access_expire"):
            user["access_expire"] = user["access_expire"].astimezone(KST).strftime("%Y-%m-%d")
    return jsonify(users)

@app.route('/admin/approve/<username>', methods=['POST'])
def approve_user(username):
    data = request.get_json()
    days = int(data.get("days", 30))
    now = datetime.now(KST)
    expire = now + timedelta(days=days)
    result = users_collection.update_one(
        {"username": username},
        {"$set": {
            "approved": True,
            "access_start": now,
            "access_expire": expire,
            "granted_days": days
        }}
    )
    if result.modified_count:
        return jsonify({"message": f"{username} 승인 완료"}), 200
    return jsonify({"message": "유저 승인 실패"}), 400

@app.route('/admin/reject/<username>', methods=['POST'])
def reject_user(username):
    result = users_collection.delete_one({"username": username})
    if result.deleted_count:
        return jsonify({"message": f"{username} 거절 및 삭제됨"}), 200
    return jsonify({"message": "유저 삭제 실패"}), 400

@app.route('/admin/extend/<username>', methods=['POST'])
def extend_user(username):
    data = request.get_json()
    days = int(data.get("days", 0))
    now = datetime.now(KST)
    user = users_collection.find_one({"username": username})
    if not user or not user.get("access_expire"):
        return jsonify({"message": "사용자를 찾을 수 없음"}), 404
    new_expire = user["access_expire"] + timedelta(days=days)
    users_collection.update_one(
        {"username": username},
        {"$set": {
            "access_expire": new_expire,
            "extended_days": days
        }}
    )
    return jsonify({"message": f"{username} 사용 기간 {days}일 연장됨"}), 200
