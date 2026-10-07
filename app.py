from flask import Flask, request, jsonify
from flask_cors import CORS
import time

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

@app.before_request
def check_rate_limit():
    if request.method == 'OPTIONS':
        return None

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
