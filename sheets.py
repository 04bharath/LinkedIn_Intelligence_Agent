"""
sheets.py  –  Google Sheets Output Layer
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_CREDS_FILE, GOOGLE_SHEET_NAME

COLUMNS = [
    "post_id", "role", "company_name", "location",
    "primary_skills", "secondary_skills", "must_to_have",
    "years_of_experience", "looking_for_college_students", "intern",
    "salary_package", "email", "phone", "hiring_intent",
    "author_name", "author_linkedin_url", "post_url", "date_posted",
    "keyword_matched", "date_processed",
]

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

_sheet_cache    = None
_spreadsheet_cache = None


def _get_spreadsheet():
    global _sheet_cache, _spreadsheet_cache
    if _spreadsheet_cache is not None:
        return _spreadsheet_cache
    creds  = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, _SCOPES)
    client = gspread.authorize(creds)
    _spreadsheet_cache = client.open(GOOGLE_SHEET_NAME)
    _sheet_cache = _spreadsheet_cache.sheet1
    return _spreadsheet_cache


def _get_sheet():
    global _sheet_cache
    if _sheet_cache is not None:
        return _sheet_cache
    _get_spreadsheet()
    return _sheet_cache


def get_sheet_url() -> str:
    """Return the public URL of the Google Sheet."""
    try:
        sp = _get_spreadsheet()
        print("Sheet URL:", sp.url)   # debug
        return sp.url
    except Exception as e:
        print("❌ Sheets Error:", e)
        return ""


def ensure_headers() -> None:
    sheet = _get_sheet()
    if not sheet.row_values(1):
        sheet.append_row(COLUMNS)
        print("[sheets] Header row written.")


def save_to_sheet(job: dict) -> None:
    sheet = _get_sheet()
    row = []
    for col in COLUMNS:
        val = job.get(col, "Not specified")
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val)
        row.append(str(val))
    sheet.append_row(row)


def save_many(jobs: list) -> int:
    for job in jobs:
        save_to_sheet(job)
    return len(jobs)