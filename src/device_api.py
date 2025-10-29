import requests
import time
import json

def get_device_list(access_token: str):
    """Fetch list of devices bound to your Qingping account."""
    timestamp = int(time.time() * 1000)
    url = f"https://apis.cleargrass.com/v1/apis/devices?timestamp={timestamp}"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch devices: {response.text}")

    devices = response.json()
    print("Devices retrieved successfully:")
    print(json.dumps(devices, indent=2))
    return devices