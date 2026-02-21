import datetime

import gspread
from django.conf import settings
from google.oauth2.service_account import Credentials

from sheet_sync_gateway.models import COL_JOB_LOGS
from sheet_sync_gateway.mongo import get_collection, get_target_collection
from sheet_sync_gateway.utils import utcnow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SyncEngine:
    def __init__(self):
        self.logs = get_collection(COL_JOB_LOGS)

    def _sheet(self, sheet_name, worksheet_name):
        creds = Credentials.from_service_account_file(settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        workbook = client.open(sheet_name)
        return workbook.worksheet(worksheet_name)

    @staticmethod
    def _normalize(value):
        return str(value or "").strip()

    def _parse_sheet_dt(self, value, date_format):
        text = self._normalize(value)
        if not text:
            return None
        try:
            local_dt = datetime.datetime.strptime(text, date_format)
            return local_dt
        except Exception:
            return None

    def _format_sheet_dt(self, value, date_format):
        if not value:
            return ""
        if isinstance(value, datetime.datetime):
            return value.strftime(date_format)
        return str(value)

    def _log(self, app_code, direction, status, message, stats=None):
        self.logs.insert_one(
            {
                "timeCreate": utcnow(),
                "app_code": app_code,
                "direction": direction,
                "status": status,
                "message": message,
                "stats": stats or {},
            }
        )

    def _ensure_header(self, ws, values, fields):
        header = values[0] if values else []
        if not header:
            ws.update("A1", [list(fields)])
            return list(fields)
        missing = [f for f in fields if f not in header]
        if missing:
            header = header + missing
            ws.update("A1", [header])
        return header

    def _row_to_dict(self, header, row):
        return {header[i]: row[i] if i < len(row) else "" for i in range(len(header))}

    def _doc_to_row(self, header, doc, updated_at_field, date_format):
        row = []
        for col in header:
            value = doc.get(col, "")
            if col == updated_at_field:
                row.append(self._format_sheet_dt(value, date_format))
            else:
                row.append(value if value is not None else "")
        return row

    def _rows_diff(self, header, row_dict, doc, updated_at_field):
        for col in header:
            if col == updated_at_field:
                continue
            if self._normalize(row_dict.get(col, "")) != self._normalize(doc.get(col, "")):
                return True
        return False

    def run_two_way(self, cfg, direction="manual", delete_key=""):
        app_code = cfg["app_code"]
        sheet_name = cfg["sheet_name"]
        worksheet_name = cfg["worksheet_name"]
        fields = cfg["fields"]
        key_field = cfg["key_field"]
        updated_at_field = cfg.get("updated_at_field", "UPDATED_AT")
        date_format = cfg.get("date_format", "%d/%m/%Y %H:%M:%S")

        col = get_target_collection(cfg["target_db"], cfg["target_collection"])
        ws = self._sheet(sheet_name, worksheet_name)
        values = ws.get_all_values()
        header = self._ensure_header(ws, values, fields)

        if not values:
            values = [header]
        if key_field not in header:
            raise Exception(f"Missing key field: {key_field}")

        if delete_key:
            key_idx = header.index(key_field)
            rows_delete = []
            for row_idx, row in enumerate(values[1:], start=2):
                cell_val = row[key_idx] if key_idx < len(row) else ""
                if self._normalize(cell_val) == self._normalize(delete_key):
                    rows_delete.append(row_idx)
            for row_idx in reversed(rows_delete):
                ws.delete_rows(row_idx)
            values = ws.get_all_values()

        sheet_map = {}
        for row_idx, row in enumerate(values[1:], start=2):
            row_dict = self._row_to_dict(header, row)
            key_val = self._normalize(row_dict.get(key_field, ""))
            if key_val:
                sheet_map[key_val] = (row_idx, row_dict)

        db_docs = list(col.find({}, {"_id": 0}))
        db_map = {self._normalize(d.get(key_field, "")): d for d in db_docs if d.get(key_field)}

        inserted_db = 0
        updated_db = 0

        now = utcnow()
        for key_val, (_, row_dict) in sheet_map.items():
            doc = db_map.get(key_val)
            sheet_updated = self._parse_sheet_dt(row_dict.get(updated_at_field), date_format)

            if not doc:
                data = {f: row_dict.get(f, "") for f in fields if f != updated_at_field}
                data[updated_at_field] = sheet_updated or now
                col.insert_one(data)
                inserted_db += 1
                db_map[key_val] = data
            else:
                db_updated = doc.get(updated_at_field)
                if (not db_updated) or (sheet_updated and sheet_updated > db_updated):
                    if self._rows_diff(header, row_dict, doc, updated_at_field):
                        update_data = {f: row_dict.get(f, "") for f in fields if f != updated_at_field}
                        update_data[updated_at_field] = sheet_updated or now
                        col.update_one({key_field: key_val}, {"$set": update_data})
                        doc.update(update_data)
                        updated_db += 1

        db_docs = list(col.find({}, {"_id": 0}))
        db_map = {self._normalize(d.get(key_field, "")): d for d in db_docs if d.get(key_field)}

        update_payload = []
        append_rows = []
        updated_sheet = 0
        appended_sheet = 0

        last_col = gspread.utils.rowcol_to_a1(1, len(header)).replace("1", "")

        for key_val, doc in db_map.items():
            if key_val not in sheet_map:
                append_rows.append(self._doc_to_row(header, doc, updated_at_field, date_format))
                appended_sheet += 1
                continue

            row_idx, row_dict = sheet_map[key_val]
            sheet_updated = self._parse_sheet_dt(row_dict.get(updated_at_field), date_format)
            db_updated = doc.get(updated_at_field)
            if (not sheet_updated) or (db_updated and db_updated > sheet_updated):
                if self._rows_diff(header, row_dict, doc, updated_at_field):
                    update_payload.append(
                        {
                            "range": f"A{row_idx}:{last_col}{row_idx}",
                            "values": [self._doc_to_row(header, doc, updated_at_field, date_format)],
                        }
                    )
                    updated_sheet += 1

        if update_payload:
            ws.batch_update({"valueInputOption": "USER_ENTERED", "data": update_payload})
        if append_rows:
            ws.append_rows(append_rows, value_input_option="USER_ENTERED")

        stats = {
            "inserted_db": inserted_db,
            "updated_db": updated_db,
            "updated_sheet": updated_sheet,
            "appended_sheet": appended_sheet,
        }
        self._log(
            app_code=app_code,
            direction=direction,
            status="success",
            message=(
                f"db_insert={inserted_db} db_update={updated_db} "
                f"sheet_update={updated_sheet} sheet_append={appended_sheet}"
            ),
            stats=stats,
        )
        return {"ok": True, **stats}
