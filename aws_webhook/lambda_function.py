import json
import os
import hmac
import hashlib
import logging
from base64 import b64decode

logger = logging.getLogger()
logger.setLevel(logging.INFO)

APP_SECRET = os.environ.get("APP_SECRET", "").strip()

def _verify_signature(signature_block: dict) -> bool:
    try:
        ts = str(signature_block.get("timestamp", ""))
        token = signature_block.get("token", "")
        sig = signature_block.get("signature", "")
        if not (APP_SECRET and ts and token and sig):
            return False
        expected = hmac.new(
            APP_SECRET.encode("utf-8"),
            (ts + token).encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception as e:
        logger.error(f"signature verify error: {e}")
        return False

def _ok(body=None, status=200):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body or {"status": "ok"})
    }

def _bad(msg, status=401):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "error", "message": msg})
    }

def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "")
    body = event.get("body", "")
    is_base64 = event.get("isBase64Encoded", False)

    if method != "POST":
        return _ok({"status": "alive"})  # simple health check for GET

    try:
        raw = b64decode(body) if is_base64 else body.encode("utf-8")
        payload = json.loads(raw.decode("utf-8"))
    except Exception as e:
        logger.error(f"bad json: {e}")
        return _bad("invalid json", 400)

    # Log the incoming payload in cloudwatch logs
    logger.info("Incoming Data: %s", json.dumps(payload, ensure_ascii=False))

    # verify signature
    sig_block = payload.get("signature", {})
    if not _verify_signature(sig_block):
        logger.warning("Signature verification failed")
        return _bad("unauthorized", 401)

    # extract data array if present (same structure you saw locally)
    data = payload.get("payload", {}).get("data", [])
    if data:
        logger.info("Parsed sensor data: %s", json.dumps(data))

    # TODO: persist to DB/S3/etc. Here we just acknowledge.
    return _ok({"status": "ok"})