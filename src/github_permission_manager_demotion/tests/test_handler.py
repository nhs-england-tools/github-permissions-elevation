import pytest
from github_permission_manager_demotion.handler import is_last_org_owner

def test_is_last_org_owner():
    all_owners = ['test-user']
    user = 'test-user'
    assert is_last_org_owner(all_owners, user) == True

def test_is_not_last_org_owner():
    all_owners = ['test-user', 'another-user']
    user = 'test-user'
    assert is_last_org_owner(all_owners, user) == False

def test_is_not_in_list_org_owners():
    all_owners = ['another-user']
    user = 'test-user'
    assert is_last_org_owner(all_owners, user) == False

def test_empty_list_org_owners():
    all_owners = []
    user = 'test-user'
    assert is_last_org_owner(all_owners, user) == False

def test_user_is_none():
    all_owners = ['test-user']
    user = None
    assert is_last_org_owner(all_owners, user) == False

def test_list_org_owners_is_none():
    all_owners = [None]
    user = 'test-user'
    assert is_last_org_owner(all_owners, user) == False

def test_list_org_owners_is_multiple_none():
    all_owners = [None, None]
    user = 'test-user'
    assert is_last_org_owner(all_owners, user) == False

def test_list_org_owners_is_user_and_none():
    all_owners = ['test-user', None]
    user = 'test-user'
    assert is_last_org_owner(all_owners, user) == False

def test_list_org_owners_is_multiple_users():
    all_owners = ['test-user', 'another-user']
    user = 'another-user'
    assert is_last_org_owner(all_owners, user) == False
