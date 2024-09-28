import json
import boto3
import requests
from datetime import datetime
from common.shared_functions import GitHubAuth, DEFAULT_REGION

def is_last_org_owner(all_owners, user):
    if len(all_owners) == 1:
        if user in all_owners:
            return True
    return False

class GitHubPermissionRemover:
    def __init__(self, requests_module=requests):
        self.dynamodb = None
        self.ssm_client = None
        self.app_id = None
        self.private_key = None
        self.installation_id = None
        self.auth_headers = None
        self.requests = requests_module

    def initialise_aws_clients(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=DEFAULT_REGION)
        self.ssm_client = boto3.client('ssm', region_name=DEFAULT_REGION)
    
    def get_all_parameters(self):
        self.app_id = self.get_ssm_parameter('/github_permission_manager_webhook/app_id')
        self.private_key = self.get_ssm_parameter('/github_permission_manager_webhook/private_key')
        self.installation_id = self.get_ssm_parameter('/github_permission_manager_webhook/installation_id')
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

    def close_issue(self, repository, issue_number):
        response = self.requests.patch(
            f"https://api.github.com/repos/{repository}/issues/{issue_number}",
            headers=self.auth_headers,
            json={"state": "closed"}
        )
        print(f"Issue closed: {response.status_code}")

    def post_comment_on_issue(self, repository, issue_number, comment_body):
        data = {
            "body": comment_body
        }
        response = requests.post(
            f"https://api.github.com/repos/{repository}/issues/{issue_number}/comments",
            headers=self.auth_headers,
            json=data
        )
        print(f"Comment posted: {response.status_code}")

    def get_all_org_owners(self, organization):
        response = requests.get(
            f"https://api.github.com/orgs/{organization}/members?role=admin",
            headers=self.auth_headers
        )
        print(f"Request to get org owners: {response.status_code}")
        org_owners = []
        for owner in response.json():
            print(f"Owner: {owner['login']}")
            org_owners.append(owner['login'])
        return org_owners


    def make_member_on_github(self, organization, user):
        data = {
            "role": "member"
        }
        response = requests.put(
            f"https://api.github.com/orgs/{organization}/memberships/{user}",
            headers=self.auth_headers,
            json=data
        )
        print(f"Comment posted: {response.status_code}")

    def demote_user_lambda(self, event, _context):
        self.initialise_aws_clients()
        self.get_all_parameters()
        organization = event.get('organization')
        user = event.get('user')
        repository = event.get('repository')
        issue_number = event.get('issue_number')
        org_owners = self.get_all_org_owners(organization)
        if user in org_owners:
            if is_last_org_owner(org_owners, user):
                self.post_comment_on_issue(repository, issue_number, "User is the last owner - therefore will not be demoted")
                self.close_issue(repository, issue_number)
                return
            self.post_comment_on_issue(repository, issue_number, "User is currently an owner - demotion to member in progress")
            self.make_member_on_github(organization, user)
            self.post_comment_on_issue(repository, issue_number, "User has been demoted")
            self.close_issue(repository, issue_number)

            table = self.dynamodb.Table('GithubElevationRequests')
            
            # Update DynamoDB
            table.update_item(
                Key={'user': user},
                UpdateExpression="set #status = :s, demoted_at = :t",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':s': 'demoted',
                    ':t': datetime.now().isoformat()
                }
            )

def handler(event, context):
    github_permission_remover = GitHubPermissionRemover()
    github_permission_remover.demote_user_lambda(event, context)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'User demoted'})
    }