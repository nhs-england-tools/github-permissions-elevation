import jwt
import time
import requests

DEFAULT_REGION = 'eu-west-2'
ESCALATION_TEAM_NAME = 'can-escalate-to-become-an-owner'
ELEVATION_BOT = 'elevatemetoowner[bot]'

class GitHubAuth:
    def __init__(self, private_key, app_id, installation_id):
        self.private_key = private_key
        self.app_id = app_id
        self.installation_id = installation_id

    def generate_jwt(self):
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + (10 * 60),  # JWT expires in 10 minutes
            "iss": self.app_id
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def get_access_token(self):
        jwt_token = self.generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.post(
            f"https://api.github.com/app/installations/{self.installation_id}/access_tokens",
            headers=headers
        )
        return response.json()["token"]
