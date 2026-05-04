"""
phase1_create_research.py - Phase 1: ノートブック作成 + Deep Research 投入

処理フロー:
  1. NotebookLM ホーム画面を開く
  2. 「ノートブックを新規作成」をクリック
  3. researcher-menu-trigger → Deep Research を選択
  4. キーワードを入力して「送信」
  5. URL から notebook_id を取得してスプレッドシートに保存
  6. status = "researching" に更新して即終了
"""

import time
import re
import traceback

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from browser_utils import (
    log, log_element_info, create_driver, check_auth,
    open_notebooklm_home, safe_click, wait_and_click,
)
from sheets_manager import SheetsManager, Task


def run(task: Task, sheets: SheetsManager) -> bool:
    """
    Phase 1 を実行する。成功すれば True を返す。

    処理時間の目安: ~2分
    """
    log("=" * 50)
    log(f"Phase 1 開始: keyword='{task.keyword}'")
    log("=" * 50)

    driver = create_driver()
    try:
        # 1. NotebookLM を開く
        if not open_notebooklm_home(driver):
            sheets.mark_error(task, "auth_required")
            return False

        # 2. 「ノートブックを新規作成」
        log("「ノートブックを新規作成」をクリック...")
        wait_and_click(
            driver,
            (By.CSS_SELECTOR, "button[aria-label='ノートブックを新規作成']"),
            timeout=30,
            label="新規作成ボタン",
        )
        time.sleep(3)

        # 3. researcher-menu-trigger → Deep Research
        log("ソース選択メニュー (researcher-menu-trigger) を開く...")
        menu_trigger = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.researcher-menu-trigger"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", menu_trigger)
        time.sleep(1)
        safe_click(driver, menu_trigger, "researcher-menu-trigger")
        time.sleep(2)

        log("Deep Research を選択...")
        opts = driver.find_elements(By.XPATH, "//*[contains(text(), 'Deep Research')]")
        log(f"  候補数: {len(opts)}")
        if opts:
            target = opts[-1]
            try:
                parent_btn = target.find_element(By.XPATH, "./ancestor::button[1]")
                driver.execute_script("arguments[0].click();", parent_btn)
            except Exception:
                driver.execute_script("arguments[0].click();", target)
            log("✅ Deep Research 選択完了")
        else:
            log("❌ Deep Research が見つかりません")
            sheets.mark_error(task, "deep_research_not_found")
            return False
        time.sleep(2)

        # 4. キーワード入力 → 送信
        log(f"キーワード '{task.keyword}' を入力...")
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 "textarea[formcontrolname='discoverSourcesQuery'],"
                 "textarea[placeholder*='調べたい内容']")
            )
        )
        textarea.send_keys(task.keyword)
        time.sleep(1)

        log("送信ボタンをクリック...")
        wait_and_click(
            driver,
            (By.CSS_SELECTOR, "button[aria-label='送信'], button.actions-enter-button"),
            timeout=10,
            label="送信ボタン",
        )
        time.sleep(3)

        # 5. URL から notebook_id を取得
        current_url = driver.current_url
        log(f"現在のURL: {current_url}")
        match = re.search(r"/notebook/([a-f0-9\-]+)", current_url)
        if match:
            notebook_id = match.group(1)
            log(f"✅ notebook_id 取得: {notebook_id}")
        else:
            # URL にまだ ID がない場合は少し待って再取得
            time.sleep(5)
            current_url = driver.current_url
            match = re.search(r"/notebook/([a-f0-9\-]+)", current_url)
            if match:
                notebook_id = match.group(1)
                log(f"✅ notebook_id 取得 (2回目): {notebook_id}")
            else:
                log(f"❌ notebook_id を取得できません: {current_url}")
                sheets.mark_error(task, "notebook_id_not_found")
                return False

        # 6. スプレッドシート更新
        sheets.save_notebook_id(task, notebook_id)
        sheets.update_status(task, "researching")
        log("✅ Phase 1 完了: status → researching")
        return True

    except Exception as e:
        log(f"❌ Phase 1 エラー: {e}")
        traceback.print_exc()
        sheets.mark_error(task, str(e)[:50])
        return False
    finally:
        driver.quit()
        log("ブラウザ終了")
