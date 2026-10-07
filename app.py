from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import re

app = Flask(__name__)

rate_limit_storage = {}

MAX_REQUESTS = 5
TIME_WINDOW = 10


ALLOWED_ORIGINS = ["http://localhost:8080"]


CORS(app, resources={
    r"/api/*" : {
        "origins" : ALLOWED_ORIGINS,
        "methods" : ["GET", "POST", "OPTIONS"],
        "allow_headers" : ["Content-Type", "x-api-key"]
    }
})


SQLI_PATTERN = re.compile(r"(?i)(\b(SELECT|UPDATE|DELETE|INSERT|DROP|ALTER|UNION)\b)")
NOSQLI_PATTERN = re.compile(r"(?i)(\$gt|\$lt|\$ne|\$where|\$regex)")


XSS_PATTERN = re.compile(r"(?i)(<script[^>]*>|javascript:|on\w+\s*=)")


BLACKLIST_IPS = set()
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

    #firewall
    if client_ip in BLACKLIST_IPS:
        return jsonify({"error": "Truy cập bị từ chối bởi Tường lửa (IP Banned)."}), 403

    user_agent = request.headers.get('User-Agent', '').lower()
    for bad_bot in BAD_USER_AGENTS:
        if bad_bot in user_agent:
            return jsonify({"error": "Phát hiện công cụ truy cập không hợp lệ."}), 403

    #CSRF
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')

        if origin and origin not in ALLOWED_ORIGINS:
            return jsonify({"error": "Lỗi CSRF: Nguồn gốc request không hợp lệ."}), 403

        if referer and not any (referer.startswith(allowed) for allowed in ALLOWED_ORIGINS):
            return jsonify({"error": "Lỗi CSRF: Nguồn gốc request không hợp lệ."}), 403

    def contains_malicious_payload(text):
        if SQLI_PATTERN.search(text) or NOSQLI_PATTERN.search(text):
            return "Injection"
        if XSS_PATTERN.search(text):
            return "XSS"
        return None

    # Quét tham số trên URL
    for key, value in request.args.items():
        threat = contains_malicious_payload(value)
        if threat:
            return jsonify({"error": "Phát hiện mã độc Injection trong URL"}), 403

    # Quét dữ liệu trong Body
    if request.is_json:
        body_str = request.get_data(as_text=True)
        threat = contains_malicious_payload(body_str)
        if threat:
            return jsonify({"error": "Phát hiện mã độc Injection trong Body!"}), 403

    api_key = request.headers.get('x-api-key')
    client_id = api_key if api_key else client_ip #địa chỉ ip của client gửi request
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

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'

    response.headers['X-Frame-Options'] = 'DENY'
    return response

@app.route('/api/data', methods = ['GET'])
def get_data():
    return jsonify({"message" : "Lấy dữ liệu thành công! Request hợp lệ."}), 200


if __name__ == '__main__':
    app.run(debug=True)
