import pytest
from unittest.mock import patch, MagicMock
from unittest.mock import patch, MagicMock
from common.shared_functions import GitHubAuth

@pytest.fixture
def github_auth():
    return GitHubAuth("dummy_key", "12345", "67890")

def test_init(github_auth):
    assert github_auth.private_key == "dummy_key"
    assert github_auth.app_id == "12345"
    assert github_auth.installation_id == "67890"

@pytest.mark.parametrize("current_time", [1600000000])
def test_generate_jwt(github_auth, current_time):
    with patch('time.time', return_value=current_time):
        with patch('jwt.encode', return_value="mocked_jwt_token") as mock_jwt_encode:
            jwt_token = github_auth.generate_jwt()

            assert jwt_token == "mocked_jwt_token"
            mock_jwt_encode.assert_called_once()
            args, kwargs = mock_jwt_encode.call_args
            payload = args[0]
            assert payload['iss'] == github_auth.app_id
            assert payload['iat'] == current_time
            assert payload['exp'] == current_time + 600
            assert kwargs['algorithm'] == "RS256"

def test_get_access_token(github_auth):
    with patch.object(GitHubAuth, 'generate_jwt', return_value="mocked_jwt_token"):
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"token": "mocked_access_token"}
            mock_post.return_value = mock_response

            access_token = github_auth.get_access_token()

            assert access_token == "mocked_access_token"
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == f"https://api.github.com/app/installations/{github_auth.installation_id}/access_tokens"
            assert kwargs['headers']["Authorization"] == "Bearer mocked_jwt_token"
            assert kwargs['headers']["Accept"] == "application/vnd.github.v3+json"
