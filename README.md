# Flask Security Middleware

Project học tập về middleware bảo mật cho API sử dụng Flask, Redis và Werkzeug. Mục tiêu là thực hành các lớp kiểm soát request cơ bản và hiểu giới hạn của chúng.

## Chức năng hiện có

- **ProxyFix:** đọc thông tin IP và giao thức từ header proxy khi được cấu hình số proxy tin cậy chính xác.
- **Rate Limiting:** giới hạn mặc định 5 request trong 10 giây theo IP client; bộ đếm được lưu trong Redis.
- **Atomic counter và TTL:** Lua script gom thao tác tăng bộ đếm và thiết lập TTL trong Redis.
- **IP Blacklist:** từ chối IP có trong Redis Set `blacklist_ips`.
- **CORS:** chỉ cho phép origin được cấu hình truy cập tài nguyên `/api/*`.
- **Kiểm tra Origin/Referer:** từ chối request thay đổi trạng thái nếu nguồn gốc không hợp lệ hoặc bị thiếu.
- **Security Headers:** thêm các header như `X-Content-Type-Options`, `X-Frame-Options`, CSP, `Referrer-Policy`, `Permissions-Policy` và `Cache-Control`; HSTS chỉ được thêm khi request được nhận diện là HTTPS.

## Công nghệ

- Python 3.10 trở lên
- Flask 3.1.3
- Flask-Cors 6.0.5
- Redis server
- redis-py 8.1.0
- Werkzeug 3.1.9

## Cấu trúc tối thiểu

```text
project/
├── app.py
├── requirements.txt
└── README.md
```

Lưu mã Flask hiện tại vào `app.py`. Nếu file có tên khác, thay `app.py` trong các lệnh chạy bên dưới bằng tên module tương ứng.

## Cài đặt trên Windows

### 1. Tạo môi trường Python

Mở PowerShell tại thư mục project:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu PowerShell không cho phép kích hoạt môi trường ảo, có thể gọi trực tiếp `\.venv\Scripts\python.exe` thay vì thay đổi chính sách thực thi toàn máy.

### 2. Khởi động Redis

Nếu đã cài Redis, hãy đảm bảo Redis đang chạy tại `localhost:6379`.

Hoặc sử dụng Docker Desktop:

```powershell
docker run --name flask-security-redis -p 127.0.0.1:6379:6379 -d redis:8
docker exec flask-security-redis redis-cli ping
```

Kết quả kiểm tra mong đợi là `PONG`. Nếu container đã tồn tại, dùng `docker start flask-security-redis` thay vì tạo lại.

### 3. Cấu hình môi trường

Chạy trong cùng cửa sổ PowerShell sẽ khởi động ứng dụng:

```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
$env:ALLOWED_ORIGINS = "http://localhost:8080"
$env:MAX_REQUESTS = "5"
$env:TIME_WINDOW = "10"
$env:TRUSTED_X_FOR_COUNT = "0"
$env:TRUSTED_X_PROTO_COUNT = "0"
$env:PORT = "5000"
```

`ALLOWED_ORIGINS` nhận danh sách origin phân tách bằng dấu phẩy, ví dụ `http://localhost:8080,https://example.com`. Chỉ khai báo những origin bạn thực sự tin cậy.

Ở môi trường local không có reverse proxy, giữ `TRUSTED_X_FOR_COUNT=0` và `TRUSTED_X_PROTO_COUNT=0`. Chỉ đặt giá trị lớn hơn 0 khi ứng dụng nằm sau proxy đáng tin cậy đã được cấu hình để ghi đè/chuẩn hóa các header chuyển tiếp. Không mở cổng ứng dụng trực tiếp ra Internet khi đang tin header do proxy chuyển tiếp.

Không đưa mật khẩu Redis hoặc thông tin bí mật vào Git. Nếu Redis có mật khẩu, hãy đặt thông tin kết nối trong biến `REDIS_URL` của môi trường triển khai.

