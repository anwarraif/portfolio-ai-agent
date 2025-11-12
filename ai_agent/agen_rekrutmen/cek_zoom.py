import requests
from requests.auth import HTTPBasicAuth

client_id = "w0gtnkYQRveUwf3EKn1mw"
client_secret = "Lja51uJexGU5uWy8A1jxslSxO9kKYtLx"

# Request token
response = requests.post(
    "https://zoom.us/oauth/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    params={"grant_type": "client_credentials"},
    auth=HTTPBasicAuth(client_id, client_secret),
)

# Print token response
if response.status_code == 200:
    print(response.json())  # Access Token is in the 'access_token' field
else:
    print("Error:", response.text)