import os
import json
import time
import base64
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB table (SensorPlugMapping)
TABLE_SENSOR_PLUG_MAPPING = os.environ.get("TABLE_SENSOR_PLUG_MAPPING", "SensorPlugMapping").strip()
dynamodb = boto3.resource("dynamodb")
mapping_table = dynamodb.Table(TABLE_SENSOR_PLUG_MAPPING)

def _json_default(o):
    if isinstance(o, Decimal):
        # int if whole, else float
        return int(o) if o % 1 == 0 else float(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

def _json_response(status: int, body: Dict[str, Any]):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_json_default),
    }

def _get_event_body_json(event: dict) -> dict:
    """
    Supports:
    - Lambda test event: event itself is the body dict
    - API Gateway (proxy): event["body"] is JSON string (maybe base64)
    """
    # If it looks like a direct test event dict, use it
    if isinstance(event, dict) and "body" not in event and ("sensor_mac" in event or "tuya_device_id" in event):
        return event

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

def _normalize_bool(v: Any, default: bool = True) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "y", "on"):
            return True
        if s in ("false", "0", "no", "n", "off"):
            return False
    return default

def _clean_sensor_mac(mac: str) -> str:
    # normalize like "CCB5D131C3D0" (no colons, uppercase)
    mac = (mac or "").strip().replace(":", "").replace("-", "").upper()
    return mac

def upsert_mapping(sensor_mac: str, tuya_device_id: str, enabled: bool, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Writes/updates:
      PK: sensor_mac (String)
      enabled (BOOL)
      tuya_device_id (String)
    Also stores:
      updated_at (Number)
      created_at (Number) if new
      user_id (String) optional (handy for UI later)
    """
    now = int(time.time())

    # Check existing to preserve created_at if present
    existing = {}
    try:
        resp = mapping_table.get_item(Key={"sensor_mac": sensor_mac})
        existing = resp.get("Item") or {}
    except Exception as e:
        logger.warning("get_item failed (continuing): %s", e)

    item = {
        "sensor_mac": sensor_mac,
        "tuya_device_id": tuya_device_id,
        "enabled": enabled,
        "updated_at": now,
    }

    if "created_at" in existing:
        item["created_at"] = existing["created_at"]
    else:
        item["created_at"] = now

    if user_id:
        item["user_id"] = user_id

    mapping_table.put_item(Item=item)
    return item

def lambda_handler(event, context):
    """
    Input (UI / test event):
    {
      "sensor_mac": "CCB5D131C3D0",
      "tuya_device_id": "eb0c85955233eb117aygws",
      "enabled": true,
      "user_id": "dev"   // optional
    }

    Optional delete/unbind:
    {
      "sensor_mac": "CCB5D131C3D0",
      "delete": true
    }
    """
    try:
        body = _get_event_body_json(event)

        # Support quick delete/unbind
        delete_flag = _normalize_bool(body.get("delete"), default=False)

        sensor_mac = _clean_sensor_mac(body.get("sensor_mac") or "")
        if not sensor_mac:
            return _json_response(400, {"status": "error", "message": "Missing sensor_mac"})

        if delete_flag:
            mapping_table.delete_item(Key={"sensor_mac": sensor_mac})
            return _json_response(200, {"status": "ok", "message": "deleted", "sensor_mac": sensor_mac})

        tuya_device_id = (body.get("tuya_device_id") or "").strip()
        if not tuya_device_id:
            return _json_response(400, {"status": "error", "message": "Missing tuya_device_id"})

        enabled = _normalize_bool(body.get("enabled"), default=True)
        
        SHARED_USER_ID = os.environ.get("SHARED_USER_ID", "qingping_shared").strip()
        saved = upsert_mapping(sensor_mac, tuya_device_id, enabled, user_id=SHARED_USER_ID)

        return _json_response(200, {
            "status": "ok",
            "mapping": {
                "sensor_mac": saved.get("sensor_mac"),
                "tuya_device_id": saved.get("tuya_device_id"),
                "enabled": saved.get("enabled"),
                "created_at": saved.get("created_at"),
                "updated_at": saved.get("updated_at"),
                "user_id": saved.get("user_id"),
            }
        })

    except Exception as e:
        logger.exception("Unhandled error")
        return _json_response(500, {"status": "error", "message": str(e)})