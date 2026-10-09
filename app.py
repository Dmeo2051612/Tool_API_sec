import os
import hashlib
import ipaddress
from urllib.parse import urlsplit

import redis
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config["DEBUG"] = False

TRUSTED_X_FOR_COUNT = max(0, int(os.getenv("TRUSTED_X_FOR_COUNT", "0")))
TRUSTED_X_PROTO_COUNT = max(0, int(os.getenv("TRUSTED_X_PROTO_COUNT", "0")))

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=TRUSTED_X_FOR_COUNT,
    x_proto=TRUSTED_X_PROTO_COUNT
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
    health_check_interval=30,
    max_connections=50
)

MAX_REQUESTS = max(1, int(os.getenv("MAX_REQUESTS", "5")))
TIME_WINDOW = max(1, int(os.getenv("TIME_WINDOW", "10")))

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
STATE_CHANGING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def normalize_origin(value, allow_path=False):
    try:
        parsed = urlsplit(value.strip())

        scheme = parsed.scheme.lower()

        if scheme not in {"http", "https"}:
            return None

        if not parsed.hostname:
            return None

        if parsed.username is not None or parsed.password is not None:
            return None

        if not allow_path and (
            parsed.path or parsed.query or parsed.fragment
        ):
            return None

        hostname = parsed.hostname.lower()
        port = parsed.port

        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"

        if (scheme == "http" and port == 80) or (
            scheme == "https" and port == 443
        ):
            port = None

        authority = hostname if port is None else f"{hostname}:{port}"

        return f"{scheme}://{authority}"

    except (ValueError, AttributeError):
        return None


ALLOWED_ORIGINS = {
    origin
    for origin in (
        normalize_origin(item.strip())
        for item in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:8080"
        ).split(",")
        if item.strip()
    )
    if origin
}

if not ALLOWED_ORIGINS:
    raise RuntimeError("ALLOWED_ORIGINS chưa được cấu hình hợp lệ.")

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": list(ALLOWED_ORIGINS),
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    }
)

RATE_LIMIT_SCRIPT = redis_client.register_script(
    """
    local current = redis.call('INCR', KEYS[1])
    local ttl = redis.call('TTL', KEYS[1])

    if ttl == -1 then
        redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
        ttl = tonumber(ARGV[1])
    end

    return {current, ttl}
    """
)


def get_client_ip():
    remote_addr = request.remote_addr

    if not remote_addr:
        return None

    try:
        return ipaddress.ip_address(remote_addr).compressed
    except ValueError:
        return None


def is_valid_request_origin():
    origin = request.headers.get("Origin")

    if origin is not None:
        normalized_origin = normalize_origin(origin)
    else:
        referer = request.headers.get("Referer")

        if not referer:
            return False

        normalized_origin = normalize_origin(
            referer,
            allow_path=True
        )

    return (
        normalized_origin is not None
        and normalized_origin in ALLOWED_ORIGINS
    )


def apply_rate_limit(client_ip):
    ip_hash = hashlib.sha256(
        client_ip.encode("utf-8")
    ).hexdigest()

    redis_key = f"rate_limit:ip:{ip_hash}"

    result = RATE_LIMIT_SCRIPT(
        keys=[redis_key],
        args=[TIME_WINDOW]
    )

    current_count = int(result[0])
    ttl = int(result[1])

    if current_count > MAX_REQUESTS:
        retry_after = max(ttl, 1)

        response = jsonify({
            "error": "Too many requests.",
            "retry_after_seconds": retry_after
        })

        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)

        return response

    return None


@app.before_request
def security_middleware():
    client_ip = get_client_ip()

    if client_ip is None:
        return jsonify({
            "error": "Không xác định được địa chỉ client."
        }), 400

    try:
        if redis_client.sismember("blacklist_ips", client_ip):
            return jsonify({
                "error": "Truy cập bị từ chối."
            }), 403

        rate_limit_response = apply_rate_limit(client_ip)

        if rate_limit_response is not None:
            return rate_limit_response

    except redis.RedisError as exc:
        app.logger.error(
            "Redis request failed: %s",
            type(exc).__name__
        )

        return jsonify({
            "error": "Dịch vụ bảo vệ hiện không khả dụng."
        }), 503

    if (
        request.method in STATE_CHANGING_METHODS
        and not is_valid_request_origin()
    ):
        return jsonify({
            "error": "Nguồn gốc request không hợp lệ."
        }), 403

    return None


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none';"
    )

    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    response.headers["Cache-Control"] = "no-store"

    if request.is_secure:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000"
        )

    return response


@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify({
        "message": "Lấy dữ liệu thành công! Request hợp lệ."
    }), 200


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
        use_reloader=False
    )