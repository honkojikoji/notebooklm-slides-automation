"""
browser_utils.py - Chrome 起動・認証チェック共通処理

Linux headless / Windows GUI 両対応。
NotebookLM へのログイン済みセッションを前提とする。
"""

import os
import sys
import time
import platform
import traceback
from pathlib import Path
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# --------------------------------------------------------------------------- #
#  ログユーティリティ
# --------------------------------------------------------------------------- #
def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def log_element_info(element, label: str = ""):
    try:
        tag = element.tag_name
        text = (element.text or "")[:80]
        displayed = element.is_displayed()
        enabled = element.is_enabled()
        log(f"  🔍 [{label}] tag={tag}, displayed={displayed}, enabled={enabled}, text='{text}'")
    except Exception as e:
        log(f"  ⚠️ [{label}] 要素情報取得失敗: {e}")


# --------------------------------------------------------------------------- #
#  Chrome ドライバー生成
# --------------------------------------------------------------------------- #
def create_driver(
    download_dir: str | None = None,
    chrome_version: int | None = None,
) -> uc.Chrome:
    """
    undetected-chromedriver のインスタンスを返す。

    - Linux では headless=new + xvfb を想定
    - Windows ではウィンドウを表示
    """
    is_linux = platform.system() == "Linux"

    profile_path = Path.home() / ".notebooklm_mcp" / "chrome_profile"
    # GitHub Actions では CHROME_PROFILE_DIR 環境変数で上書き可能
    profile_dir = os.environ.get("CHROME_PROFILE_DIR", str(profile_path.absolute()))
    Path(profile_dir).mkdir(parents=True, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    is_ci = os.environ.get("CI") == "true"
    if is_linux or is_ci:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

    if download_dir:
        prefs = {
            "download.default_directory": os.path.abspath(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
        }
        options.add_experimental_option("prefs", prefs)

    version = chrome_version
    if version is None:
        version = 147  # 強制的に147を使用する (GitHub Actionsのstableと合わせる)

    log(f"Chrome 起動: profile={profile_dir}, headless={is_linux}, version_main={version}")
    driver = uc.Chrome(options=options, version_main=version)
    return driver


# --------------------------------------------------------------------------- #
#  認証チェック
# --------------------------------------------------------------------------- #
def check_auth(driver: uc.Chrome) -> bool:
    """
    現在のページが NotebookLM にログイン済みかどうかを判定する。
    ログイン画面にリダイレクトされていれば False を返す。
    """
    current_url = driver.current_url
    if "accounts.google.com" in current_url or "signin" in current_url:
        log("❌ 認証が必要です (ログイン画面にリダイレクトされました)")
        return False
    log("✅ 認証済み")
    return True


def open_notebooklm_home(driver: uc.Chrome) -> bool:
    """NotebookLM のホーム画面を開き、認証状態を返す"""
    log("NotebookLM ホーム画面を開いています...")
    driver.get("https://notebooklm.google.com/")
    time.sleep(3)
    return check_auth(driver)


def open_notebook(driver: uc.Chrome, notebook_id: str) -> bool:
    """指定の notebook を開き、認証状態を返す"""
    url = f"https://notebooklm.google.com/notebook/{notebook_id}"
    log(f"ノートブックを開いています: {url}")
    driver.get(url)
    time.sleep(3)
    return check_auth(driver)


# --------------------------------------------------------------------------- #
#  クリックヘルパー
# --------------------------------------------------------------------------- #
def safe_click(driver: uc.Chrome, element, label: str = ""):
    """通常クリック → 失敗時は JS クリックにフォールバック"""
    try:
        element.click()
        log(f"✅ [{label}] click() 成功")
    except Exception:
        driver.execute_script("arguments[0].click();", element)
        log(f"✅ [{label}] JS クリック成功")


def wait_and_click(driver: uc.Chrome, locator: tuple, timeout: int = 30, label: str = ""):
    """要素が clickable になるまで待機してからクリック"""
    element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    log_element_info(element, label)
    safe_click(driver, element, label)
    return element
