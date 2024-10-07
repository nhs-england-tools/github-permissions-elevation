import json
import boto3
import hmac
import hashlib
import requests
import os
from datetime import datetime
from common.shared_functions import GitHubAuth, DEFAULT_REGION, ESCALATION_TEAM_NAME, ELEVATION_BOT
from utilities import get_headers_from_event, request_is_to_elevate_access, comment_contains_approval, approving_own_request

class GitHubPermissionManager:
    def __init__(self, requests_module=requests):
        self.dynamodb = None
        self.step_functions = None
        self.ssm_client = None
        self.app_id = None
        self.private_key = None
        self.installation_id = None
        self.webhook_secret = None
        self.step_function_arn = None
        self.auth_headers = None
        self.requests = requests_module

    def initialise_aws_clients(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=DEFAULT_REGION)
        self.step_functions = boto3.client('stepfunctions', region_name=DEFAULT_REGION)
        self.ssm_client = boto3.client('ssm', region_name=DEFAULT_REGION)

    def get_all_parameters(self):
        workspace = os.getenv('WORKSPACE')
        self.app_id = self.get_ssm_parameter(f"/github_permission_manager_webhook/{workspace}_app_id")
        self.private_key = self.get_ssm_parameter(f"/github_permission_manager_webhook/{workspace}_private_key")
        self.installation_id = self.get_ssm_parameter(f"/github_permission_manager_webhook/{workspace}_installation_id")
        self.webhook_secret = self.get_ssm_parameter(f"/github_permission_manager_webhook/{workspace}_secret_for_webhook")
        self.step_function_arn = self.get_ssm_parameter(f"/github_permission_manager_demotion/{workspace}_step_function_arn")
        self.auth_headers = self.get_token_to_access_github()

    def get_token_to_access_github(self):
        github_auth = GitHubAuth(self.private_key, self.app_id, self.installation_id)
        access_token = github_auth.get_access_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def get_ssm_parameter(self, parameter_name):
        parameter = self.ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        return parameter['Parameter']['Value']

    def post_comment_on_issue(self, payload, comment_body):
        print(f"Posting comment: {comment_body}")
        data = {"body": comment_body}
        try:
            response = self.requests.post(
                f"https://api.github.com/repos/{payload['repository']['full_name']}/issues/{payload['issue']['number']}/comments",
                headers=self.auth_headers,
                json=data
            )
            response.raise_for_status()
            print(f"Comment posted: {response.status_code}")
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Other error occurred: {err}")

    def make_owner_on_github(self, payload, user):
        data = {"role": "admin"}
        try:
            response = self.requests.put(
                f"https://api.github.com/orgs/{payload['organization']['login']}/memberships/{user}",
                headers=self.auth_headers,
                json=data
            )
            response.raise_for_status()
            print(f"Promoted user to Owner: {response.status_code}")
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
        except Exception as err:
            print(f"Other error occurred: {err}")

    def is_team_member(self, username, org_name, team_slug):
        team_id = self._get_team_id(org_name, team_slug)
        return self._check_membership(team_id, username) if team_id else False

    def _get_team_id(self, org_name, team_slug):
        url = f"https://api.github.com/orgs/{org_name}/teams/{team_slug}"
        response = self.requests.get(url, headers=self.auth_headers)
        if response.status_code != 200:
            print(f"Error fetching team: {response.status_code}")
            return None
        return response.json().get('id')

    def _check_membership(self, team_id, username):
        url = f"https://api.github.com/teams/{team_id}/memberships/{username}"
        response = self.requests.get(url, headers=self.auth_headers)
        if response.status_code == 200:
            print(f"User {username} is a member of the team.")
            return True
        elif response.status_code == 404:
            print(f"User {username} is not a member of the team.")
            return False
        print(f"Error checking membership: {response.status_code}")
        return False

    def request_is_from_github(self, event, headers):
        return self._is_valid_signature(event, headers)

    def _is_valid_signature(self, event, headers):
        signature = headers.get('X-Hub-Signature-256')
        if not signature:
            return False
        payload = self._get_payload(event)
        expected_signature = self._generate_signature(payload)
        return hmac.compare_digest(expected_signature, signature)

    def _get_payload(self, event):
        payload = event.get('body')
        return payload.encode('utf-8') if isinstance(payload, str) else payload

    def _generate_signature(self, payload):
        hash_object = hmac.new(self.webhook_secret.encode('utf-8'), msg=payload, digestmod=hashlib.sha256)
        return "sha256=" + hash_object.hexdigest()

    def _parse_payload(self, payload):
        return json.loads(payload) if isinstance(payload, str) else payload

    def handle_issue(self, payload):
        payload = self._parse_payload(payload)
        if self._is_elevation_request(payload):
            issue = payload['issue']
            user = issue['user']['login']
            if self._is_user_eligible_for_elevation(user, payload):
                self._process_elevation_request(payload, issue, user)
            else:
                self._notify_ineligible_user(payload, user)

    def _is_elevation_request(self, payload):
        return payload['action'] == 'opened' and request_is_to_elevate_access(payload['issue'])

    def _is_user_eligible_for_elevation(self, user, payload):
        return self.is_team_member(user, payload['repository']['owner']['login'], ESCALATION_TEAM_NAME)

    def _process_elevation_request(self, payload, issue, user):
        self.insert_into_dynamodb(payload, issue, user)
        self.post_comment_on_issue(payload, f"@{user} has requested elevation. Waiting for approval.")

    def _notify_ineligible_user(self, payload, user):
        self.post_comment_on_issue(payload, f"@{user} has requested elevation but is not a member of the elevators team.")

    def insert_into_dynamodb(self, payload, issue, user):
        table = self.dynamodb.Table('GithubElevationRequests')
        table.put_item(Item={
            'user': user,
            'issue_number': issue['number'],
            'repo': payload['repository']['full_name'],
            'status': 'pending',
            'requested_at': datetime.now().isoformat()
        })

    def handle_issue_comment(self, payload):
        payload = self._parse_payload(payload)
        if payload['action'] != 'created':
            return
        comment = payload['comment']
        user = comment['user']['login']
        if self._is_comment_from_bot(user):
            return
        if not self._is_user_eligible_for_elevation(user, payload):
            self.post_comment_on_issue(payload, f"@{user} has commented on the elevation request but is not a member of the elevators team.")
            return
        if comment_contains_approval(comment):
            self._handle_approval_comment(payload, user)
        else:
            self.post_comment_on_issue(payload, f"@{user} has commented but not approved the elevation.")

    def _is_comment_from_bot(self, user):
        return user == ELEVATION_BOT

    def _handle_approval_comment(self, payload, user):
        original_requestor = payload['issue']['user']['login']
        self.post_comment_on_issue(payload, f"@{user} has approved the elevation for @{original_requestor}.")
        if approving_own_request(user, original_requestor):
            self.post_comment_on_issue(payload, f"@{user} cannot approve own requests.")
            return
        self.promote_user_to_owner(payload, original_requestor)

    def promote_user_to_owner(self, payload, user):
        print(f"Promoting user {user} to owner.")
        most_recent_request = self.get_most_recent_request(user)
        if not most_recent_request:
            print(f"User {user} not found in the database.")
            return
        requested_at_value = most_recent_request.get('requested_at', None)
        self.make_owner_on_github(payload, user)
        self.update_user_status(user, requested_at_value)
        self.schedule_demotion(payload, user)

    def get_most_recent_request(self, user):
        table = self.dynamodb.Table('GithubElevationRequests')
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user').eq(user),
            ScanIndexForward=False,
        )
        items = response.get('Items', [])
        return items[0] if items else None

    def update_user_status(self, user, requested_at_value):
        table = self.dynamodb.Table('GithubElevationRequests')
        table.update_item(
            Key={'user': user, 'requested_at': requested_at_value},
            UpdateExpression="set #status = :s, elevated_at = :t",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':s': 'elevated',
                ':t': datetime.now().isoformat()
            }
        )

    def schedule_demotion(self, payload, user):
        elevation_duration = int(os.environ['ELEVATION_DURATION'])  # in seconds
        self.step_functions.start_execution(
            stateMachineArn=self.step_function_arn,
            input=json.dumps({
                'user': user,
                'installation_id': payload['installation']['id'],
                'organization': payload['organization']['login'],
                'repository': payload['repository']['full_name'],
                'issue_number': payload['issue']['number'],
                'wait_seconds': elevation_duration
            })
        )

    # Main handler method
    def main(self, event, _context):
        self.initialise_aws_clients()
        self.get_all_parameters()
        headers = get_headers_from_event(event)
        if not self.request_is_from_github(event, headers):
            print("Request is not from GitHub or is invalid returning 403")
            return {'statusCode': 403, 'body': json.dumps({'response': 'no'})}

        github_event = headers.get('X-GitHub-Event', None)
        print("Github event: ", github_event)
        if github_event == 'issues':
            self.handle_issue(event.get('body'))
        elif github_event == 'issue_comment':
            self.handle_issue_comment(event.get('body'))

        return {'statusCode': 200, 'body': json.dumps({'response': 'yes'})}

def handler(event, context):
    github_permission_manager = GitHubPermissionManager()
    response = github_permission_manager.main(event, context)
    return response
