import re

def get_headers_from_event(event):
    return event.get('headers', {}) or event.get('Headers', {})

def request_is_to_elevate_access(issue):
    keywords = ['request', 'elevate', 'elevation']
    title = issue.get('title', '')
    body = issue.get('body', '')
    pattern = re.compile('|'.join(keywords), re.IGNORECASE)
    return bool(pattern.search(title) or pattern.search(body))

def comment_contains_approval(comment):
    pattern = re.compile(r'approve|👍', re.IGNORECASE)
    return bool(pattern.search(comment['body']))

def approving_own_request(user, original_requestor):
    return user == original_requestor