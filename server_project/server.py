from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
import bcrypt
import jwt
import datetime
import os

app = Flask(__name__)
CORS(app)

# JWT 시크릿 키
SECRET_KEY = "your_secret_key"

# ✅ MongoDB 연결 설정
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGODB_URI)
db = client["kream-auth"]
users_collection = db["users"]

# 서버동작
@app.route('/')
def home():
    return "Server is running!"

# 회원가입
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    if users_collection.find_one({"username": username}):
        return jsonify({"message": "이미 존재하는 사용자입니다."}), 400

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    users_collection.insert_one({
        "username": username,
        "password": hashed_pw,
        "approved": False
    })
    return jsonify({"message": "회원가입 완료. 관리자 승인 후 이용 가능합니다."})

# 로그인
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    user = users_collection.find_one({"username": username})
    if not user:
        return jsonify({"message": "사용자를 찾을 수 없습니다."}), 404
    if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"message": "비밀번호가 일치하지 않습니다."}), 401
    if not user.get("approved", False):
        return jsonify({"message": "관리자 승인이 필요합니다."}), 403

    token = jwt.encode({
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, SECRET_KEY, algorithm="HS256")
    return jsonify({"token": token})

# 관리자 콘솔 로그
@app.route('/admin')
def admin_page():
    print("admin route hit")  # 콘솔 로그 찍히는지 확인용
    return render_template("admin.html")

# ✅ 관리자 페이지 라우팅 추가
@app.route("/admin")
def admin_page():
    users = list(users_collection.find())
    return render_template("admin.html", users=users)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
