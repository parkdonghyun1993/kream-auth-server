from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import bcrypt
import jwt
import datetime

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your_secret_key'

# 메모리 사용자 DB (예제용)
users = []

# 회원가입
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if any(user['username'] == username for user in users):
        return jsonify({"error": "이미 존재하는 사용자입니다."}), 400

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users.append({
        "username": username,
        "password": hashed_pw,
        "is_approved": False
    })
    return jsonify({"message": "회원가입 성공! 승인 대기 중입니다."}), 200

# 로그인
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    for user in users:
        if user["username"] == username and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            if not user.get("is_approved", False):
                return jsonify({"error": "관리자 승인 대기 중입니다."}), 403
            token = jwt.encode({
                "username": username,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
            }, app.config["SECRET_KEY"], algorithm="HS256")
            return jsonify({"token": token}), 200
    return jsonify({"error": "로그인 실패"}), 401

# 관리자 페이지
@app.route('/admin', methods=['GET'])
def admin():
    return render_template('admin.html', users=users)

# 관리자 사용자 승인
@app.route('/approve/<username>', methods=['POST'])
def approve(username):
    for user in users:
        if user["username"] == username:
            user["is_approved"] = True
            return jsonify({"message": "승인 완료"}), 200
    return jsonify({"error": "사용자 없음"}), 404

# 관리자 사용자 삭제
@app.route('/delete/<username>', methods=['POST'])
def delete(username):
    global users
    users = [user for user in users if user["username"] != username]
    return jsonify({"message": "삭제 완료"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
