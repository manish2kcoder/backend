from unittest.mock import Mock, call
from uuid import uuid4

import pendulum
import pytest

from app.models.post.enums import PostType


@pytest.fixture
def user(user_manager, cognito_client):
    user_id, username = str(uuid4()), str(uuid4())[:8]
    cognito_client.create_verified_user_pool_entry(user_id, username, f'{username}@real.app')
    yield user_manager.create_cognito_only_user(user_id, username)


user2 = user


@pytest.fixture
def post(post_manager, user):
    yield post_manager.add_post(user, str(uuid4()), PostType.TEXT_ONLY, text='go go')


@pytest.fixture
def comment(comment_manager, post, user2):
    yield comment_manager.add_comment(str(uuid4()), post.id, user2.id, 'lore ipsum')


def test_postprocess_record(comment_manager, comment, post, user2, user):
    typed_pk = comment.dynamo.typed_pk(comment.id)
    pk, sk = typed_pk['partitionKey']['S'], typed_pk['sortKey']['S']
    commented_at = pendulum.parse(comment.item['commentedAt'])

    # simulate a new comment, verify calls
    old_item = None
    new_item = comment.dynamo.client.get_typed_item(typed_pk)
    comment_manager.post_manager = Mock(comment_manager.post_manager)
    comment_manager.postprocess_record(pk, sk, old_item, new_item)
    assert comment_manager.post_manager.mock_calls == [
        call.postprocess_comment_added(post.id, user2.id, commented_at)
    ]

    # simulate a editing a comment, verify no calls
    old_item = new_item
    new_item = comment.dynamo.client.get_typed_item(typed_pk)
    comment_manager.post_manager = Mock(comment_manager.post_manager)
    comment_manager.postprocess_record(pk, sk, old_item, new_item)
    assert comment_manager.post_manager.mock_calls == []

    # simulate a deleteing a comment, verify calls
    old_item = new_item
    new_item = None
    comment_manager.post_manager = Mock(comment_manager.post_manager)
    comment_manager.postprocess_record(pk, sk, old_item, new_item)
    assert comment_manager.post_manager.mock_calls == [
        call.postprocess_comment_deleted(post.id, comment.id, user2.id, commented_at)
    ]

    # simulate a comment view, verify calls
    comment.record_view_count(user.id, 1)
    typed_pk = comment.view_dynamo.typed_pk(comment.id, user.id)
    pk, sk = typed_pk['partitionKey']['S'], typed_pk['sortKey']['S']
    old_item = None
    new_item = comment.dynamo.client.get_typed_item(typed_pk)
    comment_manager.post_manager = Mock(comment_manager.post_manager)
    comment_manager.postprocess_record(pk, sk, old_item, new_item)
    assert comment_manager.post_manager.mock_calls == [call.postprocess_comment_view_added(post.id, user.id)]