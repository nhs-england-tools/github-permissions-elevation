import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import time
import json
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import requests

from github_permission_manager_webhook.handler import GitHubPermissionManager, GitHubAuth
from github_permission_manager_webhook.utilities import get_headers_from_event, request_is_to_elevate_access, comment_contains_approval, approving_own_request

@pytest.fixture
def github_permission_manager():
    mock_requests = MagicMock()
    return GitHubPermissionManager(requests_module=mock_requests)

@pytest.fixture
def mock_ssm_client():
    with patch('boto3.client') as mock_client:
        yield mock_client.return_value

@pytest.fixture
def mock_dynamodb():
    with patch('boto3.resource') as mock_resource:
        yield mock_resource.return_value

@pytest.fixture
def mock_step_functions():
    with patch('boto3.client') as mock_client:
        yield mock_client.return_value

def generate_mock_private_key():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return pem.decode('utf-8')

def generate_mock_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem.decode('utf-8'), public_pem.decode('utf-8')

def test_get_headers_from_event():
    event = {'headers': {'X-GitHub-Event': 'issues'}}
    assert get_headers_from_event(event) == {'X-GitHub-Event': 'issues'}

def test_request_is_to_elevate_access():
    issue = {'title': 'Request to elevate access', 'body': 'Please elevate my access'}
    assert request_is_to_elevate_access(issue) == True

def test_comment_contains_approval():
    comment = {'body': 'I approve this request 👍'}
    assert comment_contains_approval(comment) == True

def test_github_auth_generate_jwt():
    mock_private_key, mock_public_key = generate_mock_key_pair()
    auth = GitHubAuth(mock_private_key, 'app_id', 'installation_id')

    current_time = int(time.time())
    with patch('time.time', return_value=current_time):
        jwt_token = auth.generate_jwt()

        # Decode the JWT to verify its contents
        decoded = jwt.decode(jwt_token, mock_public_key, algorithms=['RS256'])

        assert decoded['iss'] == 'app_id'
        assert decoded['iat'] == current_time
        assert decoded['exp'] == current_time + 600  # 10 minutes later

def test_get_token_to_access_github(github_permission_manager):
    with patch('github_permission_manager_webhook.handler.GitHubAuth') as MockGitHubAuth:
        mock_github_auth_instance = MockGitHubAuth.return_value
        mock_github_auth_instance.get_access_token.return_value = "mock_access_token"

        result = github_permission_manager.get_token_to_access_github()

        MockGitHubAuth.assert_called_once_with(
            github_permission_manager.private_key,
            github_permission_manager.app_id,
            github_permission_manager.installation_id
        )

        mock_github_auth_instance.get_access_token.assert_called_once()

        expected_result = {
            "Authorization": "Bearer mock_access_token",
            "Accept": "application/vnd.github.v3+json"
        }
        assert result == expected_result

def test_initialise_aws_clients(github_permission_manager):
    with patch('boto3.resource') as mock_resource, \
        patch('boto3.client') as mock_client:
        github_permission_manager.initialise_aws_clients()
        mock_resource.assert_called_once_with('dynamodb', region_name='eu-west-2')
        mock_client.assert_any_call('stepfunctions', region_name='eu-west-2')
        mock_client.assert_any_call('ssm', region_name='eu-west-2')

