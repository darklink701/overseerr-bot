from flask import Flask, request
import requests
import json
from dotenv import load_dotenv
import os
app = Flask(__name__)

# Load .env variables again, for overseerr URL.
load_dotenv()

OVERSEERR_URL = os.getenv("OVERSEERR_URL")
# Ensure the environment variable is set

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Missing code", 400
    
    # Log a successful code retrieval in console.
    print(f"[✅] Received code from Plex: {code}") 

    overseerr_token_url = f"{OVERSEERR_URL}/api/v1/auth/oauth/plex/"
    try:
        response = requests.post(overseerr_token_url, json={
            "code": code,
            "redirectUri": "http://localhost:5000/callback" # Substitute your overseerr URL for localhost if needed. I used localhost for testing.
        })
        response.raise_for_status()
    except Exception as e:
        print(f"Error during token exchange: {e}")
        return f"Failed to exchange code: {e}", 500
    
    
    data = response.json()
    # Save user info and token (this should be linked to their Discord ID).
    print("🔑 Logged in user:", json.dumps(data, indent=2))

    return "✅ You are now authenticated. You can close this tab."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
