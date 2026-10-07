🛡️ 7-Layer API Security Middleware

📌 Giới thiệu (Overview)

Đây là một hệ thống Middleware bảo mật chuyên sâu dành cho các Web API, được xây dựng bằng Python/Flask. Dự án này áp dụng mô hình phòng thủ nhiều lớp (Defense in Depth), hoạt động ở Tầng ứng dụng (Layer 7) nhằm bảo vệ máy chủ khỏi các cuộc tấn công phổ biến, spam lưu lượng và khai thác lỗ hổng.

🚀 Các tính năng bảo mật cốt lõi (The 7 Defense Layers)

Hệ thống xử lý mọi Request đi vào thông qua một phễu lọc gồm 7 lớp:

1. Firewall (IP & Bot Protection):

Lọc và chặn ngay lập tức các IP nằm trong Blacklist.

Nhận diện và chặn các công cụ rà quét tự động (Bots/Scanners) thông qua User-Agent (ví dụ: sqlmap, nmap, curl).

Tích hợp trích xuất IP thật (True Client IP) đằng sau các hệ thống Reverse Proxy như Cloudflare hoặc AWS API Gateway (X-Forwarded-For).

2. CORS Management (Cross-Origin Resource Sharing):

Kiểm soát nghiêm ngặt các nguồn (Origins) được phép gọi API.

Xử lý mượt mà các OPTIONS Preflight requests để tương thích với trình duyệt.

3. Anti-CSRF (Cross-Site Request Forgery):

Xác thực nguồn gốc của các requests có tính chất thay đổi dữ liệu (POST, PUT, DELETE) thông qua headers Origin và Referer.

4. WAF: SQL & NoSQL Injection Scanner:

Quét toàn bộ URL Parameters và JSON Body.

Sử dụng Regex để đánh chặn sớm các payload chứa từ khóa SQL nguy hiểm (UNION SELECT, DROP) hoặc toán tử NoSQL ($gt, $ne).

5. WAF: XSS Filter (Cross-Site Scripting):

Lọc và chặn các requests cố tình chèn thẻ <script>, các sự kiện JS (onerror, onload) trước khi chúng kịp đi vào Database.

6. Rate Limiting (Fixed Window Counter):

Ngăn chặn tấn công Brute-force và HTTP Flood (Application DDoS).

Ưu tiên nhận diện người dùng qua x-api-key. Nếu không có, tự động chuyển sang giới hạn theo IP thật.

Trả về mã lỗi chuẩn 429 Too Many Requests kèm thời gian chờ (retry_after_seconds).

7. Security Headers (Lớp giáp đầu ra):

Tự động đính kèm các headers bảo vệ trình duyệt người dùng ở mọi responses (như X-Content-Type-Options: nosniff, X-Frame-Options: DENY).

🛠️ Công nghệ sử dụng (Tech Stack)

Ngôn ngữ: Python 3.x

Framework: Flask

Thư viện: Flask-CORS, re (Regular Expressions), time

⚙️ Hướng dẫn chạy thử (Installation & Usage)

1. Clone kho lưu trữ này về máy:

git clone https://github.com/Dmeo2051612/Tool-b-o-m-t-API.git


2. Cài đặt các thư viện cần thiết:

pip install Flask Flask-Cors


3. Khởi chạy máy chủ:

python app.py


4. Hệ thống sẽ lắng nghe ở cổng 5000. Bạn có thể dùng Postman hoặc trình duyệt để gọi vào http://127.0.0.1:5000/api/data và test thử các chức năng chặn mã độc, rate limit.

💡 Hướng phát triển tương lai (Future Roadmap)

[ ] Tích hợp Caching (Redis) để thay thế cho Dictionary trong RAM, giúp scale hệ thống ra nhiều server.

[ ] Tích hợp API kiểm tra IP ảo (VPN/Proxy/Tor Detection).

[ ] Xây dựng Dashboard để theo dõi lưu lượng và cảnh báo tấn công theo thời gian thực.