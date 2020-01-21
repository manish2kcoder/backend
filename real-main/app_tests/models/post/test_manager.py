from datetime import datetime, timedelta

import botocore
import pytest
from isodate.duration import Duration

from app.models.media.enums import MediaStatus
from app.models.post.enums import PostStatus


@pytest.fixture
def posts(post_manager, user_manager):
    user = user_manager.create_cognito_only_user('pbuid', 'pbUname')
    post1 = post_manager.add_post(user.id, 'pid1', text='t')
    post2 = post_manager.add_post(user.id, 'pid2', text='t')
    yield (post1, post2)


def test_get_post(post_manager, user_manager):
    # create a post behind the scenes
    post_id = 'pid'
    user = user_manager.create_cognito_only_user('pbuid', 'pbUname')
    post_manager.add_post(user.id, post_id, text='t')

    post = post_manager.get_post(post_id)
    assert post.id == post_id


def test_get_post_dne(post_manager):
    assert post_manager.get_post('pid-dne') is None


def test_add_post_errors(post_manager):
    # try to add a post without any content (no text or media)
    with pytest.raises(post_manager.exceptions.PostException) as error_info:
        post_manager.add_post('pbuid', 'pid')
    assert 'pbuid' in str(error_info.value)
    assert 'pid' in str(error_info.value)
    assert 'without text or media' in str(error_info.value)

    # try to add a post with a negative lifetime value
    with pytest.raises(post_manager.exceptions.PostException) as error_info:
        post_manager.add_post('pbuid', 'pid', text='t', lifetime_duration=Duration(hours=-1))
    assert 'pbuid' in str(error_info.value)
    assert 'pid' in str(error_info.value)
    assert 'negative lifetime' in str(error_info.value)

    # try to add a post with a zero lifetime value
    # note that isodate parses a parses the iso duration string P0D to timedelta(0),
    # not one of their duration objects
    with pytest.raises(post_manager.exceptions.PostException) as error_info:
        post_manager.add_post('pbuid', 'pid', text='t', lifetime_duration=timedelta(0))
    assert 'pbuid' in str(error_info.value)
    assert 'pid' in str(error_info.value)
    assert 'negative lifetime' in str(error_info.value)


def test_add_text_only_post(post_manager, user_manager):
    user_id = 'pbuid'
    post_id = 'pid'
    text = 'lore ipsum'
    now = datetime.utcnow()

    # add the post
    user_manager.create_cognito_only_user(user_id, 'pbUname')
    post_manager.add_post(user_id, post_id, text=text, now=now)

    # retrieve the post & media, check it
    post = post_manager.get_post(post_id)
    assert post.id == post_id
    assert post.item['postedByUserId'] == user_id
    assert post.item['postedAt'] == now.isoformat() + 'Z'
    assert post.item['text'] == 'lore ipsum'
    assert post.item['postStatus'] == PostStatus.COMPLETED
    assert 'expiresAt' not in post.item
    assert list(post_manager.media_dynamo.generate_by_post(post_id)) == []


def test_add_media_post(post_manager):
    user_id = 'pbuid'
    post_id = 'pid'
    text = 'lore ipsum'
    now = datetime.utcnow()
    media_id = 'mid'
    media_type = 'mtype'
    media_upload = {
        'mediaId': media_id,
        'mediaType': media_type,
    }

    # add the post (& media)
    post_manager.add_post(user_id, post_id, text=text, now=now, media_uploads=[media_upload])

    # retrieve the post & media, check it
    post = post_manager.get_post(post_id)
    assert post.id == post_id
    assert post.item['postedByUserId'] == user_id
    assert post.item['postedAt'] == now.isoformat() + 'Z'
    assert post.item['text'] == 'lore ipsum'
    assert post.item['postStatus'] == PostStatus.PENDING
    assert 'expiresAt' not in post.item

    media_items = list(post_manager.media_dynamo.generate_by_post(post_id))
    assert len(media_items) == 1
    assert media_items[0]['mediaId'] == media_id
    assert media_items[0]['mediaType'] == media_type
    assert media_items[0]['postedAt'] == now.isoformat() + 'Z'
    assert media_items[0]['mediaStatus'] == MediaStatus.AWAITING_UPLOAD
    assert 'expiresAt' not in media_items[0]


def test_add_media_post_with_options(post_manager):
    user_id = 'pbuid'
    post_id = 'pid'
    text = 'lore ipsum'
    now = datetime.utcnow()
    media_id = 'mid'
    media_type = 'mtype'
    media_upload = {
        'mediaId': media_id,
        'mediaType': media_type,
        'takenInReal': False,
        'originalFormat': 'org-format',
    }
    lifetime_duration = Duration(hours=1)

    # add the post (& media)
    post_manager.add_post(
        user_id, post_id, text=text, now=now, media_uploads=[media_upload], lifetime_duration=lifetime_duration,
        comments_disabled=False, likes_disabled=True, verification_hidden=False,
    )
    expires_at = now + lifetime_duration

    # retrieve the post & media, check it
    post = post_manager.get_post(post_id)
    assert post.id == post_id
    assert post.item['postedByUserId'] == user_id
    assert post.item['postedAt'] == now.isoformat() + 'Z'
    assert post.item['text'] == 'lore ipsum'
    assert post.item['postStatus'] == PostStatus.PENDING
    assert post.item['expiresAt'] == expires_at.isoformat() + 'Z'
    assert post.item['commentsDisabled'] is False
    assert post.item['likesDisabled'] is True
    assert post.item['verificationHidden'] is False

    media_items = list(post_manager.media_dynamo.generate_by_post(post_id))
    assert len(media_items) == 1
    assert media_items[0]['mediaId'] == media_id
    assert media_items[0]['mediaType'] == media_type
    assert media_items[0]['postedAt'] == now.isoformat() + 'Z'
    assert media_items[0]['mediaStatus'] == MediaStatus.AWAITING_UPLOAD
    assert media_items[0]['takenInReal'] is False
    assert media_items[0]['originalFormat'] == 'org-format'


