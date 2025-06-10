import requests
import json
import time
import os

# === CONFIGURATION ===
ZENDESK_SUBDOMAIN = "your_subdomain"  # e.g., 'gmttour'
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI = "your_redirect_uri"
TOKEN_FILE = "zendesk_token.json"

# === TOKEN MANAGEMENT ===

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

def save_token(token_data):
    token_data['timestamp'] = int(time.time())
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)

def is_token_expired(token_data):
    if not token_data:
        return True
    expires_in = token_data.get("expires_in", 0)
    timestamp = token_data.get("timestamp", 0)
    return time.time() > timestamp + expires_in - 60  # refresh 1 min before expiry

def refresh_token(token_data):
    print("🔄 Refreshing access token...")
    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/oauth/tokens"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    new_token = response.json()
    save_token(new_token)
    return new_token

def get_valid_token():
    token_data = load_token()
    if token_data and not is_token_expired(token_data):
        return token_data["access_token"]
    elif token_data:
        return refresh_token(token_data)["access_token"]
    else:
        raise Exception("⚠️ No valid token available. You must authorize first and store the initial token.")

# === API CALL EXAMPLE ===

def call_zendesk_api():
    access_token = get_valid_token()
    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets.json"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 401:
        print("Token might be invalid. Trying to refresh...")
        access_token = refresh_token(load_token())["access_token"]
        headers["Authorization"] = f"Bearer {access_token}"
        response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("✅ API Response:", response.json())

# === RUN ===
if __name__ == "__main__":
    call_zendesk_api()
