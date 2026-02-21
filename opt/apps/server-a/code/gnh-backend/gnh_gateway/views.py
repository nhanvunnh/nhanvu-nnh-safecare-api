from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from gnh_gateway.auth import require_auth
from gnh_gateway.models import COL_GNH, COL_SYNC_LOG, GNH_FIELDS, utcnow
from gnh_gateway.mongo import get_collection
from gnh_gateway.sheet_sync_client import SheetSyncError, fetch_sheet_logs, run_sheet_sync
from gnh_gateway.utils import fmt_dt, get_param, has_param, normalize_doc, parse_int, parse_row_sort_dt, to_image_url


def error_response(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"Error": str(message)}, status=code)


def obj_response(payload):
    return Response(payload, status=status.HTTP_200_OK)


def success_response(message="Success"):
    return Response({"Success": message}, status=status.HTTP_200_OK)


def paginate(items, page, page_size, window=6):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    end = start + page_size
    sliced = items[start:end]

    start_page = max(1, page - window)
    end_page = min(total_pages, page + window)
    page_numbers = list(range(start_page, end_page + 1))

    return sliced, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "show_first": 1 not in page_numbers,
        "show_last": total_pages not in page_numbers,
        "show_left_ellipsis": (1 not in page_numbers) and start_page > 2,
        "show_right_ellipsis": (total_pages not in page_numbers) and end_page < total_pages - 1,
    }


def list_data(page=1, page_size=50, phone_filter=""):
    col = get_collection(COL_GNH)
    query = {}
    if phone_filter:
        query["SO_DIEN_THOAI"] = phone_filter

    records = list(col.find(query, {"_id": 0}))
    records.sort(key=parse_row_sort_dt, reverse=True)

    page_size = max(1, min(page_size, 200))
    items, meta = paginate(records, page, page_size)

    data = []
    for raw in items:
        item = normalize_doc(raw)
        item["HINH_NHAN"] = to_image_url(item.get("HINH_NHAN"))
        item["HINH_GIAO"] = to_image_url(item.get("HINH_GIAO"))
        data.append(item)

    return {
        "ok": True,
        "data": data,
        **meta,
    }


def logs_data(page=1, page_size=50, status_filter=""):
    try:
        return fetch_sheet_logs(app_code="gnh", page=page, page_size=page_size, status_filter=status_filter)
    except SheetSyncError:
        col = get_collection(COL_SYNC_LOG)
        query = {}
        if status_filter:
            query["status"] = status_filter

        items = list(col.find(query, {"_id": 0}).sort("timeCreate", -1))
        page_size = max(1, min(page_size, 200))
        sliced, meta = paginate(items, page, page_size)

        data = []
        for row in sliced:
            data.append(
                {
                    "timeCreate": fmt_dt(row.get("timeCreate")),
                    "direction": row.get("direction") or "",
                    "status": row.get("status") or "",
                    "message": row.get("message") or "",
                }
            )

        return {
            "ok": True,
            "data": data,
            **meta,
        }


class GNHListView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="read")
            page = parse_int(get_param(request, "page", 1), 1)
            page_size = parse_int(get_param(request, "page_size", 50), 50)
            phone_filter = str(get_param(request, "phone_filter", "") or "").strip()
            return obj_response(list_data(page, page_size, phone_filter))
        except Exception as exc:
            return error_response(exc)


class GNHDetailView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="read")
            key = str(get_param(request, "key", "") or "").strip()
            if not key:
                return error_response("Missing key")
            doc = get_collection(COL_GNH).find_one({"MA_GIAO_NHAN": key}, {"_id": 0})
            if not doc:
                return error_response("Not found", code=status.HTTP_404_NOT_FOUND)
            data = normalize_doc(doc)
            data["HINH_NHAN"] = to_image_url(data.get("HINH_NHAN"))
            data["HINH_GIAO"] = to_image_url(data.get("HINH_GIAO"))
            return obj_response({"ok": True, "data": data})
        except Exception as exc:
            return error_response(exc)


class GNHCreateView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="write")
            key = str(get_param(request, "MA_GIAO_NHAN", "") or "").strip()
            if not key:
                return error_response("Missing MA_GIAO_NHAN")

            col = get_collection(COL_GNH)
            if col.find_one({"MA_GIAO_NHAN": key}, {"_id": 1}):
                return error_response("MA_GIAO_NHAN already exists")

            data = {}
            for field in GNH_FIELDS:
                if field == "UPDATED_AT":
                    continue
                data[field] = get_param(request, field, "")
            data["UPDATED_AT"] = utcnow()

            col.insert_one(data)
            try:
                result = run_sheet_sync(app_code="gnh", direction="manual")
            except SheetSyncError as exc:
                result = {"ok": False, "error": str(exc)}
            return obj_response({"ok": True, "data": normalize_doc(data), "sync": result})
        except Exception as exc:
            return error_response(exc)


class GNHUpdateView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="write")
            key = str(get_param(request, "MA_GIAO_NHAN", "") or "").strip()
            if not key:
                return error_response("Missing MA_GIAO_NHAN")

            col = get_collection(COL_GNH)
            if not col.find_one({"MA_GIAO_NHAN": key}, {"_id": 1}):
                return error_response("Not found", code=status.HTTP_404_NOT_FOUND)

            update_data = {}
            for field in GNH_FIELDS:
                if field in {"MA_GIAO_NHAN", "UPDATED_AT"}:
                    continue
                if has_param(request, field):
                    update_data[field] = get_param(request, field)

            update_data["UPDATED_AT"] = utcnow()
            col.update_one({"MA_GIAO_NHAN": key}, {"$set": update_data})
            doc = col.find_one({"MA_GIAO_NHAN": key}, {"_id": 0})

            try:
                result = run_sheet_sync(app_code="gnh", direction="manual")
            except SheetSyncError as exc:
                result = {"ok": False, "error": str(exc)}
            return obj_response({"ok": True, "data": normalize_doc(doc), "sync": result})
        except Exception as exc:
            return error_response(exc)


class GNHDeleteView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="write")
            key = str(get_param(request, "MA_GIAO_NHAN", "") or "").strip()
            if not key:
                return error_response("Missing MA_GIAO_NHAN")

            col = get_collection(COL_GNH)
            result = col.delete_one({"MA_GIAO_NHAN": key})
            if result.deleted_count == 0:
                return error_response("Not found", code=status.HTTP_404_NOT_FOUND)

            try:
                sync_result = run_sheet_sync(app_code="gnh", direction="manual", delete_key=key)
                sheet_delete = {"ok": True}
            except SheetSyncError as exc:
                sheet_delete = {"ok": False, "error": str(exc)}
                sync_result = {"ok": False, "error": str(exc)}
            return obj_response({"ok": True, "deleted": key, "sheet_delete": sheet_delete, "sync": sync_result})
        except Exception as exc:
            return error_response(exc)


class GNHSyncView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="write")
            result = run_sheet_sync(app_code="gnh", direction="manual")
            return obj_response(result)
        except Exception as exc:
            return error_response(exc)


class GNHLogsView(APIView):
    def post(self, request):
        try:
            require_auth(request, required_scope="read")
            page = parse_int(get_param(request, "page", 1), 1)
            page_size = parse_int(get_param(request, "page_size", 50), 50)
            status_filter = str(get_param(request, "status", "") or "").strip()
            return obj_response(logs_data(page, page_size, status_filter))
        except Exception as exc:
            return error_response(exc)
