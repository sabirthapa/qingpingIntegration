import os
import json
import time
import base64
import logging
import urllib.request
import urllib.parse
from decimal import Decimal
from typing import Dict, Any

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------- ENV ----------
TABLE_QINGPING_DEVICES = os.environ.get("TABLE_QINGPING_DEVICES", "QingpingDevices")
DEVICES_GSI_USER_ID = os.environ.get("DEVICES_GSI_USER_ID", "gsi_user_id")
SHARED_USER_ID = os.environ.get("SHARED_USER_ID", "qingping_shared")

QINGPING_CLIENT_ID = os.environ.get("QINGPING_APP_KEY")
QINGPING_CLIENT_SECRET = os.environ.get("QINGPING_APP_SECRET")

OAUTH_TOKEN_URL = "https://oauth.cleargrass.com/oauth2/token"
QINGPING_DEVICES_API = "https://apis.cleargrass.com/v1/apis/devices"

# ---------- AWS ----------
dynamodb = boto3.resource("dynamodb")
devices_table = dynamodb.Table(TABLE_QINGPING_DEVICES)

# ---------- OAuth token cache (per Lambda container) ----------
_TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0,
}

# ---------- Helpers ----------
def _json_default(o):
    if isinstance(o, Decimal):
        return int(o) if o % 1 == 0 else float(o)
    raise TypeError()

def _json_response(status: int, body: Dict[str, Any]):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_json_default),
    }

# ---------- OAuth ----------
def get_qingping_access_token() -> str:
    now = time.time()

    # Reuse token if still valid
    if _TOKEN_CACHE["access_token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["access_token"]

    auth = base64.b64encode(
        f"{QINGPING_CLIENT_ID}:{QINGPING_CLIENT_SECRET}".encode()
    ).decode()

    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": "device_full_access",
    }).encode()

    req = urllib.request.Request(
        OAUTH_TOKEN_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode())

    token = payload.get("access_token")
    expires_in = int(payload.get("expires_in", 7200))

    if not token:
        raise RuntimeError("Failed to obtain Qingping access token")

    # Cache token (refresh 60s early)
    _TOKEN_CACHE["access_token"] = token
    _TOKEN_CACHE["expires_at"] = now + expires_in - 60

    logger.info("Fetched new Qingping OAuth token")
    return token

# ---------- Qingping API ----------
def fetch_qingping_devices() -> Dict[str, dict]:
    token = get_qingping_access_token()

    url = f"{QINGPING_DEVICES_API}?limit=50&offset=0&timestamp={int(time.time()*1000)}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())

    devices = {}
    for d in data.get("devices", []):
        info = d.get("info", {})
        mac = info.get("mac")
        if not mac:
            continue

        devices[mac] = {
            "sensor_mac": mac,
            "device_name": info.get("name"),
            "product": info.get("product"),
            "version": info.get("version"),
            "enabled": True,
            "user_id": SHARED_USER_ID,
            "bound_at": info.get("created_at"),
        }

    return devices

def fetch_db_devices() -> Dict[str, dict]:
    resp = devices_table.query(
        IndexName=DEVICES_GSI_USER_ID,
        KeyConditionExpression=Key("user_id").eq(SHARED_USER_ID),
    )
    return {it["sensor_mac"]: it for it in resp.get("Items", [])}

# ---------- Lambda ----------
def lambda_handler(event, context):
    try:
        qingping_devices = fetch_qingping_devices()
        db_devices = fetch_db_devices()

        qingping_macs = set(qingping_devices.keys())
        db_macs = set(db_devices.keys())

        # Add new devices
        for mac in qingping_macs - db_macs:
            devices_table.put_item(Item=qingping_devices[mac])
            logger.info(f"Added device {mac}")

        # Remove deleted devices
        for mac in db_macs - qingping_macs:
            devices_table.delete_item(Key={"sensor_mac": mac})
            logger.info(f"Removed device {mac}")

        return _json_response(200, {
            "status": "ok",
            "user_id": SHARED_USER_ID,
            "count": len(qingping_devices),
            "devices": list(qingping_devices.values()),
        })

    except Exception as e:
        logger.exception("Qingping sync failed")
        return _json_response(500, {
            "status": "error",
            "message": str(e),
        })