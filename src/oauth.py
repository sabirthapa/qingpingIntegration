import requests
import base64

def get_access_token(app_key: str, app_secret: str) -> str:
    """Obtain OAuth 2.0 access token from Qingping."""
    url = "https://oauth.cleargrass.com/oauth2/token"
    auth_header = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "device_full_access"
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        raise Exception(f"Failed to get token: {response.text}")

    token = response.json().get("access_token")
    print("Access token acquired successfully.")
    return token