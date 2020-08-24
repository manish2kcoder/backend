import pendulum
import pytest
from app.models.like.enums import LikeStatus
from app.models.match.dynamo import MatchDynamo


def match_dynamo(dynamo_client):
    yield MatchDynamo(dynamo_client)


@pytest.fixture
def test_parse_pk(match_dynamo):
    pk = {
        'partitionKey': 'like/lbuid/pid',
        'sortKey': '-',
    }
    liked_by_user_id, post_id = match_dynamo.parse_pk(pk)
    assert liked_by_user_id == 'lbuid'
    assert post_id == 'pid'


@pytest.fixture
def test_get_common_likes(like_dynamo, match_dynamo):
    generate_test_data(like_dynamo)
    matches = match_dynamo.get_common_likes('lbuid')
    assert matches is None
    assert len(matches) == 1


def generate_test_data(like_dynamo):
    # lbuid likes pbuid
    liked_by_user_id = 'lbuid'
    like_status = LikeStatus.ONYMOUSLY_LIKED
    post_id = 'pid'
    post_item = {
        'postId': post_id,
        'postedByUserId': 'pbuid',
    }

    # verify no already in db
    assert like_dynamo.get_like(liked_by_user_id, post_id) is None

    # add the like to the DB
    now = pendulum.now('utc')
    like_dynamo.add_like(liked_by_user_id, post_item, like_status, now=now)

    # verify it exists and has the correct format
    like_item = like_dynamo.get_like(liked_by_user_id, post_id)
    liked_at_str = now.to_iso8601_string()
    assert like_item == {
        'schemaVersion': 1,
        'partitionKey': 'post/pid',
        'sortKey': 'like/luid',
        'gsiA1PartitionKey': 'like/luid',
        'gsiA1SortKey': 'ONYMOUSLY_LIKED/' + liked_at_str,
        'gsiA2PartitionKey': 'like/pid',
        'gsiA2SortKey': 'ONYMOUSLY_LIKED/' + liked_at_str,
        'gsiK2PartitionKey': 'like/pbuid',
        'gsiK2SortKey': 'luid',
        'likedByUserId': 'luid',
        'likeStatus': 'ONYMOUSLY_LIKED',
        'likedAt': liked_at_str,
        'postId': 'pid',
    }
    # pbuid likes lbuid
    liked_by_user_id = 'pbuid'
    like_status = LikeStatus.ONYMOUSLY_LIKED
    post_id = 'pid'
    post_item = {
        'postId': post_id,
        'postedByUserId': 'lbuid',
    }

    # verify no already in db
    assert like_dynamo.get_like(liked_by_user_id, post_id) is None

    # add the like to the DB
    now = pendulum.now('utc')
    like_dynamo.add_like(liked_by_user_id, post_item, like_status, now=now)

    # verify it exists and has the correct format
    like_item = like_dynamo.get_like(liked_by_user_id, post_id)
    liked_at_str = now.to_iso8601_string()
    assert like_item == {
        'schemaVersion': 1,
        'partitionKey': 'post/pid',
        'sortKey': 'like/luid',
        'gsiA1PartitionKey': 'like/luid',
        'gsiA1SortKey': 'ONYMOUSLY_LIKED/' + liked_at_str,
        'gsiA2PartitionKey': 'like/pid',
        'gsiA2SortKey': 'ONYMOUSLY_LIKED/' + liked_at_str,
        'gsiK2PartitionKey': 'like/pbuid',
        'gsiK2SortKey': 'luid',
        'likedByUserId': 'luid',
        'likeStatus': 'ONYMOUSLY_LIKED',
        'likedAt': liked_at_str,
        'postId': 'pid',
    }
