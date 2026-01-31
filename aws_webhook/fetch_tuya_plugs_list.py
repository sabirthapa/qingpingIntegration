# lambda_function.py
import os
import json
import time
import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# env
TUYA_ACCESS_ID = os.environ.get("TUYA_ACCESS_ID", "").strip()
TUYA_ACCESS_SECRET = os.environ.get("TUYA_ACCESS_SECRET", "").strip()
TUYA_BASE_URL = os.environ.get("TUYA_BASE_URL", "https://openapi.tuyaus.com").strip()

# we have separate script to fetch this
TUYA_SPACE_ID = os.environ.get("TUYA_SPACE_ID", "").strip()

# Optional filters, leave empty to return everything in the space.
TUYA_CATEGORIES = os.environ.get("TUYA_CATEGORIES", "").strip()
_TUYA_TOKEN_CACHE = {"token": None, "expires_at": 0}

# helpers
def _json_response(status: int, body: Dict[str, Any]):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body),
    }


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


def tuya_request(method: str, path: str, token: str = "", query: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None):
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
    resp = requests.request(method, url, headers=headers, data=body_str if body_str else None, timeout=15)
    data = resp.json() if resp.text else {}

    if not resp.ok:
        raise RuntimeError({"http": resp.status_code, "body": data})

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


def list_all_devices_in_space(token: str, space_id: str):
    """
    Uses:
      GET /v2.0/cloud/thing/space/device
    Pagination:
      page_size max 20
      last_id = last returned device id
    """
    all_devices = []
    last_id = None
    page_size = 20

    while True:
        query = {
            "space_ids": space_id,  
            "page_size": page_size,
        }
        if last_id:
            query["last_id"] = last_id
        if TUYA_CATEGORIES:
            query["categories"] = TUYA_CATEGORIES

        resp = tuya_request("GET", "/v2.0/cloud/thing/space/device", token=token, query=query)
        items = resp.get("result") or []
        if not items:
            break

        all_devices.extend(items)
        last_id = items[-1].get("id")

        # If fewer than page_size returned, done
        if len(items) < page_size:
            break

    return all_devices


# Lambda handler
def lambda_handler(event, context):
    # Preflight for browser CORS
    method = (event.get("requestContext", {}).get("http", {}).get("method") or "").upper()
    if method == "OPTIONS":
        return _json_response(200, {"status": "ok"})

    try:
        if not TUYA_SPACE_ID:
            return _json_response(400, {
                "status": "error",
                "message": "Missing TUYA_SPACE_ID env var (set it to your 'My Space' space_id)."
            })

        token = get_tuya_token()
        devices = list_all_devices_in_space(token, TUYA_SPACE_ID)

        # Clean output for frontend dropdown
        cleaned = []
        for d in devices:
            cleaned.append({
                "tuya_device_id": d.get("id"),
                "name": d.get("customName") or d.get("custom_name") or d.get("name"),
                "category": d.get("category"),
                "online": d.get("isOnline") if "isOnline" in d else d.get("is_online"),
            })

        # Optional: sort by name
        cleaned.sort(key=lambda x: (x.get("name") or "").lower())

        return _json_response(200, {
            "status": "ok",
            "space_id": TUYA_SPACE_ID,
            "count": len(cleaned),
            "devices": cleaned,
        })

    except Exception as e:
        logger.exception("list_tuya_devices failed")
        return _json_response(500, {"status": "error", "message": str(e)})