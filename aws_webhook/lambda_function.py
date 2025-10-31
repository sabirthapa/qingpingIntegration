import json
import uuid
import os
import hmac
import hashlib
import logging
import requests
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Qingping
APP_SECRET = os.environ.get("APP_SECRET", "").strip()

# Tuya
ACCESS_ID = os.environ.get("TUYA_ACCESS_ID", "").strip()
ACCESS_SECRET = os.environ.get("TUYA_ACCESS_SECRET", "").strip()
DEVICE_ID = os.environ.get("TUYA_DEVICE_ID", "").strip()
BASE_URL = "https://openapi.tuyaus.com"

# signature verification
def _verify_signature(signature_block: dict) -> bool:
    try:
        ts = str(signature_block.get("timestamp", ""))
        token = signature_block.get("token", "")
        sig = signature_block.get("signature", "")
        if not (APP_SECRET and ts and token and sig):
            return False
        expected = hmac.new(APP_SECRET.encode("utf-8"),
                            (ts + token).encode("utf-8"),
                            hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception as e:
        logger.error(f"signature verify error: {e}")
        return False

def get_tuya_token():
    # generate timestamp and nonce
    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())

    # build stringToSign
    content_sha256 = hashlib.sha256(b"").hexdigest()
    string_to_sign = "GET\n" + content_sha256 + "\n\n" + "/v1.0/token?grant_type=1"

    # build full string to hash
    message = ACCESS_ID + t + nonce + string_to_sign

    # cmpute HMAC-SHA256 and uppercase
    sign = hmac.new(
        ACCESS_SECRET.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest().upper()

    headers = {
        "client_id": ACCESS_ID,
        "sign": sign,
        "t": t,
        "nonce": nonce,
        "sign_method": "HMAC-SHA256",
        "Signature-Headers": "",
        "lang": "en",
        "dev_lang": "python"
    }

    url = f"{BASE_URL}/v1.0/token?grant_type=1"
    r = requests.get(url, headers=headers)
    logger.info(f"Raw token response: {r.text}")

    try:
        resp = r.json()
    except Exception:
        raise Exception(f"Non-JSON response: {r.text}")

    if not resp.get("success"):
        raise Exception(f"Tuya auth failed: {json.dumps(resp)}")

    return resp["result"]["access_token"]

# tuya control
def control_plug(state: bool):
    token = get_tuya_token()
    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())

    # prepare the body
    data = {"commands": [{"code": "switch_1", "value": state}]}
    body_str = json.dumps(data, separators=(",", ":"))

    # compute SHA256 of body
    content_sha256 = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

    # build stringToSign according to Tuya spec
    string_to_sign = "POST\n" + content_sha256 + "\n\n" + f"/v1.0/devices/{DEVICE_ID}/commands"

    # build message to sign
    message = ACCESS_ID + token + t + nonce + string_to_sign

    # compute final signature
    sign = hmac.new(
        ACCESS_SECRET.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest().upper()

    headers = {
        "client_id": ACCESS_ID,
        "access_token": token,
        "sign": sign,
        "t": t,
        "nonce": nonce,
        "sign_method": "HMAC-SHA256",
        "lang": "en",
        "dev_lang": "python",
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/v1.0/devices/{DEVICE_ID}/commands"
    r = requests.post(url, headers=headers, data=body_str)
    logger.info(f"Tuya control response: {r.text}")
    return r.json()

# lambda Handler
def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "")
    body = event.get("body", "")
    if method != "POST":
        return {"statusCode": 200, "body": json.dumps({"status": "alive"})}

    try:
        payload = json.loads(body)
    except Exception as e:
        logger.error(f"bad json: {e}")
        return {"statusCode": 400, "body": json.dumps({"status": "error", "message": "invalid json"})}

    logger.info("Incoming Data: %s", json.dumps(payload, ensure_ascii=False))
    sig_block = payload.get("signature", {})
    if not _verify_signature(sig_block):
        return {"statusCode": 401, "body": json.dumps({"status": "unauthorized"})}

    data = payload.get("payload", {}).get("data", [])
    if not data:
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}

    # example condition
    latest = data[-1]
    pm25 = latest.get("pm25", {}).get("value", 0)
    co2 = latest.get("co2", {}).get("value", 0)

    logger.info(f"Sensor readings -> PM2.5: {pm25}")

    if pm25 > 10:
        logger.info("Air quality poor, turning ON plug")
        control_plug(True)
    else:
        logger.info("Air quality fine, turning OFF plug")
        control_plug(False)

    return {"statusCode": 200, "body": json.dumps({"status": "ok"})}