def test_generate_posts_flagged_by_user(post_manager, posts):
    post1, post2 = posts
    our_user_id = 'uid-our'

    # check with no flagged posts
    resp = list(post_manager.generate_posts_flagged_by_user(our_user_id))
    assert resp == []

    # add a post and flag it behind the scenes
    post_manager.dynamo.add_flag_and_increment_flag_count(post1.id, our_user_id)

    # check with one flagged post
    resp = list(post_manager.generate_posts_flagged_by_user(our_user_id))
    assert len(resp) == 1
    assert resp[0].id == post1.id

    # add another post and flag it behind the scenes
    post_manager.dynamo.add_flag_and_increment_flag_count(post2.id, our_user_id)

    # check with two flagged posts
    resp = list(post_manager.generate_posts_flagged_by_user(our_user_id))
    assert len(resp) == 2
    assert resp[0].id == post1.id
    assert resp[1].id == post2.id


def test_generate_user_ids_who_flagged_post(post_manager, posts):
    post, _ = posts
    user_id_1 = 'uid-1'
    user_id_2 = 'uid-2'

    # check with no flagged posts
    resp = list(post_manager.generate_user_ids_who_flagged_post(post.id))
    assert resp == []

    # flag it
    post_manager.dynamo.add_flag_and_increment_flag_count(post.id, user_id_1)

    # check with one flag
    resp = list(post_manager.generate_user_ids_who_flagged_post(post.id))
    assert len(resp) == 1
    assert resp[0] == user_id_1

    # flag it again
    post_manager.dynamo.add_flag_and_increment_flag_count(post.id, user_id_2)

    # check with two flags
    resp = list(post_manager.generate_user_ids_who_flagged_post(post.id))
    assert len(resp) == 2
    assert resp[0] == user_id_1
    assert resp[1] == user_id_2


def test_delete_recently_expired_posts(post_manager, user_manager, caplog):
    user = user_manager.create_cognito_only_user('pbuid', 'pbUname')
    now = datetime.utcnow()

    # create four posts with diff. expiration qualities
    post_no_expires = post_manager.add_post(user.id, 'pid1', text='t')
    assert 'expiresAt' not in post_no_expires.item

    post_future_expires = post_manager.add_post(user.id, 'pid2', text='t', lifetime_duration=Duration(hours=1))
    assert post_future_expires.item['expiresAt'] > now.isoformat() + 'Z'

    post_expired_today = post_manager.add_post(user.id, 'pid3', text='t', lifetime_duration=Duration(hours=1),
                                               now=(now - Duration(hours=2)))
    assert post_expired_today.item['expiresAt'] < now.isoformat() + 'Z'
    assert post_expired_today.item['expiresAt'] > (now - Duration(hours=24)).isoformat() + 'Z'

    post_expired_last_week = post_manager.add_post(user.id, 'pid4', text='t', lifetime_duration=Duration(hours=1),
                                                   now=(now - Duration(days=7)))
    assert post_expired_last_week.item['expiresAt'] < (now - Duration(days=6)).isoformat() + 'Z'

    # run the deletion run
    post_manager.delete_recently_expired_posts(now=now)

    # check we logged one delete
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert 'Deleting' in caplog.records[0].msg
    assert post_expired_today.id in caplog.records[0].msg

    # check one of the posts is missing from the DB, but the rest are still there
    assert post_no_expires.refresh_item().item
    assert post_future_expires.refresh_item().item
    assert post_expired_today.refresh_item().item is None
    assert post_expired_last_week.refresh_item().item


@pytest.mark.xfail(raises=botocore.exceptions.ClientError, reason='Moto cant handle the scan filter expression')
def test_delete_older_expired_posts(post_manager, user_manager, caplog):
    user = user_manager.create_cognito_only_user('pbuid', 'pbUname')
    now = datetime.utcnow()

    # create four posts with diff. expiration qualities
    post_no_expires = post_manager.add_post(user.id, 'pid1', text='t')
    assert 'expiresAt' not in post_no_expires.item

    post_future_expires = post_manager.add_post(user.id, 'pid2', text='t', lifetime_duration=Duration(hours=1))
    assert post_future_expires.item['expiresAt'] > now.isoformat() + 'Z'

    post_expired_today = post_manager.add_post(user.id, 'pid3', text='t', lifetime_duration=Duration(hours=1),
                                               now=(now - Duration(hours=2)))
    assert post_expired_today.item['expiresAt'] < now.isoformat() + 'Z'
    assert post_expired_today.item['expiresAt'] > (now - Duration(hours=24)).isoformat() + 'Z'

    post_expired_last_week = post_manager.add_post(user.id, 'pid4', text='t', lifetime_duration=Duration(hours=1),
                                                   now=(now - Duration(days=7)))
    assert post_expired_last_week.item['expiresAt'] < (now - Duration(days=6)).isoformat() + 'Z'

    # run the deletion run
    post_manager.delete_older_expired_posts(now=now)

    # check we logged one delete
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert 'Deleting' in caplog.records[0].msg
    assert post_expired_last_week.id in caplog.records[0].msg

    # check one of the posts is missing from the DB, but the rest are still there
    assert post_no_expires.refresh_item().item
    assert post_future_expires.refresh_item().item
    assert post_expired_today.refresh_item().item
    assert post_expired_last_week.refresh_item().item is None
