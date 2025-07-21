from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
import bcrypt
import jwt
import os

app = Flask(__name__)
CORS(app)

# 회원 데이터 저장용 (메모리 또는 DB 대체 가능)
users = []

# 예시 유저 구조: {"username": "abc", "password": "hashed", "is_approved": False}

# 관리자 페이지
@app.route("/admin")
def admin_page():
    return render_template("admin.html", users=users)

# 회원가입
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data["username"]
    password = data["password"]

    if any(u["username"] == username for u in users):
        return jsonify({"message": "이미 존재하는 사용자입니다."}), 400

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users.append({"username": username, "password": hashed_pw, "is_approved": False})
    return jsonify({"message": "회원가입 완료. 관리자 승인 대기 중"}), 201

# 로그인
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    user = next((u for u in users if u["username"] == username), None)
    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"message": "로그인 실패"}), 401

    if not user["is_approved"]:
        return jsonify({"message": "승인 대기중"}), 403

    token = jwt.encode({"username": username}, "SECRET", algorithm="HS256")
    return jsonify({"message": "로그인 성공", "token": token})

# 관리자 승인
@app.route("/approve_user", methods=["POST"])
def approve_user():
    username = request.form["username"]
    for user in users:
        if user["username"] == username:
            user["is_approved"] = True
            break
    return redirect("/admin")

# 관리자 삭제
@app.route("/delete_user", methods=["POST"])
def delete_user():
    username = request.form["username"]
    global users
    users = [u for u in users if u["username"] != username]
    return redirect("/admin")

# 기본 루트
@app.route("/")
def home():
    return "✅ KREAM Auth Server is Running"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
