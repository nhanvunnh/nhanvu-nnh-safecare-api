from gnh_gateway.models import COL_API_TOKEN, COL_GNH, COL_SYNC_LOG
from gnh_gateway.mongo import get_collection


def create_indexes():
    gnh = get_collection(COL_GNH)
    logs = get_collection(COL_SYNC_LOG)
    tokens = get_collection(COL_API_TOKEN)

    gnh.create_index([("MA_GIAO_NHAN", 1)], unique=True, name="uniq_ma_giao_nhan")
    gnh.create_index([("SO_DIEN_THOAI", 1), ("UPDATED_AT", -1)], name="idx_phone_updated")
    gnh.create_index([("UPDATED_AT", -1)], name="idx_updated_desc")

    logs.create_index([("timeCreate", -1)], name="idx_log_time_desc")
    logs.create_index([("status", 1), ("timeCreate", -1)], name="idx_log_status_time")

    tokens.create_index([("token", 1)], unique=True, name="uniq_api_token")
    tokens.create_index([("isActive", 1), ("scope", 1)], name="idx_active_scope")
