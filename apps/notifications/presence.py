"""User presence tracking via cache."""
from django.core.cache import cache


def is_online(user_id):
    return bool(cache.get(f'presence_user_{user_id}'))


def online_users(user_ids):
    """Return set of user IDs that are online."""
    result = set()
    for uid in user_ids:
        if is_online(uid):
            result.add(uid)
    return result