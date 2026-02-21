from datetime import datetime

COL_GNH = "gnh_sheet"
COL_SYNC_LOG = "gnh_sync_logs"
COL_API_TOKEN = "api_tokens"

GNH_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"

GNH_FIELDS = [
    "MA_GIAO_NHAN",
    "TEN_KHACH_HANG",
    "SO_DIEN_THOAI",
    "MA_CAN_HO",
    "THU_HOI",
    "MA_GIAO_HANG",
    "MA_KHO",
    "VI_TRI",
    "NGAY_NHAN",
    "NGAY_GIAO",
    "GIA_TIEN",
    "HINH_NHAN",
    "HINH_GIAO",
    "NOI_DUNG_GOI_HANG",
    "GIAO_HANG",
    "TINH_TRANG",
    "GIO_NHAN",
    "GIO_GIAO",
    "GHI_CHU",
    "LOAI_VE",
    "HTTT",
    "UPDATED_AT",
]


def utcnow() -> datetime:
    return datetime.utcnow()
