"""
phase3_download_pptx.py - Phase 3: PPTX ダウンロード + Google Drive アップロード

処理フロー:
  1. 保存済みの notebook_id でノートブックを開く
  2. スライドの生成完了を確認
     - まだ生成中 → 即終了 (次回ランで再チェック)
     - 完了済み → 「その他」→「PowerPoint（.pptx）をダウンロード」
  3. ダウンロードした PPTX を Google Drive にアップロード
  4. 共有リンクをスプレッドシートの E列 に書き込む
  5. status = "done" に更新
"""

import os
import time
import glob
import traceback
import tempfile

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from browser_utils import (
    log, log_element_info, create_driver, open_notebook,
    safe_click,
)
from sheets_manager import SheetsManager, Task
from drive_uploader import upload_to_drive


def run(task: Task, sheets: SheetsManager) -> bool:
    """
    Phase 3 を実行する。成功すれば True を返す。
    まだ準備ができていなければ False を返す (エラーではない)。
    """
    log("=" * 50)
    log(f"Phase 3 開始: keyword='{task.keyword}', notebook_id='{task.notebook_id}'")
    log("=" * 50)

    if not task.notebook_id:
        log("❌ notebook_id が未設定です")
        sheets.mark_error(task, "no_notebook_id")
        return False

    # 一時ダウンロードディレクトリ
    download_dir = tempfile.mkdtemp(prefix="nlm_slides_")
    log(f"ダウンロード先: {download_dir}")

    driver = create_driver(download_dir=download_dir)
    try:
        # 1. ノートブックを開く
        if not open_notebook(driver, task.notebook_id):
            sheets.mark_error(task, "auth_required")
            return False

        time.sleep(5)

        # 2. 生成完了の確認
        log("スライド生成の完了状態を確認しています...")
        loading_locator = (By.XPATH, "//span[contains(text(), 'スライド資料を生成しています')]")
        loading_elements = driver.find_elements(*loading_locator)
        if loading_elements:
            log("⏳ まだスライドを生成中です → 次回ランで再チェック")
            return False  # エラーではない

        # 「その他」ボタンを探す
        log("「その他」ボタンを探しています...")
        more_buttons = driver.find_elements(
            By.CSS_SELECTOR,
            "button[aria-label='その他'], button.artifact-more-button",
        )
        log(f"  候補数: {len(more_buttons)}")

        if not more_buttons:
            log("⏳ 「その他」ボタンが見つかりません → スライドがまだ存在しない可能性")
            return False

        # 最新のアーティファクトの「その他」ボタンをクリック
        target_btn = more_buttons[-1]
        log_element_info(target_btn, "その他ボタン")
        driver.execute_script("arguments[0].click();", target_btn)
        log("✅ 「その他」メニューを開きました")
        time.sleep(2)

        # メニュー項目をログ出力
        menu_items = driver.find_elements(By.CSS_SELECTOR, "button[role='menuitem']")
        log(f"  メニュー項目数: {len(menu_items)}")
        for i, item in enumerate(menu_items):
            log_element_info(item, f"menuitem[{i}]")

        # 「PowerPoint（.pptx）をダウンロード」をクリック
        log("PowerPoint ダウンロードボタンを探しています...")
        try:
            dl_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "//*[contains(text(), 'PowerPoint')]/ancestor::button[1]"
                     " | //button[@role='menuitem' and .//span[contains(text(), 'PowerPoint')]]")
                )
            )
            log_element_info(dl_btn, "PPTX DLボタン")
            safe_click(driver, dl_btn, "PPTX DLボタン")
        except TimeoutException:
            log("❌ PowerPoint ダウンロードボタンが見つかりません")
            sheets.mark_error(task, "pptx_btn_not_found")
            return False

        # ダウンロード完了を監視
        log("ダウンロード完了を監視しています...")
        pptx_path = None
        for i in range(120):
            time.sleep(1)
            pptx_files = glob.glob(os.path.join(download_dir, "*.pptx"))
            crdownload = glob.glob(os.path.join(download_dir, "*.crdownload"))
            if i % 10 == 0:
                log(f"  監視中... pptx={len(pptx_files)}, crdownload={len(crdownload)}")
            if pptx_files and not crdownload:
                pptx_path = pptx_files[0]
                log(f"✅ ダウンロード完了: {pptx_path}")
                break

        if not pptx_path:
            log("❌ ダウンロードがタイムアウトしました")
            sheets.mark_error(task, "download_timeout")
            return False

        # 3. Google Drive にアップロード
        log("Google Drive にアップロードしています...")
        drive_link = upload_to_drive(pptx_path)
        log(f"✅ アップロード完了: {drive_link}")

        # 4. スプレッドシート更新
        sheets.save_drive_link(task, drive_link)
        sheets.update_status(task, "done")
        log("✅ Phase 3 完了: status → done")
        return True

    except Exception as e:
        log(f"❌ Phase 3 エラー: {e}")
        traceback.print_exc()
        sheets.mark_error(task, str(e)[:50])
        return False
    finally:
        driver.quit()
        log("ブラウザ終了")
