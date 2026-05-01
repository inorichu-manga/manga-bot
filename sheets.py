import json
import os
import random
from datetime import datetime

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv(override=True)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]

MANGA_LIST_SHEET = "manga_list"
HISTORY_SHEET = "history"


def _get_service():
    # 環境変数 GOOGLE_CREDENTIALS_JSON が優先（クラウドデプロイ用）
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def get_manga_list() -> list[dict]:
    """manga_listシートの全行を取得。列順: title / quote / theme / link"""
    result = (
        _get_service()
        .spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=f"{MANGA_LIST_SHEET}!A2:D")
        .execute()
    )
    rows = result.get("values", [])
    return [
        {"title": r[0], "quote": r[1], "theme": r[2], "link": r[3]}
        for r in rows
        if len(r) >= 4
    ]


def pick_manga(manga_list: list[dict]) -> dict:
    """ランダムに1件選ぶ"""
    return random.choice(manga_list)


def get_recent_history(n: int = 7) -> list[dict]:
    """historyシートの最新n件を取得。列順: date / title / post / analysis / insights"""
    result = (
        _get_service()
        .spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=f"{HISTORY_SHEET}!A2:E")
        .execute()
    )
    rows = result.get("values", [])
    recent = rows[-n:] if len(rows) > n else rows
    keys = ["date", "title", "post", "analysis", "insights"]
    return [dict(zip(keys, r)) for r in recent]


def append_history(post_text: str, manga: dict, analysis: str = "", insights: str = "") -> None:
    """historyシートに投稿結果を追記"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = [now, manga["title"], post_text, analysis, insights]
    (
        _get_service()
        .spreadsheets()
        .values()
        .append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{HISTORY_SHEET}!A:E",
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        )
        .execute()
    )
