import logging

from app import models
from .dynamo import MatchDynamo

logger = logging.getLogger()


class MatchManager:
    def __init__(self, clients, managers=None):
        managers = managers or {}
        managers['match'] = self
        self.follower_manager = managers.get('follower') or models.FollowerManager(clients, managers=managers)
        self.clients = clients
        if 'dynamo' in clients:
            self.dynamo = MatchDynamo(clients['dynamo'])

    """ All users not in contact list and with mutual friends should ideally be potential matches """

    def get_potential_matches(self, user_id):
        potential_matches = []
        # This user's followers list
        this_user_followers = self.follower_manager.generate_follower_user_ids(user_id)
        if this_user_followers:
            for followed_user_id in this_user_followers:
                # Followers of follower
                followed_user_followers = self.follower_manager.generate_follower_user_ids(followed_user_id)
                # If follower not in original user's follower list
                for follower in followed_user_followers:
                    if follower not in this_user_followers:
                        potential_matches.append(followed_user_followers)
        return potential_matches

    """People with mutual likes"""

    def get_matches(self, user_id):
        return self.dynamo.get_common_likes(user_id)
