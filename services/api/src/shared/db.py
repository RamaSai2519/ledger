import pymongo

from shared.configs import CONFIG

_client = None


def get_db():
    global _client
    if _client is None:
        _client = pymongo.MongoClient(CONFIG["mongo_uri"])
    return _client[CONFIG["mongo_db_name"]]


def get_users_collection():
    return get_db()["users"]


def get_households_collection():
    return get_db()["households"]


def get_categories_collection():
    return get_db()["categories"]


def get_wallets_collection():
    return get_db()["wallets"]


def get_transactions_collection():
    return get_db()["transactions"]


def get_revoked_tokens_collection():
    return get_db()["revoked_tokens"]


def get_budgets_collection():
    return get_db()["budgets"]


def get_notifications_collection():
    return get_db()["notifications"]


def get_net_worth_snapshots_collection():
    return get_db()["net_worth_snapshots"]


def get_sms_inbox_collection():
    return get_db()["sms_inbox"]


def get_sms_parser_rules_collection():
    return get_db()["sms_parser_rules"]


def get_merchant_category_map_collection():
    return get_db()["merchant_category_map"]


def get_client():
    # Ensures the client is initialized, then returns it directly for
    # session/transaction use (start_session lives on the client, not the db).
    get_db()
    return _client
