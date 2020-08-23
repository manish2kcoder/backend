import functools
import logging

from boto3.dynamodb.conditions import Key

logger = logging.getLogger()


class MatchDynamo:
    def __init__(self, dynamo_client):
        self.client = dynamo_client

    def pk(self, liked_by_user_id, post_id):
        return {'partitionKey': f'post/{post_id}', 'sortKey': f'like/{liked_by_user_id}'}

    def parse_pk(self, pk):
        if pk['sortKey'] == '-':
            _, liked_by_user_id, post_id = pk['partitionKey'].split('/')
        else:
            _, post_id = pk['partitionKey'].split('/')
            _, liked_by_user_id = pk['sortKey'].split('/')
        return liked_by_user_id, post_id

    """Get users who is common with this user in likes. i.e. both liked each other's posts"""
    def get_common_likes(self, liked_by_user_id):
        query_kwargs = {
            'KeyConditionExpression': Key('gsiA1PartitionKey').eq(f'like/{liked_by_user_id}'),
            'IndexName': 'GSI-A1',
        }
        liked_users = self.client.generate_all_query(query_kwargs)
        matches = []
        for liked_user in liked_users:
            if(liked_user["likedByUserId"] == liked_by_user_id):
                matches.append(liked_user)
        return matches
