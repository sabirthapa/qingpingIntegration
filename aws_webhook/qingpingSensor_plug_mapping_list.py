import os
import json
import base64
import logging
from decimal import Decimal
from typing import Any, Dict

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_SENSOR_PLUG_MAPPING = os.environ.get("TABLE_SENSOR_PLUG_MAPPING", "SensorPlugMapping").strip()
MAPPING_GSI_USER_ID = os.environ.get("MAPPING_GSI_USER_ID", "gsi_user_id").strip()

dynamodb = boto3.resource("dynamodb")
mapping_table = dynamodb.Table(TABLE_SENSOR_PLUG_MAPPING)

# ---------- helpers ----------
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # keep ints as int, floats as float
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)

def _json_response(status: int, body: Dict[str, Any]):
    # Basic CORS for browser calls
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }

def _get_query_param(event: dict, name: str) -> str:
    qsp = event.get("queryStringParameters") or {}
    val = (qsp.get(name) or "").strip() if isinstance(qsp, dict) else ""
    return val

def _get_body_json(event: dict) -> dict:
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

# handler
def lambda_handler(event, context):
    # Preflight
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return _json_response(200, {"status": "ok"})

    try:

        SHARED_USER_ID = os.environ.get("SHARED_USER_ID", "qingping_shared").strip()
        user_id = SHARED_USER_ID

        resp = mapping_table.query(
            IndexName=MAPPING_GSI_USER_ID,
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        items = resp.get("Items", []) or []

        # Return clean fields for UI
        mappings = []
        for it in items:
            mappings.append({
                "user_id": it.get("user_id"),
                "sensor_mac": it.get("sensor_mac"),
                "tuya_device_id": it.get("tuya_device_id"),
                "enabled": it.get("enabled", True),
                "created_at": it.get("created_at"),
                "updated_at": it.get("updated_at"),
            })

        return _json_response(200, {
            "status": "ok",
            "user_id": user_id,
            "count": len(mappings),
            "mappings": mappings
        })

    except Exception as e:
        logger.exception("Unhandled error in mapping list")
        return _json_response(500, {"status": "error", "message": str(e)})