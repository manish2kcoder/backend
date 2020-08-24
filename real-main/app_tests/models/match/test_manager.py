import uuid

import pytest

from app.models.like.enums import LikeStatus
from app.models.post.enums import PostType
from app.models.match.manager import MatchManager
from app_tests.conftest import user_manager,cognito_client,post_manager,like_manager

FIRST_USER_ID = ''
SECOND_USER_ID = ''

@pytest.fixture
def test_get_potential_matches(user_manager,cognito_client,like_manager,post_manager):
    generate_test_data_potential_match(user_manager,cognito_client,like_manager,post_manager)
    matcher = MatchManager()
    potential_matches = matcher.get_potential_matches(FIRST_USER_ID)
    assert potential_matches is not None
    assert len(potential_matches) == 1

@pytest.fixture
def test_get_matches(user_manager,cognito_client,like_manager,post_manager):
    generate_test_data_match(user_manager,cognito_client,like_manager,post_manager)
    matcher = MatchManager()
    matches = matcher.get_matches(FIRST_USER_ID)
    assert matches is not None
    assert len(matches) == 1


# Creates 2 users, posts from both and likes second's post from first id
def generate_test_data_potential_match(user_manager,cognito_client,like_manager,post_manager):
    first_user = user1(user_manager,cognito_client)
    first_user_post = user1_posts(post_manager,first_user)
    second_user = user1(user_manager,cognito_client)
    second_user_post = user2_posts(post_manager,second_user)
    like_post(like_manager,first_user,second_user,second_user_post)


# Creates 2 users, posts from both and likes each other's posts
def generate_test_data_match(user_manager,cognito_client,like_manager,post_manager):
    first_user = user1(user_manager,cognito_client)
    first_user_post = user1_posts(post_manager,first_user)
    second_user = user2(user_manager,cognito_client)
    second_user_post = user2_posts(post_manager,second_user)
    like_post(like_manager,first_user,second_user,second_user_post)
    like_post(like_manager, second_user, first_user, first_user_post)

def user1(user_manager, cognito_client):
    FIRST_USER_ID = uuid.uuid4()
    user_id, username = str(FIRST_USER_ID), str(FIRST_USER_ID)[:8]
    cognito_client.create_verified_user_pool_entry(user_id, username, f'{username}@real.app')
    return user_manager.create_cognito_only_user(user_id, username)

def user1_posts(post_manager, user1):
    post1 = post_manager.add_post(user1, 'pid1', PostType.TEXT_ONLY, text='lore ipsum')
    post2 = post_manager.add_post(user1, 'pid2', PostType.TEXT_ONLY, text='lore ipsum')
    return (post1, post2)

def user2(user_manager, cognito_client):
    SECOND_USER_ID = uuid.uuid4()
    user_id, username = str(SECOND_USER_ID), str(SECOND_USER_ID)[:8]
    cognito_client.create_verified_user_pool_entry(user_id, username, f'{username}@real.app')
    return user_manager.create_cognito_only_user(user_id, username)

def user2_posts(post_manager, user2):
    post1 = post_manager.add_post(user2, 'pid3', PostType.TEXT_ONLY, text='lore ipsum')
    post2 = post_manager.add_post(user2, 'pid4', PostType.TEXT_ONLY, text='lore ipsum')
    return (post1, post2)


def like_post(like_manager, user1, user2, user2_posts):
    # verify initial state
    post, _ = user2_posts
    assert like_manager.get_like(user1.id, post.id) is None
    assert like_manager.get_like(user2.id, post.id) is None

    # like post
    like_manager.like_post(user1, post, LikeStatus.ONYMOUSLY_LIKED)
    like = like_manager.get_like(user1.id, post.id)

    # like post the other way
    like_manager.like_post(user2, post, LikeStatus.ONYMOUSLY_LIKED)
    like = like_manager.get_like(user2.id, post.id)
