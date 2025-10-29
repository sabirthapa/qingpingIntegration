import json
from src.oauth import get_access_token
from src.device_api import get_device_list

def main():
    with open("config/credentials.json") as f:
        creds = json.load(f)
    
    app_key = creds["APP_KEY"]
    app_secret = creds["APP_SECRET"]

    token = get_access_token(app_key, app_secret)
    devices = get_device_list(token)

if __name__ == "__main__":
    main()