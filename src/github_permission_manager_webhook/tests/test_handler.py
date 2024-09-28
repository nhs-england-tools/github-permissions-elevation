import pytest
import hmac
import hashlib
from github_permission_manager_webhook.handler import GitHubPermissionManager, get_headers_from_event, request_is_to_elevate_access, comment_contains_approval, approving_own_request

def test_is_valid_request_valid_signature():
    test_permission_manager = GitHubPermissionManager()
    event = {
        'body': '{"key": "value"}'
    }
    headers = {
        'X-Hub-Signature-256': 'sha256=validsignature'
    }
    test_permission_manager.webhook_secret = 'mysecret'

    payload = event['body'].encode('utf-8')
    hash_object = hmac.new(test_permission_manager.webhook_secret.encode('utf-8'), msg=payload, digestmod=hashlib.sha256)
    valid_signature = "sha256=" + hash_object.hexdigest()
    headers['X-Hub-Signature-256'] = valid_signature

    assert test_permission_manager.request_is_from_github(event, headers) == True

def test_is_valid_request_invalid_signature():
    test_permission_manager = GitHubPermissionManager()
    event = {
        'body': '{"key": "value"}'
    }
    headers = {
        'X-Hub-Signature-256': 'sha256=invalidsignature'
    }
    test_permission_manager.webhook_secret = 'mysecret'

    assert test_permission_manager.request_is_from_github(event, headers) == False

def test_is_valid_request_no_signature():
    test_permission_manager = GitHubPermissionManager()
    event = {
        'body': '{"key": "value"}'
    }
    headers = {}
    test_permission_manager.webhook_secret = 'mysecret'

    assert test_permission_manager.request_is_from_github(event, headers) == False

def test_is_valid_request_no_body():
    test_permission_manager = GitHubPermissionManager()
    event = {}
    headers = {
        'X-Hub-Signature-256': 'sha256=validsignature'
    }
    test_permission_manager.webhook_secret = 'mysecret'

    assert test_permission_manager.request_is_from_github(event, headers) == False

def test_is_valid_request_valid_signature_github_example():
    """
    Example data from https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries#testing-the-webhook-payload-validation
    """
    test_permission_manager = GitHubPermissionManager()
    event = {
        'body': 'Hello, World!'
    }
    headers = {}
    test_permission_manager.webhook_secret = "It's a Secret to Everybody"
    valid_signature = "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"
    headers['X-Hub-Signature-256'] = valid_signature

    assert test_permission_manager.request_is_from_github(event, headers) == True

def test_get_headers_from_event_with_headers():
    event = {
        'headers': {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer token'
        }
    }
    expected_headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token'
    }
    assert get_headers_from_event(event) == expected_headers

def test_get_headers_from_event_without_headers():
    event = {
        'body': 'some body content',
        'queryStringParameters': {
            'param1': 'value1'
        }
    }
    assert get_headers_from_event(event) == {}

def test_get_headers_from_event_with_different_casing():
    event = {
        'Headers': {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer token'
        }
    }
    expected_headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token'
    }
    assert get_headers_from_event(event) == expected_headers

def test_get_headers_from_event_with_empty_event():
    event = {}
    assert get_headers_from_event(event) == {}

def test_get_headers_from_event_with_mixed_keys():
    event = {
        'headers': {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer token'
        },
        'body': 'some body content',
        'queryStringParameters': {
            'param1': 'value1'
        }
    }
    expected_headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token'
    }
    assert get_headers_from_event(event) == expected_headers

def test_request_is_to_elevate_access_with_keyword_in_title():
    issue = {
        'title': 'Please request access elevation',
        'body': 'Some body content'
    }
    assert request_is_to_elevate_access(issue) == True

def test_request_is_to_elevate_access_with_keyword_in_body():
    issue = {
        'title': 'Some title',
        'body': 'This is a request to elevate access'
    }
    assert request_is_to_elevate_access(issue) == True

def test_request_is_to_elevate_access_without_keywords():
    issue = {
        'title': 'Some title',
        'body': 'Some body content'
    }
    assert request_is_to_elevate_access(issue) == False

def test_request_is_to_elevate_access_with_empty_title_and_body():
    issue = {
        'title': '',
        'body': ''
    }
    assert request_is_to_elevate_access(issue) == False

def test_request_is_to_elevate_access_with_missing_title_and_body():
    issue = {}
    assert request_is_to_elevate_access(issue) == False

def test_comment_contains_approval_with_approve():
    comment = {
        'body': 'I approve this request.'
    }
    assert comment_contains_approval(comment) == True

def test_comment_contains_approval_with_thumbs_up():
    comment = {
        'body': 'Great job! 👍'
    }
    assert comment_contains_approval(comment) == True

def test_comment_contains_approval_with_both_approve_and_thumbs_up():
    comment = {
        'body': 'I approve this request. 👍'
    }
    assert comment_contains_approval(comment) == True

def test_comment_contains_approval_without_keywords():
    comment = {
        'body': 'This is a comment without approval.'
    }
    assert comment_contains_approval(comment) == False

def test_comment_contains_approval_with_empty_body():
    comment = {
        'body': ''
    }
    assert comment_contains_approval(comment) == False

def test_approving_own_request_same_user():
    user = 'test_user'
    original_requestor = 'test_user'
    assert approving_own_request(user, original_requestor) == True

def test_approving_own_request_different_user():
    user = 'test_user'
    original_requestor = 'different_user'
    assert approving_own_request(user, original_requestor) == False