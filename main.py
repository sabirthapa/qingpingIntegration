import json
from src.oauth import get_access_token

def main():
    with open("config/credentials.json") as f:
        creds = json.load(f)
    
    app_key = creds["APP_KEY"]
    app_secret = creds["APP_SECRET"]

    token = get_access_token(app_key, app_secret)
    print("Access Token:", token)

if __name__ == "__main__":
    main()