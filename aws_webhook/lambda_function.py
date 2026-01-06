import json
import uuid
import os
import hmac
import hashlib
import logging
import requests
import time
from datetime import datetime, timedelta
import boto3
from decimal import Decimal
from typing import Optional
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Qingping
APP_SECRET = os.environ.get("APP_SECRET", "").strip()

# Tuya
ACCESS_ID = os.environ.get("TUYA_ACCESS_ID", "").strip()
ACCESS_SECRET = os.environ.get("TUYA_ACCESS_SECRET", "").strip()
BASE_URL = "https://openapi.tuyaus.com"
_TUYA_TOKEN_CACHE = {"token": None, "expires_at": 0}

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
    
# creating DynamoDB handles
dynamodb = boto3.resource("dynamodb")
TABLE_SENSOR_READINGS = os.environ.get("TABLE_SENSOR_READINGS", "SensorReadings")
TABLE_SENSOR_PLUG_MAPPING = os.environ.get("TABLE_SENSOR_PLUG_MAPPING", "SensorPlugMapping")

readings_table = dynamodb.Table(TABLE_SENSOR_READINGS)
mapping_table = dynamodb.Table(TABLE_SENSOR_PLUG_MAPPING)

def _get_event_body_str(event: dict) -> str:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except Exception:
            return ""
    return body

# save sensor reading
def save_sensor_reading(sensor_mac: str, reading: dict):
    # reading["timestamp"]["value"] is seconds in your payload
    ts_sec = int(reading.get("timestamp", {}).get("value", 0))
    item = {
        "sensor_mac": sensor_mac,
        "ts": ts_sec,  # your DynamoDB sort key (Number)
        "pm25": Decimal(str(reading.get("pm25", {}).get("value", 0))),
        "pm10": Decimal(str(reading.get("pm10", {}).get("value", 0))),
        "co2": Decimal(str(reading.get("co2", {}).get("value", 0))),
        "temperature": Decimal(str(reading.get("temperature", {}).get("value", 0))),
        "humidity": Decimal(str(reading.get("humidity", {}).get("value", 0))),
        "battery": Decimal(str(reading.get("battery", {}).get("value", 0))),
        "received_at": int(time.time())
    }
    try:
        readings_table.put_item(Item=item)
    except Exception as e:
        logger.error(f"DynamoDB put_item failed for {sensor_mac} ts={ts_sec}: {e}")

# lookup plug for a sensor
def get_plug_device_id_for_sensor(sensor_mac: str) -> Optional[str]:
    try:
        resp = mapping_table.get_item(Key={"sensor_mac": sensor_mac})
        item = resp.get("Item")

        if item and item.get("enabled", True):
            return item.get("tuya_device_id")

        return None
    except Exception as e:
        logger.error(f"DynamoDB get_item failed for mapping {sensor_mac}: {e}")
        return None

# detect qingping payload
def _is_qingping_webhook(event: dict) -> bool:
    body = _get_event_body_str(event)
    if not body or body == "":
        return False
    try:
        payload = json.loads(body)
    except Exception:
        return False
    return isinstance(payload, dict) and "signature" in payload and "payload" in payload

# saves data and later controls the right plug
def handle_qingping_webhook(event):
    body = _get_event_body_str(event)
    try:
        payload = json.loads(body)
    except Exception as e:
        logger.error(f"bad json: {e}")
        return {"statusCode": 400, "body": json.dumps({"status": "error", "message": "invalid json"})}

    logger.info("Incoming Qingping Data: %s", json.dumps(payload, ensure_ascii=False))

    sig_block = payload.get("signature", {})
    if not _verify_signature(sig_block):
        return {"statusCode": 401, "body": json.dumps({"status": "unauthorized"})}

    info = payload.get("payload", {}).get("info", {})
    sensor_mac = info.get("mac")
    data_list = payload.get("payload", {}).get("data", [])

    if not sensor_mac or not data_list:
        return {"statusCode": 200, "body": json.dumps({"status": "ok", "message": "no data"})}

    # Save ALL readings (or just latest — your choice)
    for reading in data_list:
        save_sensor_reading(sensor_mac, reading)

    latest = data_list[-1]
    pm25 = float(latest.get("pm25", {}).get("value", 0))
    logger.info(f"Saved readings for {sensor_mac}. Latest pm25={pm25}")

    # OPTIONAL: control plug if mapping exists
    plug_device_id = get_plug_device_id_for_sensor(sensor_mac)
    if plug_device_id:
        state = pm25 >= 9
        logger.info(f"Mapped plug found: {plug_device_id}. Setting switch={state}")
        try:
            control_plug(plug_device_id, state)
        except Exception as e:
            logger.error(f"Tuya control failed for {plug_device_id}: {e}")
    else:
        logger.info(f"No plug mapping found for sensor {sensor_mac} (skipping control)")

    return {"statusCode": 200, "body": json.dumps({"status": "ok"})}

