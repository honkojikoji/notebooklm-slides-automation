"""
dispatcher.py - メインディスパッチャー

スプレッドシートを読み取り、各タスクの status に応じて
Phase 1 / 2 / 3 を振り分けて実行する。

優先度: Phase3 (generating) > Phase2 (researching) > Phase1 (pending)
  → 完了に近いタスクを先に処理し、1回のランで複数フェーズをこなす
"""

import sys
import os
import traceback

# scripts/ ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from browser_utils import log
from sheets_manager import SheetsManager

import phase1_create_research
import phase2_import_generate
import phase3_download_pptx


def main():
    log("=" * 60)
    log("NotebookLM Slide Generator - Dispatcher 起動")
    log("=" * 60)

    try:
        sheets = SheetsManager()
    except Exception as e:
        log(f"❌ SheetsManager の初期化に失敗: {e}")
        traceback.print_exc()
        sys.exit(1)

    tasks = sheets.get_all_tasks()
    log(f"タスク総数: {len(tasks)}")
    for t in tasks:
        log(f"  row={t.row}: keyword='{t.keyword}', status='{t.status}', notebook_id='{t.notebook_id}'")

    # -------------------------------------------------------------- #
    #  Phase 3: generating → done (完了に近いものを最優先)
    # -------------------------------------------------------------- #
    generating_tasks = [t for t in tasks if t.status == "generating"]
    log(f"\n--- Phase 3 候補 (generating): {len(generating_tasks)} 件 ---")
    for task in generating_tasks:
        log(f"Phase 3 実行: '{task.keyword}'")
        try:
            phase3_download_pptx.run(task, sheets)
        except Exception as e:
            log(f"❌ Phase 3 で例外: {e}")
            traceback.print_exc()

    # -------------------------------------------------------------- #
    #  Phase 2: researching → generating
    # -------------------------------------------------------------- #
    researching_tasks = [t for t in tasks if t.status == "researching"]
    log(f"\n--- Phase 2 候補 (researching): {len(researching_tasks)} 件 ---")
    for task in researching_tasks:
        log(f"Phase 2 実行: '{task.keyword}'")
        try:
            phase2_import_generate.run(task, sheets)
        except Exception as e:
            log(f"❌ Phase 2 で例外: {e}")
            traceback.print_exc()

    # -------------------------------------------------------------- #
    #  Phase 1: pending → researching (新規投入は1件だけ)
    # -------------------------------------------------------------- #
    pending_tasks = [t for t in tasks if t.status == "pending"]
    log(f"\n--- Phase 1 候補 (pending): {len(pending_tasks)} 件 ---")
    if pending_tasks:
        task = pending_tasks[0]  # 最初の1件のみ
        log(f"Phase 1 実行: '{task.keyword}'")
        try:
            phase1_create_research.run(task, sheets)
        except Exception as e:
            log(f"❌ Phase 1 で例外: {e}")
            traceback.print_exc()
    else:
        log("新規投入するタスクはありません")

    # -------------------------------------------------------------- #
    #  サマリー
    # -------------------------------------------------------------- #
    log("\n" + "=" * 60)
    log("Dispatcher 完了 — 最終サマリー")
    log("=" * 60)
    updated_tasks = sheets.get_all_tasks()
    for t in updated_tasks:
        status_icon = {
            "pending": "⬜",
            "researching": "🔍",
            "generating": "🔄",
            "done": "✅",
        }.get(t.status, "❌" if "error" in t.status else "❓")
        log(f"  {status_icon} '{t.keyword}' → {t.status}")


if __name__ == "__main__":
    main()
