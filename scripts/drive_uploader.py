"""
drive_uploader.py - Google Drive アップロード + 共有リンク取得

サービスアカウントを使用して PPTX ファイルを指定フォルダにアップロードし、
「リンクを知っている全員が閲覧可能」に設定したうえで共有リンクを返す。
"""

import os
import json
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _get_credentials():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not sa_json:
        raise RuntimeError("環境変数 GOOGLE_SERVICE_ACCOUNT_JSON が設定されていません")
    sa_info = json.loads(sa_json)
    return service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)


def upload_to_drive(file_path: str, folder_id: Optional[str] = None) -> str:
    """
    PPTX ファイルを Google Drive にアップロードし、共有リンクを返す。

    Args:
        file_path: アップロードするファイルのパス
        folder_id: 保存先フォルダの ID (None の場合はルートに保存)

    Returns:
        共有リンク (https://drive.google.com/file/d/{id}/view)
    """
    if folder_id is None:
        folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")

    creds = _get_credentials()
    service = build("drive", "v3", credentials=creds)

    # ファイルメタデータ
    file_metadata = {"name": os.path.basename(file_path)}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    # アップロード
    media = MediaFileUpload(file_path, mimetype=PPTX_MIME, resumable=True)
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )
    file_id = file["id"]

    # 共有設定: リンクを知っている全員が閲覧可能
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    share_link = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"[DriveUploader] アップロード完了: {share_link}")
    return share_link
