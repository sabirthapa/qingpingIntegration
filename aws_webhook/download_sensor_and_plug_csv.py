# lambda_function.py
import os
import json
import time
import uuid
import hmac
import hashlib
import base64
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timedelta, timezone
import zoneinfo

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LOCAL_TZ = zoneinfo.ZoneInfo(os.environ.get("LOCAL_TZ", "America/New_York"))

# ---------- ENV ----------
# DynamoDB
SENSOR_READINGS_TABLE = os.environ.get("SENSOR_READINGS_TABLE", "SensorReadings").strip()
SENSOR_READINGS_PK = os.environ.get("SENSOR_READINGS_PK", "sensor_mac").strip()
SENSOR_READINGS_SK = os.environ.get("SENSOR_READINGS_SK", "ts").strip()

MAPPING_TABLE = os.environ.get("TABLE_SENSOR_PLUG_MAPPING", "SensorPlugMapping").strip()

# Tuya
TUYA_ACCESS_ID = os.environ.get("TUYA_ACCESS_ID", "").strip()
TUYA_ACCESS_SECRET = os.environ.get("TUYA_ACCESS_SECRET", "").strip()
TUYA_BASE_URL = os.environ.get("TUYA_BASE_URL", "https://openapi.tuyaus.com").strip()
TUYA_SWITCH_CODE = os.environ.get("TUYA_SWITCH_CODE", "switch_1").strip()

# Token cache
_TUYA_TOKEN_CACHE = {"token": None, "expires_at": 0}

dynamodb = boto3.resource("dynamodb")
readings_table = dynamodb.Table(SENSOR_READINGS_TABLE)
mapping_table = dynamodb.Table(MAPPING_TABLE)

# ---------- Helpers ----------
def _json_response(status: int, body: Dict[str, Any]):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, default=_json_default),
    }