def test_get_all_parameters(github_permission_manager):
    with patch.dict('os.environ', {'WORKSPACE': 'workspace'}), \
        patch.object(github_permission_manager, 'get_ssm_parameter') as mock_get_ssm_parameter, \
        patch.object(github_permission_manager, 'get_token_to_access_github') as mock_get_token_to_access_github:

        mock_get_ssm_parameter.side_effect = lambda param: f"mock_{param.split('/')[-1]}"
        mock_get_token_to_access_github.return_value = {"Authorization": "Bearer mock_token"}

        github_permission_manager.get_all_parameters()

        mock_get_ssm_parameter.assert_any_call('/github_permission_manager_webhook/workspace_app_id')
        mock_get_ssm_parameter.assert_any_call('/github_permission_manager_webhook/workspace_private_key')
        mock_get_ssm_parameter.assert_any_call('/github_permission_manager_webhook/workspace_installation_id')
        mock_get_ssm_parameter.assert_any_call('/github_permission_manager_webhook/workspace_secret_for_webhook')
        mock_get_ssm_parameter.assert_any_call('/github_permission_manager_demotion/workspace_step_function_arn')
        # Verify that get_token_to_access_github was called
        mock_get_token_to_access_github.assert_called_once()

        assert github_permission_manager.app_id == "mock_workspace_app_id"
        assert github_permission_manager.private_key == "mock_workspace_private_key"
        assert github_permission_manager.installation_id == "mock_workspace_installation_id"
        assert github_permission_manager.webhook_secret == "mock_workspace_secret_for_webhook"
        assert github_permission_manager.step_function_arn == "mock_workspace_step_function_arn"
        assert github_permission_manager.auth_headers == {"Authorization": "Bearer mock_token"}

def test_post_comment_on_issue(github_permission_manager):
    payload = {'repository': {'full_name': 'org/repo'}, 'issue': {'number': 1}}
    comment_body = 'Test comment'

    mock_post = github_permission_manager.requests.post
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_post.return_value = mock_response

    github_permission_manager.post_comment_on_issue(payload, comment_body)

    mock_post.assert_called_once_with(
        'https://api.github.com/repos/org/repo/issues/1/comments',
        headers=github_permission_manager.auth_headers,
        json={"body": comment_body}
    )

    assert mock_post.called

def test_post_comment_on_issue_http_error(github_permission_manager, capfd):
    payload = {'repository': {'full_name': 'org/repo'}, 'issue': {'number': 1}}
    comment_body = 'Test comment'

    mock_post = github_permission_manager.requests.post
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
    mock_post.return_value = mock_response

    github_permission_manager.post_comment_on_issue(payload, comment_body)

    mock_post.assert_called_once_with(
        'https://api.github.com/repos/org/repo/issues/1/comments',
        headers=github_permission_manager.auth_headers,
        json={"body": comment_body}
    )

    # Capture the output
    captured = capfd.readouterr()
    assert "HTTP error occurred: Not Found" in captured.out
    assert mock_post.called

def test_post_comment_on_issue_other_error(github_permission_manager, capfd):
    payload = {'repository': {'full_name': 'org/repo'}, 'issue': {'number': 1}}
    comment_body = 'Test comment'

    mock_post = github_permission_manager.requests.post
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("Some other error")
    mock_post.return_value = mock_response

    github_permission_manager.post_comment_on_issue(payload, comment_body)

    mock_post.assert_called_once_with(
        'https://api.github.com/repos/org/repo/issues/1/comments',
        headers=github_permission_manager.auth_headers,
        json={"body": comment_body}
    )

    # Capture the output
    captured = capfd.readouterr()
    assert "Other error occurred: Some other error" in captured.out
    assert mock_post.called

def test_make_owner_on_github(github_permission_manager):
    payload = {
        'organization': {'login': 'test-org'}
    }
    user = 'test-user'

    mock_put = github_permission_manager.requests.put
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_put.return_value = mock_response

    github_permission_manager.make_owner_on_github(payload, user)

    mock_put.assert_called_once_with(
        'https://api.github.com/orgs/test-org/memberships/test-user',
        headers=github_permission_manager.auth_headers,
        json={"role": "admin"}
    )

    assert mock_response.status_code == 200