def convert_tuya_timestamp_to_utc_minus_5(ms: int) -> str:
    utc_dt = datetime.utcfromtimestamp(ms / 1000.0)
    est_dt = utc_dt - timedelta(hours=5)   # fixed UTC-5 (no DST handling)
    return est_dt.strftime("%Y-%m-%d %I:%M:%S %p (UTC-5)")

# tuya Control 
def get_tuya_token():
    now = time.time()

    # Reuse token if still valid
    if _TUYA_TOKEN_CACHE["token"] and now < _TUYA_TOKEN_CACHE["expires_at"]:
        return _TUYA_TOKEN_CACHE["token"]

    # 1. Generate timestamp and nonce
    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())

    # 2. Build stringToSign
    content_sha256 = hashlib.sha256(b"").hexdigest()
    string_to_sign = "GET\n" + content_sha256 + "\n\n" + "/v1.0/token?grant_type=1"

    # 3. Build full string to hash
    message = ACCESS_ID + t + nonce + string_to_sign

    # 4. Compute signature
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
    }

    url = f"{BASE_URL}/v1.0/token?grant_type=1"
    r = requests.get(url, headers=headers, timeout=10)
    logger.info(f"Raw token response: {r.text}")
    r.raise_for_status()
    resp = r.json()

    if not resp.get("success"):
        raise Exception(f"Tuya auth failed: {json.dumps(resp)}")

    token = resp["result"]["access_token"]
    expire_seconds = int(resp["result"].get("expire_time", 7200))

    # Cache token (refresh 60s early)
    _TUYA_TOKEN_CACHE["token"] = token
    _TUYA_TOKEN_CACHE["expires_at"] = now + expire_seconds - 60

    return token

def control_plug(device_id: str, state: bool):
    token = get_tuya_token()
    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())

    data = {"commands": [{"code": "switch_1", "value": state}]}
    body_str = json.dumps(data, separators=(",", ":"))
    content_sha256 = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

    path = f"/v1.0/devices/{device_id}/commands"
    string_to_sign = "POST\n" + content_sha256 + "\n\n" + path
    message = ACCESS_ID + token + t + nonce + string_to_sign

    sign = hmac.new(ACCESS_SECRET.encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest().upper()

    headers = {
        "client_id": ACCESS_ID,
        "access_token": token,
        "sign": sign,
        "t": t,
        "nonce": nonce,
        "sign_method": "HMAC-SHA256",
        "Content-Type": "application/json",
    }

    url = BASE_URL + path
    r = requests.post(url, headers=headers, data=body_str, timeout=10)
    logger.info(f"Tuya control response: {r.text}")
    r.raise_for_status()
    return r.json()

def lambda_handler(event, context):

    # 1) Qingping webhook (real events)
    if _is_qingping_webhook(event):
        return handle_qingping_webhook(event)

    # 2) Manual demo / AWS test event
    if event.get("manual_on") or event.get("manual_off") or event.get("read_status"):
        return handle_manual(event)

    # 3) default (health check)
    return {"statusCode": 200, "body": json.dumps({"status": "alive"})}

def handle_manual(event):
    # device id for manual control
    device_id = event.get("device_id") or os.environ.get("TUYA_DEVICE_ID", "").strip()
    if not device_id:
        return {"statusCode": 400, "body": json.dumps({"status": "error", "message": "missing device_id"})}

    if event.get("manual_on"):
        logger.info("MANUAL DEMO → Turning plug ON")
        return {"statusCode": 200, "body": json.dumps(control_plug(device_id, True))}

    if event.get("manual_off"):
        logger.info("MANUAL DEMO → Turning plug OFF")
        return {"statusCode": 200, "body": json.dumps(control_plug(device_id, False))}

    if event.get("read_status"):
        logger.info("Reading plug status")
        result = read_plug_status(device_id)
        if result.get("success") and "t" in result:
            logger.info(f"Tuya server time (UTC-5): {convert_tuya_timestamp_to_utc_minus_5(result['t'])}")
        return {"statusCode": 200, "body": json.dumps(result)}
    
    return {"statusCode": 200, "body": json.dumps({"status": "no manual command detected"})}

def read_plug_status(device_id: str):
    token = get_tuya_token()
    t = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())

    content_sha256 = hashlib.sha256(b"").hexdigest()
    path = f"/v1.0/devices/{device_id}/status"
    string_to_sign = "GET\n" + content_sha256 + "\n\n" + path
    message = ACCESS_ID + token + t + nonce + string_to_sign

    sign = hmac.new(ACCESS_SECRET.encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest().upper()

    headers = {
        "client_id": ACCESS_ID,
        "access_token": token,
        "sign": sign,
        "t": t,
        "nonce": nonce,
        "sign_method": "HMAC-SHA256",
    }

    r = requests.get(BASE_URL + path, headers=headers, timeout=10)
    logger.info(f"Plug status response: {r.text}")
    r.raise_for_status()
    return r.json()