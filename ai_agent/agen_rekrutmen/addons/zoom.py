import requests
import time
import logging

logger = logging.getLogger(__name__)

class CustomZoomTool(ZoomTool):
    def __init__(self, *, account_id: Optional[str] = None, client_id: Optional[str] = None, client_secret: Optional[str] = None, name: str = "zoom_tool"):
        super().__init__(account_id=account_id, client_id=client_id, client_secret=client_secret, name=name)
        self.token_url = "https://zoom.us/oauth/token"
        self.access_token = None
        self.token_expires_at = 0

    def get_access_token(self) -> str:
        if self.access_token and time.time() < self.token_expires_at:
            return str(self.access_token)
            
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "account_credentials", "account_id": self.account_id}

        try:
            response = requests.post(self.token_url, headers=headers, data=data, auth=(self.client_id, self.client_secret))
            response.raise_for_status()

            token_info = response.json()
            self.access_token = token_info["access_token"]
            expires_in = token_info["expires_in"]
            self.token_expires_at = time.time() + expires_in - 60

            self._set_parent_token(str(self.access_token))
            return str(self.access_token)

        except requests.RequestException as e:
            logger.error(f"Error fetching access token: {e}")
            return ""

    def create_meeting(self, topic: str, start_time: str, duration: int, timezone: str = "UTC") -> dict:
        """Create a Zoom Meeting."""
        url = "https://api.zoom.us/v2/users/me/meetings"
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        payload = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_time,  # ISO 8601 format: "2023-01-01T12:00:00Z"
            "duration": duration,  # Duration in minutes
            "timezone": timezone,
            "settings": {
                "join_before_host": True,
                "waiting_room": False
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error creating Zoom meeting: {e}")
            return {}


zoom_tool = CustomZoomTool(
    account_id="your_zoom_account_id",
    client_id="your_zoom_client_id",
    client_secret="your_zoom_client_secret"
)

# Buat meeting
meeting_info = zoom_tool.create_meeting(
    topic="Interview with Candidate",
    start_time="2025-01-15T10:00:00Z",  # Sesuaikan dengan waktu interview
    duration=30,  # 30 menit
    timezone="Asia/Jakarta"
)

# Ambil link Zoom
if meeting_info:
    meeting_link = meeting_info.get("join_url", "Link not available")
    print(f"Zoom Meeting Link: {meeting_link}")
else:
    print("Failed to create Zoom Meeting.")
