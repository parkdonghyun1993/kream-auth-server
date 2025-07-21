from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import sqlite3
import bcrypt
import jwt
import os

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv("JWT_SECRET", "mysecret")

DB_FILE = "users.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_user_table():
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            expiry TEXT
        )
        """)
create_user_table()

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data["username"]
    password = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()

    try:
        with get_db() as db:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        return jsonify({"status": "success", "message": "회원가입 완료"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "fail", "message": "이미 존재하는 사용자"}), 400

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            return jsonify({"status": "fail", "message": "사용자 없음"}), 404
        if not bcrypt.checkpw(password.encode(), user["password"].encode()):
            return jsonify({"status": "fail", "message": "비밀번호 불일치"}), 401

        if not user["expiry"]:
            return jsonify({"status": "fail", "message": "관리자 승인 대기중"}), 403

        if datetime.today() > datetime.strptime(user["expiry"], "%Y-%m-%d"):
            return jsonify({"status": "fail", "message": "사용기간 만료"}), 403

        token = jwt.encode({"username": username}, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({"status": "success", "token": token}), 200

@app.route("/admin/set_expiry", methods=["POST"])
def set_expiry():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        if payload["username"] != "admin":
            return jsonify({"status": "fail", "message": "권한 없음"}), 403

        data = request.json
        with get_db() as db:
            db.execute("UPDATE users SET expiry = ? WHERE username = ?", (data["expiry"], data["username"]))
        return jsonify({"status": "success", "message": "기간 설정 완료"}), 200
    except Exception:
        return jsonify({"status": "fail", "message": "인증 실패"}), 403

@app.route("/me", methods=["GET"])
def me():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        return jsonify({"status": "success", "username": payload["username"]})
    except:
        return jsonify({"status": "fail", "message": "토큰 인증 실패"}), 401

# ✅ 여기에서 외부 접속을 허용하는 host 설정 포함
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
