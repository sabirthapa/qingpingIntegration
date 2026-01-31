import os
import json
import base64
import logging
from decimal import Decimal
from typing import Dict, Any

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB
DYNAMO_TABLE_DEVICES = os.environ.get("TABLE_QINGPING_DEVICES", "QingpingDevices").strip()
DEVICES_GSI_USER_ID = os.environ.get("DEVICES_GSI_USER_ID", "gsi_user_id").strip()

dynamodb = boto3.resource("dynamodb")
devices_table = dynamodb.Table(DYNAMO_TABLE_DEVICES)

def _json_response(status: int, body: Dict[str, Any]):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_json_default),
    }

def _json_default(o):
    if isinstance(o, Decimal):
        # Convert Decimal to int if it’s whole-number, else float
        if o % 1 == 0:
            return int(o)
        return float(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
    
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

def lambda_handler(event, context):
    """
    Supports:
    - Test event: {"user_id": "dev"}
    - API Gateway body: {"user_id": "dev"}
    - (optional) queryStringParameters.user_id

    Returns list of devices bound to that user_id from QingpingDevices via GSI.
    """
    try:

        SHARED_USER_ID = os.environ.get("SHARED_USER_ID", "qingping_shared").strip()
        user_id = SHARED_USER_ID
        
        resp = devices_table.query(
            IndexName=DEVICES_GSI_USER_ID,
            KeyConditionExpression=Key("user_id").eq(user_id),
        )

        items = resp.get("Items", []) or []

        # Optional: return only fields UI needs (cleaner)
        devices = []
        for it in items:
            devices.append({
                "sensor_mac": it.get("sensor_mac"),
                "device_name": it.get("device_name"),
                "product": it.get("product"),
                "enabled": it.get("enabled", True),
                "bound_at": it.get("bound_at"),
                "version": it.get("version"),
            })

        return _json_response(200, {
            "status": "ok",
            "user_id": user_id,
            "count": len(devices),
            "devices": devices
        })

    except Exception as e:
        logger.exception("Unhandled error")
        return _json_response(500, {"status": "error", "message": str(e)})