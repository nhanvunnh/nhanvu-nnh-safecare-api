from sheet_sync_gateway.models import COL_API_TOKENS, COL_APP_CONFIGS, COL_JOB_LOGS
from sheet_sync_gateway.mongo import get_collection


def create_indexes():
    app_configs = get_collection(COL_APP_CONFIGS)
    logs = get_collection(COL_JOB_LOGS)
    tokens = get_collection(COL_API_TOKENS)

    app_configs.create_index([("app_code", 1)], unique=True, name="uniq_app_code")
    app_configs.create_index([("is_active", 1), ("app_code", 1)], name="idx_active_app")

    logs.create_index([("timeCreate", -1)], name="idx_logs_time")
    logs.create_index([("app_code", 1), ("timeCreate", -1)], name="idx_logs_app_time")
    logs.create_index([("status", 1), ("timeCreate", -1)], name="idx_logs_status_time")

    tokens.create_index([("token", 1)], unique=True, name="uniq_api_token")
    tokens.create_index([("isActive", 1), ("scope", 1)], name="idx_active_scope")