### 4. Chạy ứng dụng

```powershell
python app.py
```

Ứng dụng chạy tại `http://127.0.0.1:5000` theo cấu hình mặc định.

## API mẫu

### `GET /api/data`

```powershell
curl.exe -i http://127.0.0.1:5000/api/data
```

Request thành công trả về JSON tương tự:

```json
{
  "message": "Lấy dữ liệu thành công! Request hợp lệ."
}
```

### Kiểm tra Rate Limiting

Mặc định, mỗi IP được phép 5 request trong một cửa sổ 10 giây. Gửi 6 request liên tiếp:

```powershell
1..6 | ForEach-Object {
    curl.exe -s -o NUL -w "%{http_code}`n" http://127.0.0.1:5000/api/data
}
```

Sau khi vượt giới hạn, request sẽ nhận HTTP `429`. Chờ TTL hết hạn rồi thử lại.

### Thêm hoặc gỡ IP khỏi blacklist

Thêm IP vào blacklist:

```powershell
docker exec flask-security-redis redis-cli SADD blacklist_ips 127.0.0.1
```

Gỡ IP khỏi blacklist:

```powershell
docker exec flask-security-redis redis-cli SREM blacklist_ips 127.0.0.1
```

Các lệnh trên áp dụng khi dùng container Redis có tên `flask-security-redis`. Nếu đang chạy Redis theo cách khác, dùng công cụ Redis tương ứng. Blacklist hiện lưu địa chỉ IP gốc, không phải giá trị hash.

## Hành vi khi Redis không khả dụng

Middleware hiện dùng chính sách **Fail-Closed**: nếu lệnh Redis phát sinh lỗi, request nhận HTTP `503 Service Unavailable`. Code hiện tại chưa có Circuit Breaker, bản sao Redis, hoặc cơ chế fallback trong RAM.

## Giới hạn và phạm vi sử dụng

Đây là middleware mẫu phục vụ học tập và kiểm thử, **chưa phải API Gateway hoàn chỉnh và chưa đủ điều kiện tự thân để triển khai làm lớp bảo vệ cho ứng dụng tài chính**.

- Ứng dụng chỉ có endpoint minh họa `GET /api/data`; chưa chuyển tiếp request đến backend khác.
- Chưa triển khai Authentication/Authorization, JWT, quản lý user ID hay giới hạn request theo danh tính người dùng. Rate Limit hiện chỉ dựa trên IP.
- SHA-256 được dùng để tạo key Rate Limit, nhưng điều đó không tự động bảo đảm tuân thủ GDPR hoặc làm dữ liệu IP hoàn toàn ẩn danh. Blacklist vẫn chứa IP dạng rõ.
- WAF bên ngoài như Cloudflare hoặc ModSecurity chưa được cấu hình trong project này.
- Kiểm tra Origin/Referer không thay thế Authentication, Authorization hoặc toàn bộ biện pháp CSRF cần thiết cho một ứng dụng có phiên đăng nhập.
- Redis vẫn là thành phần phụ thuộc tập trung; khi Redis lỗi, request bị từ chối với HTTP 503.
- Rate Limiting theo IP không đủ để ngăn mọi loại DoS/DDoS và không thay thế kiểm soát tài nguyên ở tầng hạ tầng.
- `python app.py` dùng server phát triển của Flask; không dùng cách chạy này cho production. Khi triển khai, cần WSGI server phù hợp, HTTPS, cấu hình proxy chính xác, giám sát, quản lý secret và kiểm thử bảo mật.

Với ứng dụng quản lý chi tiêu, nên đặt nghiệp vụ giao dịch, phân quyền và tính nhất quán dữ liệu trong backend chính (ví dụ Spring Boot + SQL Server). Chỉ bổ sung Flask làm gateway nếu có yêu cầu định tuyến và vận hành rõ ràng.
