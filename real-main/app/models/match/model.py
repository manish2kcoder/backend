import logging

logger = logging.getLogger()


class Match:
    def __init__(self, user_id, match_dynamo,):
        self.dynamo = match_dynamo
        self.liked_by_user_id = user_id
