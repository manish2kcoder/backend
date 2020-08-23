class MatchException(Exception):
    pass


class NoMatchFound(MatchException):
    def __init__(self, user_id, post_id):
        self.user_id = user_id
        super().__init__()

    def __str__(self):
        return f'User `{self.user_id}` has no matches'
