from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import re

app = Flask(__name__)

rate_limit_storage = {}

MAX_REQUESTS = 5
TIME_WINDOW = 10


CORS(app, resources={
    r"/api/*" : {
        "origins" : "http://localhost:8080",
        "methods" : ["GET", "POST", "OPTIONS"],
        "allow_headers" : ["Content-Type", "x-api-key"]
    }
})


SQLI_PATTERN = re.compile(r"(?i)(\b(SELECT|UPDATE|DELETE|INSERT|DROP|ALTER|UNION)\b)")
NOSQLI_PATTERN = re.compile(r"(?i)(\$gt|\$lt|\$ne|\$where|\$regex)")


BLACKLIST_IPS = {}
BAD_USER_AGENTS = ["sqlmap", "nmap", "zgrab", "nikto", "curl", "python-requests"]

def get_real_ip():
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr

@app.before_request
def check_rate_limit():
    if request.method == 'OPTIONS':
        return None

    client_ip = get_real_ip()

    if client_ip in BLACKLIST_IPS:
        return jsonify({"error": "Truy cập bị từ chối bởi Tường lửa (IP Banned)."})

    user_agent = request.headers.get('User-Agent', '').lower()
    for bad_bot in BAD_USER_AGENTS:
        if bad_bot in user_agent:
            return jsonify({"error": "Phát hiện công cụ truy cập không hợp lệ."}), 403
    
    for key, value in request.args.items():
        if SQLI_PATTERN.search(value) or NOSQLI_PATTERN.search(value):
            return jsonify({"error": "Phát hiện mã độc Injection trong URL"}), 403

    if request.is_json:
        body_str = request.get_data(as_text=True)
        if SQLI_PATTERN.search(body_str) or NOSQLI_PATTERN.search(body_str):
            return jsonify({"error": "Phát hiện mã độc Injection trong Body!"}), 403

    api_key = request.headers.get('x-api-key')
    client_id = api_key if api_key else request.remote_addr #địa chỉ ip của client gửi request
    #ý nghĩa dòng trên là Ưu tiên nhận diện người dùng bằng API Key. Nếu không có API Key thì nhận diện bằng IP


    current_time = time.time()
    #trường hợp nếu user mới tạo request đầu
    if client_id not in rate_limit_storage:
        rate_limit_storage[client_id] = {"count": 1, "start_time": current_time}
        return None     #Cho phép request đi tiếp


    user_record = rate_limit_storage[client_id]
    time_passed = current_time - user_record["start_time"]


    if time_passed > TIME_WINDOW:
        user_record["count"] = 1
        user_record["start_time"] = current_time
    else:
        user_record["count"] += 1
        if user_record["count"] > MAX_REQUESTS:
            return jsonify({
                "error": "Too many request. Máy chủ đang bận",
                "Vui lòng thử lại sau" : round(TIME_WINDOW - time_passed, 1)
            }), 429

    return None




@app.route('/api/data', methods = ['GET'])
def get_data():
    return jsonify({"message" : "Lấy dữ liệu thành công! Request hợp lệ."}), 200


if __name__ == '__main__':
    app.run(debug=True)
