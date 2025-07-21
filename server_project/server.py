import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

client = None
users_collection = None

# MongoDB 초기화 (fork-safe)
def init_db():
    global client, users_collection
    if client is None:
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("환경변수 MONGODB_URI가 설정되지 않았습니다.")
        client = MongoClient(mongodb_uri)
        db = client['kream_auth']
        users_collection = db['users']

@app.route('/')
def index():
    return "Server is running"

@app.route('/register', methods=['POST'])
def register():
    init_db()
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if users_collection.find_one({"username": username}):
        return jsonify({"success": False, "message": "이미 존재하는 사용자입니다."}), 400

    hashed_pw = generate_password_hash(password)
    users_collection.insert_one({"username": username, "password": hashed_pw})
    return jsonify({"success": True, "message": "회원가입 성공"})

@app.route('/login', methods=['POST'])
def login():
    init_db()
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = users_collection.find_one({"username": username})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"success": False, "message": "로그인 실패"}), 401

    return jsonify({"success": True, "message": "로그인 성공"})

@app.route('/admin')
def admin():
    init_db()
    users = list(users_collection.find({}, {"_id": 0}))
    return render_template("admin.html", users=users)
    except Exception as e:
        return f"DB 연결 실패: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
