"""
phase2_import_generate.py - Phase 2: インポート + スライド生成投入

処理フロー:
  1. 保存済みの notebook_id でノートブックを開く
  2. 「インポート」ボタンが存在するか確認
     - なければ即終了 (次回ランで再チェック)
     - あればクリック → 1分待機
  3. 「スライド資料をカスタマイズ」→ 指示入力 → 「生成」
  4. status = "generating" に更新して即終了
"""

import time
import traceback

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from browser_utils import (
    log, log_element_info, create_driver, open_notebook,
    safe_click, wait_and_click,
)
from sheets_manager import SheetsManager, Task


def run(task: Task, sheets: SheetsManager) -> bool:
    """
    Phase 2 を実行する。成功すれば True を返す。
    まだ準備ができていなければ False を返す (エラーではない)。
    """
    log("=" * 50)
    log(f"Phase 2 開始: keyword='{task.keyword}', notebook_id='{task.notebook_id}'")
    log("=" * 50)

    if not task.notebook_id:
        log("❌ notebook_id が未設定です")
        sheets.mark_error(task, "no_notebook_id")
        return False

    driver = create_driver()
    try:
        # 1. ノートブックを開く
        if not open_notebook(driver, task.notebook_id):
            sheets.mark_error(task, "auth_required")
            return False

        # 2. 「インポート」ボタンを確認
        log("「インポート」ボタンを探しています (最大30秒)...")
        import_btn_xpath = "//button[.//span[contains(text(), 'インポート')]]"
        try:
            import_btn = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, import_btn_xpath))
            )
        except TimeoutException:
            log("⏳ インポートボタンがまだ表示されていません → 次回ランで再チェック")
            return False  # エラーではなく、まだ準備ができていないだけ

        log_element_info(import_btn, "インポートボタン")
        safe_click(driver, import_btn, "インポートボタン")
        log("✅ インポートクリック完了")

        # 1分待機
        log("インポート後、1分間待機します...")
        for remaining in range(60, 0, -10):
            log(f"  ⏳ 残り {remaining} 秒...")
            time.sleep(10)
        log("✅ 1分待機完了")

        # 3. 「スライド資料をカスタマイズ」ボタン (chevron_forward)
        log("「スライド資料をカスタマイズ」ボタンを探しています...")
        customize_locator = (
            By.CSS_SELECTOR,
            "button[aria-label='スライド資料をカスタマイズ'],"
            "button[data-edit-button-type='8']",
        )
        customize_btn = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(customize_locator)
        )
        log_element_info(customize_btn, "カスタマイズボタン")
        safe_click(driver, customize_btn, "カスタマイズボタン")
        time.sleep(2)

        # 指示テキスト入力
        instruction = f'日本語で「{task.keyword}」について詳しく解説する。'
        log(f"指示テキスト: '{instruction}'")
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 "textarea[aria-label='作成するスライドについて説明してください'],"
                 "textarea[placeholder*='概要を追加する']")
            )
        )
        textarea.clear()
        textarea.send_keys(instruction)
        log("✅ 指示入力完了")
        time.sleep(1)

        # 「生成」ボタン
        log("「生成」ボタンをクリック...")
        generate_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[contains(text(), '生成')]]")
            )
        )
        safe_click(driver, generate_btn, "生成ボタン")
        log("✅ 生成ボタンクリック完了")
        time.sleep(3)

        # 4. status 更新
        sheets.update_status(task, "generating")
        log("✅ Phase 2 完了: status → generating")
        return True

    except Exception as e:
        log(f"❌ Phase 2 エラー: {e}")
        traceback.print_exc()
        sheets.mark_error(task, str(e)[:50])
        return False
    finally:
        driver.quit()
        log("ブラウザ終了")
