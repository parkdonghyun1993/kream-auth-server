from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
import bcrypt
import pytz

app = Flask(__name__)
CORS(app)

# MongoDB 연결
client = MongoClient(os.environ.get("MONGODB_URI"))
db = client["kream_auth"]
users_collection = db["users"]

# KST 시간대
KST = pytz.timezone("Asia/Seoul")

# 기본 페이지
@app.route("/")
def index():
    return "Server is running"

# 관리자 페이지
@app.route("/admin")
def admin_page():
    return render_template("admin.html")

# 전체 유저 조회 (승인 여부와 무관)
@app.route("/admin/users", methods=["GET"])
def get_all_users():
    users = list(users_collection.find({}, {"_id": 0, "password": 0}))
    return jsonify(users)

# 회원가입
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    if users_collection.find_one({"username": username}):
        return jsonify({"message": "이미 존재하는 사용자입니다."}), 409

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    now = datetime.now(KST)

    user = {
        "username": username,
        "password": hashed_pw,
        "approved": False,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "approved_at": None,
        "access_start": None,
        "access_expire": None
    }

    users_collection.insert_one(user)
    return jsonify({"message": "회원가입 신청이 완료되었습니다."}), 201

# 로그인
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    user = users_collection.find_one({"username": username})
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"message": "아이디 또는 비밀번호가 틀렸습니다."}), 401

    if not user.get("approved"):
        return jsonify({"message": "관리자 승인이 필요합니다.", "access_granted": False}), 403

    now = datetime.now(KST)
    expire_str = user.get("access_expire")
    if expire_str:
        expire_time = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
        if now > expire_time:
            return jsonify({"message": "사용 기간이 만료되었습니다.", "access_granted": False}), 403

    return jsonify({"message": "로그인 성공", "access_granted": True}), 200

# 승인
@app.route("/admin/approve/<username>", methods=["POST"])
def approve_user(username):
    data = request.get_json()
    days = data.get("days", 30)
    now = datetime.now(KST)
    expire = now + timedelta(days=days)

    result = users_collection.update_one(
        {"username": username},
        {"$set": {
            "approved": True,
            "approved_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "access_start": now.strftime("%Y-%m-%d %H:%M:%S"),
            "access_expire": expire.strftime("%Y-%m-%d %H:%M:%S")
        }}
    )
    if result.modified_count:
        return jsonify({"message": f"{username} 승인됨"}), 200
    return jsonify({"message": "업데이트 실패"}), 400

# 거절
@app.route("/admin/reject/<username>", methods=["POST"])
def reject_user(username):
    result = users_collection.delete_one({"username": username})
    if result.deleted_count:
        return jsonify({"message": f"{username} 삭제됨"}), 200
    return jsonify({"message": "삭제 실패"}), 400

# 기간 연장
@app.route("/admin/extend/<username>", methods=["POST"])
def extend_period(username):
    data = request.get_json()
    days = data.get("days", 0)

    user = users_collection.find_one({"username": username})
    if not user:
        return jsonify({"message": "사용자를 찾을 수 없습니다."}), 404

    expire_str = user.get("access_expire")
    now = datetime.now(KST)

    if expire_str:
        base = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
        new_expire = base + timedelta(days=days)
    else:
        new_expire = now + timedelta(days=days)

    users_collection.update_one(
        {"username": username},
        {"$set": {
            "access_expire": new_expire.strftime("%Y-%m-%d %H:%M:%S")
        }}
    )
    return jsonify({"message": f"{username}의 사용 기간이 연장되었습니다."}), 200

# 사용 기간 수동 지정
@app.route("/admin/set_period/<username>", methods=["POST"])
def set_period(username):
    data = request.get_json()
    start = data.get("start")
    expire = data.get("expire")

    users_collection.update_one(
        {"username": username},
        {"$set": {
            "access_start": start,
            "access_expire": expire
        }}
    )
    return jsonify({"message": "사용 기간이 설정되었습니다."})

# 비밀번호 변경
@app.route("/admin/change_password/<username>", methods=["POST"])
def change_password(username):
    data = request.get_json()
    new_password = data.get("password")

    hashed_pw = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

    users_collection.update_one(
        {"username": username},
        {"$set": {"password": hashed_pw}}
    )
    return jsonify({"message": f"{username}의 비밀번호가 변경되었습니다."})

if __name__ == "__main__":
    app.run(debug=True, port=10000)
