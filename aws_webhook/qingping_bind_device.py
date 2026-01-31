import os
import json
import time
import base64
import logging
from typing import Dict, Any

import requests
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Qingping endpoints
OAUTH_BASE = "https://oauth.cleargrass.com"
API_BASE = "https://apis.cleargrass.com"

# env vars
QINGPING_APP_KEY = os.environ.get("QINGPING_APP_KEY", "").strip()
QINGPING_APP_SECRET = os.environ.get("QINGPING_APP_SECRET", "").strip()

# DynamoDB
DYNAMO_TABLE_DEVICES = os.environ.get("TABLE_QINGPING_DEVICES", "QingpingDevices")
dynamodb = boto3.resource("dynamodb")
devices_table = dynamodb.Table(DYNAMO_TABLE_DEVICES)

# token cache (warm Lambda reuse)
_TOKEN_CACHE = {"token": None, "expires_at": 0}

def _json_response(status: int, body: Dict[str, Any]):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }

def _get_event_body_json(event: dict) -> dict:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except Exception:
            return {}
    if not body:
        return {}
    if isinstance(body, str):
        try:
            return json.loads(body)
        except Exception:
            return {}
    return body if isinstance(body, dict) else {}

def get_qingping_access_token() -> str:
    """
    OAuth2 Client Credentials flow.
    Returns a bearer access token, cached until near expiry.
    """
    now = int(time.time())
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]

    if not QINGPING_APP_KEY or not QINGPING_APP_SECRET:
        raise RuntimeError("Missing QINGPING_APP_KEY or QINGPING_APP_SECRET env var")

    basic_raw = f"{QINGPING_APP_KEY}:{QINGPING_APP_SECRET}".encode("utf-8")
    basic_b64 = base64.b64encode(basic_raw).decode("utf-8")

    url = f"{OAUTH_BASE}/oauth2/token"
    headers = {
        "Authorization": f"Basic {basic_b64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "device_full_access",
    }

    r = requests.post(url, headers=headers, data=data, timeout=10)
    logger.info("OAuth token response: %s", r.text)
    r.raise_for_status()

    resp = r.json()
    token = resp.get("access_token")
    expires_in = int(resp.get("expires_in", 0))

    if not token or expires_in <= 0:
        raise RuntimeError(f"Unexpected token response: {resp}")

    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = now + expires_in - 60  # refresh 60s early
    return token

def bind_device(device_token: str, product_id: int) -> Dict[str, Any]:
    access_token = get_qingping_access_token()
    url = f"{API_BASE}/v1/apis/devices"

    payload = {
        "device_token": device_token,
        "product_id": int(product_id),
        "timestamp": int(time.time() * 1000),
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    r = requests.post(url, headers=headers, json=payload, timeout=10)
    logger.info("Device bind response: %s", r.text)
    r.raise_for_status()
    return r.json()

def save_bound_device(user_id: str, result: dict):
    info = (result or {}).get("info", {}) or {}
    mac = info.get("mac")
    if not mac:
        raise RuntimeError(f"Bind response missing info.mac: {result}")

    item = {
        "sensor_mac": mac,              # partition key
        "user_id": user_id,
        "device_name": info.get("name"),
        "version": info.get("version"),
        "created_at": info.get("created_at"),
        "product": info.get("product"),
        "bound_at": int(time.time()),
        "enabled": True,
    }

    devices_table.put_item(Item=item)

def lambda_handler(event, context):
    """
    Input from UI:
    {
      "user_id": "dev",
      "device_token": "143412",
      "product_id": 1203
    }
    """
    try:
        body_json = _get_event_body_json(event)

        user_id = (body_json.get("user_id") or "dev").strip()  # temp default until auth exists
        device_token = (body_json.get("device_token") or "").strip()
        product_id = body_json.get("product_id")

        if not device_token or product_id is None:
            return _json_response(400, {
                "status": "error",
                "message": "Missing device_token or product_id"
            })

        result = bind_device(device_token, int(product_id))
        save_bound_device(user_id, result)

        return _json_response(200, {
            "status": "ok",
            "bound": {
                "user_id": user_id,
                "mac": result.get("info", {}).get("mac"),
                "name": result.get("info", {}).get("name"),
                "product": result.get("info", {}).get("product"),
            },
            "raw": result
        })

    except requests.HTTPError as e:
        details = ""
        try:
            details = e.response.text if e.response is not None else ""
        except Exception:
            pass
        return _json_response(502, {
            "status": "error",
            "message": "Qingping API HTTP error",
            "details": details
        })

    except Exception as e:
        logger.exception("Unhandled error")
        return _json_response(500, {"status": "error", "message": str(e)})