def test_is_team_member(github_permission_manager):
    user = 'user'
    org = 'org'
    team = 'team'

    mock_get = github_permission_manager.requests.get
    mock_response_team = MagicMock()
    mock_response_team.json.return_value = {'id': 1}
    mock_response_team.status_code = 200

    mock_response_membership = MagicMock()
    mock_response_membership.status_code = 200

    mock_get.side_effect = [mock_response_team, mock_response_membership]

    result = github_permission_manager.is_team_member(user, org, team)

    mock_get.assert_any_call(
        f'https://api.github.com/orgs/{org}/teams/{team}',
        headers=github_permission_manager.auth_headers
    )

    mock_get.assert_any_call(
        f'https://api.github.com/teams/1/memberships/{user}',
        headers=github_permission_manager.auth_headers
    )

    assert result == True

def test_handle_issue_ineligible_user(github_permission_manager):
    payload = {
        'action': 'opened',
        'issue': {'title': 'Request elevation', 'user': {'login': 'user'}},
        'repository': {'owner': {'login': 'org'}}
    }
    with patch.object(github_permission_manager, '_is_user_eligible_for_elevation', return_value=False) as mock_elevation_eligible, \
        patch.object(github_permission_manager, '_process_elevation_request') as mock_process, \
        patch.object(github_permission_manager, '_notify_ineligible_user') as mock_notify_ineligible:
        github_permission_manager.handle_issue(json.dumps(payload))
        mock_process.assert_not_called()
        mock_elevation_eligible.assert_called_once()
        mock_notify_ineligible.assert_called_once()

def test_handle_issue_eligible_user(github_permission_manager):
    payload = {
        'action': 'opened',
        'issue': {'title': 'Request elevation', 'user': {'login': 'user'}},
        'repository': {'owner': {'login': 'org'}}
    }
    with patch.object(github_permission_manager, '_is_user_eligible_for_elevation', return_value=True) as mock_elevation_eligible, \
        patch.object(github_permission_manager, '_process_elevation_request') as mock_process, \
        patch.object(github_permission_manager, '_notify_ineligible_user') as mock_notify_ineligible:
        github_permission_manager.handle_issue(json.dumps(payload))
        mock_process.assert_called_once()
        mock_elevation_eligible.assert_called_once()
        mock_notify_ineligible.assert_not_called()

def test_handle_issue_comment_eligible_user(github_permission_manager):
    payload = {
        'action': 'created',
        'comment': {'user': {'login': 'user'}, 'body': 'approve'},
        'repository': {'owner': {'login': 'org'}}
    }
    with patch.object(github_permission_manager, '_is_user_eligible_for_elevation', return_value=True) as mock_elevation_eligible, \
        patch.object(github_permission_manager, '_handle_approval_comment') as mock_handle:
        github_permission_manager.handle_issue_comment(json.dumps(payload))
        mock_handle.assert_called_once()
        mock_elevation_eligible.assert_called_once()

def test_handle_issue_comment_ineligible_user(github_permission_manager):
    payload = {
        'action': 'created',
        'comment': {'user': {'login': 'user'}, 'body': 'approve'},
        'repository': {'owner': {'login': 'org'}}
    }
    with patch.object(github_permission_manager, '_is_user_eligible_for_elevation', return_value=False) as mock_elevation_eligible, \
        patch.object(github_permission_manager, '_handle_approval_comment') as mock_handle:
        github_permission_manager.handle_issue_comment(json.dumps(payload))
        mock_handle.assert_not_called()
        mock_elevation_eligible.assert_called_once()

def test_main_handler(github_permission_manager):
    event = {'headers': {'X-GitHub-Event': 'issues'}, 'body': '{}'}
    with patch.object(github_permission_manager, 'initialise_aws_clients'), \
        patch.object(github_permission_manager, 'get_all_parameters'), \
        patch.object(github_permission_manager, 'request_is_from_github', return_value=True), \
        patch.object(github_permission_manager, 'handle_issue') as mock_handle:
        response = github_permission_manager.main(event, None)
        mock_handle.assert_called_once()
        assert response['statusCode'] == 200
        assert json.loads(response['body']) == {'response': 'yes'}
