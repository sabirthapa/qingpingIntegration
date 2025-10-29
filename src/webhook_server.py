from flask import Flask, request, jsonify
import json, hmac, hashlib, os

# load config from /config/credentials.json
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "credentials.json")

with open(CONFIG_PATH, "r") as f:
    creds = json.load(f)

APP_SECRET = creds["APP_SECRET"]

app = Flask(__name__)

@app.route("/qingping-webhook", methods=["POST"])
def receive_data():
    try:
        payload = request.get_json()
        print("\nIncoming Data:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        # extract signature block
        sig_data = payload.get("signature", {})
        token = sig_data.get("token", "")
        timestamp = str(sig_data.get("timestamp", ""))
        signature = sig_data.get("signature", "")

        # verify authenticity using HMAC SHA256
        expected_sig = hmac.new(
            APP_SECRET.encode(),
            (timestamp + token).encode(),
            hashlib.sha256
        ).hexdigest()

        if signature != expected_sig:
            print("Signature verification failed!")
            return jsonify({"status": "unauthorized"}), 401

        # extract sensor data
        sensor_data = payload.get("payload", {}).get("data", [])
        if sensor_data:
            print("Parsed sensor data:")
            print(json.dumps(sensor_data, indent=2))
        else:
            print("No sensor data found in payload.")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)