def _csv_response(filename: str, csv_text: str):
    return {
        "statusCode": 200,
        "isBase64Encoded": True,
        "headers": {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": base64.b64encode(csv_text.encode("utf-8")).decode("utf-8"),
    }

def _json_default(o):
    if isinstance(o, Decimal):
        if o % 1 == 0:
            return int(o)
        return float(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

def _clean_sensor_mac(mac: str) -> str:
    return (mac or "").strip().replace(":", "").replace("-", "").upper()

def _get_qs(event: dict) -> dict:
    qsp = event.get("queryStringParameters") or {}
    return qsp if isinstance(qsp, dict) else {}

def _parse_time(value: str, *, is_end: bool = False) -> int:
    if value is None:
        raise ValueError("missing time")
    s = str(value).strip()

    # epoch seconds
    if s.isdigit():
        return int(s)

    # date-only: YYYY-MM-DD
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        d = datetime.strptime(s, "%Y-%m-%d").date()

        if is_end:
            # exclusive next-day midnight (local), then convert to inclusive seconds
            end_local_excl = datetime(d.year, d.month, d.day, tzinfo=LOCAL_TZ) + timedelta(days=1)
            end_utc_excl = end_local_excl.astimezone(timezone.utc)
            return int(end_utc_excl.timestamp()) - 1
        else:
            start_local = datetime(d.year, d.month, d.day, tzinfo=LOCAL_TZ)
            start_utc = start_local.astimezone(timezone.utc)
            return int(start_utc.timestamp())

    # ISO datetime (if no tz given, assume LOCAL_TZ)
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=LOCAL_TZ)
        return int(dt.astimezone(timezone.utc).timestamp())
    except Exception:
        raise ValueError(f"Invalid time format: {s}")

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _build_canonical_query(query: Optional[Dict[str, Any]]) -> str:
    if not query:
        return ""
    cleaned = {k: v for k, v in query.items() if v is not None and str(v) != ""}
    return urlencode(sorted(cleaned.items()), doseq=True)

def _tuya_sign(method: str, path_with_query: str, body_str: str, access_token: str, t_ms: str, nonce: str) -> str:
    content_sha256 = _sha256_hex(body_str) if body_str else hashlib.sha256(b"").hexdigest()
    string_to_sign = f"{method.upper()}\n{content_sha256}\n\n{path_with_query}"
    message = f"{TUYA_ACCESS_ID}{access_token}{t_ms}{nonce}{string_to_sign}"
    return hmac.new(
        TUYA_ACCESS_SECRET.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest().upper()

def _http_json(method: str, url: str, headers: dict, body_str: str = "") -> dict:
    data = body_str.encode("utf-8") if body_str else None
    req = Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError({"http": e.code, "body": raw})
    except URLError as e:
        raise RuntimeError({"http": "url_error", "body": str(e)})

def tuya_request(method: str, path: str, token: str = "", query: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> dict:
    if not TUYA_ACCESS_ID or not TUYA_ACCESS_SECRET:
        raise RuntimeError("Missing TUYA_ACCESS_ID or TUYA_ACCESS_SECRET")

    method = method.upper()
    body_str = json.dumps(body, separators=(",", ":")) if body else ""
    t_ms = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())

    qs = _build_canonical_query(query)
    path_with_query = path + (f"?{qs}" if qs else "")

    sign = _tuya_sign(method, path_with_query, body_str, token, t_ms, nonce)

    headers = {
        "client_id": TUYA_ACCESS_ID,
        "sign": sign,
        "t": t_ms,
        "nonce": nonce,
        "sign_method": "HMAC-SHA256",
    }
    if token:
        headers["access_token"] = token
    if body:
        headers["Content-Type"] = "application/json"

    url = TUYA_BASE_URL + path_with_query
    data = _http_json(method, url, headers=headers, body_str=body_str)

    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(data)

    return data

def get_tuya_token() -> str:
    now = time.time()
    if _TUYA_TOKEN_CACHE["token"] and now < _TUYA_TOKEN_CACHE["expires_at"]:
        return _TUYA_TOKEN_CACHE["token"]

    data = tuya_request("GET", "/v1.0/token", token="", query={"grant_type": 1})
    result = data.get("result") or {}
    token = result.get("access_token")
    expire_seconds = int(result.get("expire_time", 7200))

    if not token:
        raise RuntimeError({"msg": "token missing in response", "resp": data})

    _TUYA_TOKEN_CACHE["token"] = token
    _TUYA_TOKEN_CACHE["expires_at"] = now + expire_seconds - 60
    return token

def get_mapping(sensor_mac: str) -> Optional[dict]:
    try:
        resp = mapping_table.get_item(Key={"sensor_mac": sensor_mac})
        return resp.get("Item")
    except Exception as e:
        logger.warning(f"Failed to get mapping for {sensor_mac}: {e}")
        return None

def query_sensor_readings(sensor_mac: str, start_ts: int, end_ts: int) -> List[dict]:
    key_expr = Key(SENSOR_READINGS_PK).eq(sensor_mac) & Key(SENSOR_READINGS_SK).between(start_ts, end_ts)

    items: List[dict] = []
    kwargs = {"KeyConditionExpression": key_expr}
    while True:
        resp = readings_table.query(**kwargs)
        items.extend(resp.get("Items") or [])
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            break
        kwargs["ExclusiveStartKey"] = lek
    return items

def tuya_fetch_switch_logs(token: str, tuya_device_id: str, start_ms: int, end_ms: int) -> List[dict]:
    logs: List[dict] = []
    last_row_key = ""
    size = 100

    while True:
        query = {
            "codes": TUYA_SWITCH_CODE,
            "start_time": start_ms,
            "end_time": end_ms,
            "size": size,
        }
        if last_row_key:
            query["last_row_key"] = last_row_key

        resp = tuya_request("GET", f"/v2.0/cloud/thing/{tuya_device_id}/report-logs", token=token, query=query)
        result = resp.get("result") or {}
        page_logs = result.get("logs") or []
        logs.extend(page_logs)

        has_more = bool(result.get("has_more"))
        last_row_key = result.get("last_row_key") or ""

        if not has_more or not last_row_key:
            break

    return logs

def _to_number(x):
    if isinstance(x, Decimal):
        return int(x) if x % 1 == 0 else float(x)
    return x

def _csv_escape(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        v = json.dumps(v, default=_json_default)
    v = str(_to_number(v))
    if any(c in v for c in [",", '"', "\n", "\r"]):
        v = '"' + v.replace('"', '""') + '"'
    return v

def build_csv(sensor_mac: str, sensor_items: List[dict], plug_logs: List[dict]) -> str:
    """
    Output columns: source, time_iso, time_epoch_s, sensor_mac, metric, value
    """
    rows: List[List[str]] = []
    header = ["source", "time_iso", "time_epoch_s", "sensor_mac", "metric", "value"]
    rows.append(header)

    # Sensor readings
    for it in sensor_items:
        ts = it.get(SENSOR_READINGS_SK)
        ts_s = int(_to_number(ts)) if ts is not None else None
        time_iso = datetime.fromtimestamp(ts_s, tz=timezone.utc).astimezone(LOCAL_TZ).isoformat() if ts_s else ""
        for k, v in it.items():
            if k in (SENSOR_READINGS_PK, SENSOR_READINGS_SK):
                continue
            if isinstance(v, (str, int, float, bool, Decimal)):
                rows.append([
                    "sensor",
                    time_iso,
                    str(ts_s or ""),
                    sensor_mac,
                    k,
                    str(_to_number(v)),
                ])

    # Plug logs (only if available)
    for lg in plug_logs:
        event_ms = lg.get("event_time")
        event_s = int(int(event_ms) / 1000) if event_ms else None
        time_iso = datetime.fromtimestamp(event_s, tz=timezone.utc).astimezone(LOCAL_TZ).isoformat() if event_s else ""
        code = lg.get("code") or TUYA_SWITCH_CODE
        val = lg.get("value")
        rows.append([
            "plug",
            time_iso,
            str(event_s or ""),
            sensor_mac,
            code,
            str(val),
        ])

    lines = []
    for r in rows:
        lines.append(",".join(_csv_escape(x) for x in r))
    return "\n".join(lines) + "\n"

# ---------- Lambda handler ----------
def lambda_handler(event, context):
    # CORS preflight
    method = (event.get("requestContext", {}).get("http", {}).get("method") or "").upper()
    if method == "OPTIONS":
        return _json_response(200, {"status": "ok"})

    try:
        qs = _get_qs(event)

        sensor_mac = _clean_sensor_mac(qs.get("sensor_mac") or "")
        if not sensor_mac:
            return _json_response(400, {"status": "error", "message": "Missing query param: sensor_mac"})

        start_time = qs.get("start_time")
        end_time = qs.get("end_time")
        if not start_time or not end_time:
            return _json_response(400, {"status": "error", "message": "Missing query params: start_time and end_time"})

        start_ts = _parse_time(start_time, is_end=False)
        end_ts = _parse_time(end_time, is_end=True)
        if end_ts < start_ts:
            return _json_response(400, {"status": "error", "message": "end_time must be >= start_time"})

        # 1) Query sensor readings (ALWAYS)
        sensor_items = query_sensor_readings(sensor_mac, start_ts, end_ts)
        
        # If no sensor data found, return error
        if not sensor_items:
            return _json_response(404, {
                "status": "error",
                "message": f"No sensor data found for {sensor_mac} in the specified time range",
                "sensor_mac": sensor_mac,
                "start_time": start_time,
                "end_time": end_time
            })

        # 2) Try to find mapping and fetch plug logs (OPTIONAL)
        plug_logs = []
        mapping = get_mapping(sensor_mac)
        
        if mapping and mapping.get("tuya_device_id"):
            # Mapping exists - try to fetch plug logs
            tuya_device_id = mapping["tuya_device_id"]
            try:
                token = get_tuya_token()
                plug_logs = tuya_fetch_switch_logs(token, tuya_device_id, start_ms=start_ts * 1000, end_ms=end_ts * 1000)
                logger.info(f"Fetched {len(plug_logs)} plug logs for {sensor_mac}")
            except Exception as e:
                # Log error but continue - sensor data is still valid
                logger.warning(f"Failed to fetch plug logs for {sensor_mac}: {e}")
        else:
            logger.info(f"No mapping found for {sensor_mac} - CSV will include sensor data only")

        # 3) Build CSV
        csv_text = build_csv(sensor_mac, sensor_items, plug_logs)
        filename = f"sensor_{sensor_mac}_{start_time}_{end_time}.csv"

        return _csv_response(filename, csv_text)

    except Exception as e:
        logger.exception("download csv failed")
        return _json_response(500, {"status": "error", "message": str(e)})