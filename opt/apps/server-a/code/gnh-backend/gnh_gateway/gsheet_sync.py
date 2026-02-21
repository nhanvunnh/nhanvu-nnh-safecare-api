import os
from datetime import datetime

import gspread
from django.conf import settings
from google.oauth2.service_account import Credentials

from gnh_gateway.models import COL_GNH, COL_SYNC_LOG, GNH_FIELDS, utcnow
from gnh_gateway.mongo import get_collection
from gnh_gateway.utils import parse_sheet_dt

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GnhSyncService:
    def __init__(self):
        self.gnh_col = get_collection(COL_GNH)
        self.log_col = get_collection(COL_SYNC_LOG)

    def _sheet(self):
        creds = Credentials.from_service_account_file(settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        workbook = client.open(settings.GNH_SHEET_NAME)
        return workbook.worksheet(settings.GNH_WORKSHEET_NAME)

    def _ensure_header(self, ws, values):
        header = values[0] if values else []
        if not header:
            ws.update("A1", [list(GNH_FIELDS)])
            return list(GNH_FIELDS)
        missing = [f for f in GNH_FIELDS if f not in header]
        if missing:
            header = header + missing
            ws.update("A1", [header])
        return header

    @staticmethod
    def _normalize(value):
        return str(value or "").strip()

    def _row_to_dict(self, header, row):
        return {header[i]: row[i] if i < len(row) else "" for i in range(len(header))}

    def _doc_to_row(self, header, doc):
        row = []
        for col in header:
            if col == "UPDATED_AT":
                dt = doc.get("UPDATED_AT")
                row.append(dt.strftime("%d/%m/%Y %H:%M:%S") if dt else "")
            else:
                row.append(doc.get(col, "") or "")
        return row

    def _rows_diff(self, header, row_dict, doc):
        for col in header:
            if col == "UPDATED_AT":
                continue
            if self._normalize(row_dict.get(col, "")) != self._normalize(doc.get(col, "")):
                return True
        return False

    def _log(self, direction, status, message):
        self.log_col.insert_one(
            {
                "timeCreate": datetime.utcnow(),
                "direction": direction,
                "status": status,
                "message": message,
            }
        )

    def sync_two_way(self, direction="manual"):
        ws = self._sheet()
        values = ws.get_all_values()
        header = self._ensure_header(ws, values)
        if not values:
            values = [header]

        key_field = "MA_GIAO_NHAN"
        if key_field not in header:
            raise Exception(f"Missing key field {key_field}")

        sheet_map = {}
        for row_idx, row in enumerate(values[1:], start=2):
            row_dict = self._row_to_dict(header, row)
            key_val = self._normalize(row_dict.get(key_field, ""))
            if key_val:
                sheet_map[key_val] = (row_idx, row_dict)

        db_docs = list(self.gnh_col.find({}, {"_id": 0}))
        db_map = {self._normalize(d.get(key_field, "")): d for d in db_docs if d.get(key_field)}

        inserted_db = 0
        updated_db = 0

        for key_val, (_, row_dict) in sheet_map.items():
            doc = db_map.get(key_val)
            sheet_updated = parse_sheet_dt(row_dict.get("UPDATED_AT"))
            if not doc:
                data = {f: row_dict.get(f, "") for f in GNH_FIELDS if f != "UPDATED_AT"}
                data["UPDATED_AT"] = sheet_updated or utcnow()
                self.gnh_col.insert_one(data)
                inserted_db += 1
                db_map[key_val] = data
            else:
                db_updated = doc.get("UPDATED_AT")
                if (not db_updated) or (sheet_updated and sheet_updated > db_updated):
                    if self._rows_diff(header, row_dict, doc):
                        update_fields = {f: row_dict.get(f, "") for f in GNH_FIELDS if f != "UPDATED_AT"}
                        update_fields["UPDATED_AT"] = sheet_updated or utcnow()
                        self.gnh_col.update_one({"MA_GIAO_NHAN": key_val}, {"$set": update_fields})
                        doc.update(update_fields)
                        updated_db += 1

        db_docs = list(self.gnh_col.find({}, {"_id": 0}))
        db_map = {self._normalize(d.get("MA_GIAO_NHAN", "")): d for d in db_docs if d.get("MA_GIAO_NHAN")}

        update_payload = []
        append_rows = []
        updated_sheet = 0
        appended_sheet = 0

        last_col = gspread.utils.rowcol_to_a1(1, len(header)).replace("1", "")

        for key_val, doc in db_map.items():
            if key_val not in sheet_map:
                append_rows.append(self._doc_to_row(header, doc))
                appended_sheet += 1
                continue

            row_idx, row_dict = sheet_map[key_val]
            sheet_updated = parse_sheet_dt(row_dict.get("UPDATED_AT"))
            db_updated = doc.get("UPDATED_AT")
            if (not sheet_updated) or (db_updated and db_updated > sheet_updated):
                if self._rows_diff(header, row_dict, doc):
                    update_payload.append(
                        {
                            "range": f"A{row_idx}:{last_col}{row_idx}",
                            "values": [self._doc_to_row(header, doc)],
                        }
                    )
                    updated_sheet += 1

        if update_payload:
            ws.batch_update({"valueInputOption": "USER_ENTERED", "data": update_payload})
        if append_rows:
            ws.append_rows(append_rows, value_input_option="USER_ENTERED")

        result = {
            "ok": True,
            "inserted_db": inserted_db,
            "updated_db": updated_db,
            "updated_sheet": updated_sheet,
            "appended_sheet": appended_sheet,
        }
        self._log(
            direction=direction,
            status="success",
            message=(
                f"db_insert={inserted_db} db_update={updated_db} "
                f"sheet_update={updated_sheet} sheet_append={appended_sheet}"
            ),
        )
        return result

    def delete_key_from_sheet(self, key_value: str):
        key_value = self._normalize(key_value)
        if not key_value:
            return {"ok": False, "deleted_rows": 0}

        ws = self._sheet()
        values = ws.get_all_values()
        header = self._ensure_header(ws, values)
        if not values:
            return {"ok": True, "deleted_rows": 0}

        if "MA_GIAO_NHAN" not in header:
            return {"ok": False, "deleted_rows": 0}

        key_idx = header.index("MA_GIAO_NHAN")
        delete_rows = []
        for row_idx, row in enumerate(values[1:], start=2):
            cell_value = row[key_idx] if key_idx < len(row) else ""
            if self._normalize(cell_value) == key_value:
                delete_rows.append(row_idx)

        for row_idx in reversed(delete_rows):
            ws.delete_rows(row_idx)

        if delete_rows:
            self._log("manual", "success", f"sheet_delete key={key_value} count={len(delete_rows)}")
        return {"ok": True, "deleted_rows": len(delete_rows)}


def run_loop_forever(interval_seconds=30):
    svc = GnhSyncService()
    svc._log("loop", "success", "loop started")
    while True:
        try:
            svc.sync_two_way(direction="loop")
        except Exception as exc:
            svc._log("loop", "error", str(exc))
        import time

        time.sleep(max(5, int(interval_seconds)))


def service_account_exists() -> bool:
    return os.path.isfile(settings.GOOGLE_SERVICE_ACCOUNT_FILE)
