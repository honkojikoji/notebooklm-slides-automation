"""
sheets_manager.py - Google Sheets 読み書きユーティリティ

スプレッドシートの構造:
  A列: keyword
  B列: status (pending / researching / generating / done / error)
  C列: notebook_id
  D列: updated_at
  E列: drive_link
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

import gspread

SPREADSHEET_ID = "1OuUuOi6M-zI5W9msEccQDASzpOGJMu2m1rDXtUIgcsA"
SHEET_INDEX = 0  # gid=0


@dataclass
class Task:
    row: int  # 1-indexed row number in the spreadsheet
    keyword: str
    status: str = "pending"
    notebook_id: str = ""
    updated_at: str = ""
    drive_link: str = ""


class SheetsManager:
    def __init__(self):
        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        if not sa_json:
            raise RuntimeError("環境変数 GOOGLE_SERVICE_ACCOUNT_JSON が設定されていません")

        sa_info = json.loads(sa_json)
        self.gc = gspread.service_account_from_dict(sa_info)
        self.sh = self.gc.open_by_key(SPREADSHEET_ID)
        self.ws = self.sh.get_worksheet(SHEET_INDEX)

    # ------------------------------------------------------------------ #
    #  読み取り
    # ------------------------------------------------------------------ #
    def get_all_tasks(self) -> list[Task]:
        """全行を読み取り Task のリストを返す（1行目はヘッダーとしてスキップ可能）"""
        rows = self.ws.get_all_values()
        tasks: list[Task] = []

        for i, row in enumerate(rows):
            # 1行目がヘッダーの場合はスキップ
            if i == 0 and row and row[0].lower().strip() in ("keyword", "キーワード", ""):
                continue

            keyword = row[0].strip() if len(row) > 0 else ""
            if not keyword:
                continue  # 空行はスキップ

            task = Task(
                row=i + 1,  # gspread は 1-indexed
                keyword=keyword,
                status=(row[1].strip() if len(row) > 1 else "pending") or "pending",
                notebook_id=row[2].strip() if len(row) > 2 else "",
                updated_at=row[3].strip() if len(row) > 3 else "",
                drive_link=row[4].strip() if len(row) > 4 else "",
            )
            tasks.append(task)

        return tasks

    def get_tasks_by_status(self, status: str) -> list[Task]:
        return [t for t in self.get_all_tasks() if t.status == status]

    # ------------------------------------------------------------------ #
    #  書き込み
    # ------------------------------------------------------------------ #
    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def update_status(self, task: Task, new_status: str):
        """B列 (status) と D列 (updated_at) を更新"""
        self.ws.update_cell(task.row, 2, new_status)
        self.ws.update_cell(task.row, 4, self._now())
        task.status = new_status

    def save_notebook_id(self, task: Task, notebook_id: str):
        """C列 (notebook_id) を保存"""
        self.ws.update_cell(task.row, 3, notebook_id)
        task.notebook_id = notebook_id

    def save_drive_link(self, task: Task, drive_link: str):
        """E列 (drive_link) を保存"""
        self.ws.update_cell(task.row, 5, drive_link)
        task.drive_link = drive_link

    def mark_error(self, task: Task, message: str = ""):
        """エラー状態にする"""
        error_status = f"error: {message}" if message else "error"
        self.update_status(task, error_status)
