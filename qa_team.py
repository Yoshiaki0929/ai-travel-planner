"""
QA Agent Team for AI Travel Planner
-------------------------------------
4つの専門QAエージェントがそれぞれの観点でテストを実施し、
最後にQAリーダーが結果をまとめてレポートを生成します。

QA Agent Team 構成:
  1. Unit Test Agent     - 各ツール関数の単体テスト
  2. Edge Case Agent     - 境界値・異常系テスト
  3. Logic Validator     - ビジネスロジック整合性検証
  4. Frontend Inspector  - HTML/JS/API スキーマ検証
  5. QA Leader (Claude)  - 全結果を統合し最終レポート生成
"""

import json
import sys
import traceback
import re
import anthropic
from anthropic import beta_tool

client = anthropic.Anthropic()

# ─────────────────────────────────────────────────
# テスト対象の関数を直接インポート
# (@beta_tool は Python 関数として普通に呼び出せる)
# ─────────────────────────────────────────────────
sys.path.insert(0, ".")
from agents import (
    research_destination,
    calculate_budget,
    create_itinerary,
    find_experiences,
)


# ════════════════════════════════════════════════════════
# QA Agent 1: Unit Test Agent
# ════════════════════════════════════════════════════════
@beta_tool
def run_unit_tests() -> str:
    """各ツール関数を正常系データで単体テストする。
    関数が呼び出し可能か、JSON を返すか、必須キーが存在するかを確認する。
    """
    results = []

    # ── research_destination ──
    cases = [
        ("バリ島", "2024-03-01〜2024-03-04"),
        ("パリ",   "2024-06-10〜2024-06-15"),
        ("未知の都市X", "2024-12-01〜2024-12-03"),
    ]
    for dest, dates in cases:
        try:
            raw = research_destination(dest, dates)
            data = json.loads(raw)
            required = {"destination", "travel_dates", "highlights", "climate",
                        "travel_tips", "language", "currency"}
            missing = required - set(data.keys())
            ok = len(missing) == 0 and isinstance(data["highlights"], list)
            results.append({
                "agent": "UnitTest",
                "function": "research_destination",
                "input": dest,
                "status": "PASS" if ok else "FAIL",
                "detail": f"missing keys: {missing}" if missing else "全必須キー存在",
            })
        except Exception as e:
            results.append({
                "agent": "UnitTest",
                "function": "research_destination",
                "input": dest,
                "status": "ERROR",
                "detail": str(e),
            })

    # ── calculate_budget ──
    budget_cases = [
        ("バリ島",     4, 250_000, 2),
        ("パリ",       5, 500_000, 2),
        ("ニューヨーク", 7, 800_000, 1),
        ("京都",       3, 120_000, 2),
    ]
    for dest, days, budget, people in budget_cases:
        try:
            raw = calculate_budget(dest, days, budget, people)
            data = json.loads(raw)
            required = {"総予算", "1人あたり予算", "内訳", "節約ポイント", "予算評価"}
            missing = required - set(data.keys())
            ok = len(missing) == 0
            results.append({
                "agent": "UnitTest",
                "function": "calculate_budget",
                "input": f"{dest}/{days}日/{budget}円/{people}人",
                "status": "PASS" if ok else "FAIL",
                "detail": f"missing: {missing}" if missing else "全必須キー存在",
            })
        except Exception as e:
            results.append({
                "agent": "UnitTest",
                "function": "calculate_budget",
                "input": dest,
                "status": "ERROR",
                "detail": str(e),
            })

    # ── create_itinerary ──
    itinerary_cases = [
        ("バリ島", 4, "リゾート重視"),
        ("パリ",   5, "バランス型"),
        ("東京",   3, "観光重視"),
        ("未知",   7, "グルメ重視"),
    ]
    for dest, days, style in itinerary_cases:
        try:
            raw = create_itinerary(dest, days, style)
            data = json.loads(raw)
            day_count = len(data.get("日程表", []))
            ok = day_count == days
            results.append({
                "agent": "UnitTest",
                "function": "create_itinerary",
                "input": f"{dest}/{days}日/{style}",
                "status": "PASS" if ok else "FAIL",
                "detail": f"期待{days}日, 実際{day_count}日",
            })
        except Exception as e:
            results.append({
                "agent": "UnitTest",
                "function": "create_itinerary",
                "input": dest,
                "status": "ERROR",
                "detail": str(e),
            })

    # ── find_experiences ──
    exp_cases = [
        ("バリ島", "グルメ、リラックス", 10_000),
        ("パリ",   "アート、ショッピング", 20_000),
        ("東京",   "観光",              5_000),
        ("不明",   "存在しない興味",     8_000),
    ]
    for dest, interests, daily_budget in exp_cases:
        try:
            raw = find_experiences(dest, interests, daily_budget)
            data = json.loads(raw)
            required = {"旅行先", "予算レベル", "1日体験予算", "おすすめ体験"}
            missing = required - set(data.keys())
            ok = len(missing) == 0 and isinstance(data.get("おすすめ体験"), dict)
            results.append({
                "agent": "UnitTest",
                "function": "find_experiences",
                "input": f"{dest}/{interests}/{daily_budget}円",
                "status": "PASS" if ok else "FAIL",
                "detail": f"missing: {missing}" if missing else "全必須キー存在",
            })
        except Exception as e:
            results.append({
                "agent": "UnitTest",
                "function": "find_experiences",
                "input": dest,
                "status": "ERROR",
                "detail": str(e),
            })

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    return json.dumps({
        "summary": f"Unit Tests: {pass_count}/{len(results)} PASS",
        "results": results,
    }, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════
# QA Agent 2: Edge Case Agent
# ════════════════════════════════════════════════════════
@beta_tool
def run_edge_case_tests() -> str:
    """境界値・異常系・エッジケースをテストする。
    ゼロ除算、1日旅行、大人数、超低予算などを検証する。
    """
    results = []

    def test(name, fn, *args):
        try:
            result = fn(*args)
            data = json.loads(result)
            results.append({
                "agent": "EdgeCase", "name": name,
                "status": "PASS", "detail": "例外なく正常終了",
            })
            return data
        except ZeroDivisionError as e:
            results.append({
                "agent": "EdgeCase", "name": name,
                "status": "FAIL", "detail": f"ZeroDivisionError: {e}",
            })
        except Exception as e:
            results.append({
                "agent": "EdgeCase", "name": name,
                "status": "ERROR", "detail": f"{type(e).__name__}: {e}",
            })
        return None

    # 1日旅行
    test("1日旅行のスケジュール", create_itinerary, "バリ島", 1, "バランス型")

    # 長期旅行 (30日)
    test("30日間旅行のスケジュール", create_itinerary, "パリ", 30, "バランス型")

    # 超低予算
    test("超低予算(1万円/1人)", calculate_budget, "バリ島", 4, 10_000, 1)

    # 大人数
    test("10人旅行の予算", calculate_budget, "パリ", 5, 1_000_000, 10)

    # num_people=1 での除算確認
    test("1人旅行の予算", calculate_budget, "東京", 3, 150_000, 1)

    # 空文字列の旅行先
    test("空文字列の旅行先(research)", research_destination, "", "2024-01-01〜2024-01-03")

    # 空文字列の旅行先(itinerary)
    test("空文字列の旅行先(itinerary)", create_itinerary, "", 3, "バランス型")

    # 興味が空文字列
    test("興味が空文字列", find_experiences, "バリ島", "", 10_000)

    # 日予算0円
    test("日予算0円", find_experiences, "パリ", "グルメ", 0)

    # 絵文字が旅行先に含まれる
    test("絵文字付き旅行先", research_destination, "🌴バリ島🌊", "2024-03-01")

    # 非常に長い旅行先名
    long_name = "a" * 500
    test("500文字の旅行先名", research_destination, long_name, "2024-01-01")

    # duration_days が負 → Python は range(1, 0) なので空リストになるはず
    test("duration_days=0", create_itinerary, "東京", 0, "バランス型")

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    return json.dumps({
        "summary": f"Edge Case Tests: {pass_count}/{len(results)} PASS",
        "results": results,
    }, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════
# QA Agent 3: Logic Validator
# ════════════════════════════════════════════════════════
@beta_tool
def validate_business_logic() -> str:
    """ビジネスロジックの整合性を検証する。
    予算計算の数値整合性、日程の連続性、興味マッチングなどを確認する。
    """
    results = []

    # ── 予算内訳の合計検証 ──
    try:
        raw = calculate_budget("バリ島", 4, 300_000, 2)
        data = json.loads(raw)
        inner = data["内訳"]

        def extract_num(s: str) -> int:
            m = re.search(r"([\d,]+)円", s)
            return int(m.group(1).replace(",", "")) if m else 0

        total_per_person = 300_000 // 2  # 150_000
        items = {k: extract_num(v) for k, v in inner.items()}
        allocated = sum(items.values())
        # 割り算の丸め誤差を考慮して±5%以内を許容
        tolerance = total_per_person * 0.05
        ok = abs(allocated - total_per_person) <= tolerance
        results.append({
            "agent": "LogicValidator",
            "check": "予算内訳の合計",
            "status": "PASS" if ok else "FAIL",
            "detail": f"1人予算:{total_per_person:,}円, 配分合計:{allocated:,}円, 差:{abs(allocated-total_per_person):,}円",
        })
    except Exception as e:
        results.append({
            "agent": "LogicValidator", "check": "予算内訳の合計",
            "status": "ERROR", "detail": str(e),
        })

    # ── 予算評価ラベルの正当性 ──
    try:
        cases = [
            ("バリ島", 4, 500_000, 1, "余裕あり"),   # 十分な予算
            ("パリ",   5,  50_000, 1, "やや厳しい"),  # 非常に少ない予算
        ]
        for dest, days, budget, people, expected_label in cases:
            raw = calculate_budget(dest, days, budget, people)
            data = json.loads(raw)
            actual = data.get("予算評価", "")
            ok = actual == expected_label
            results.append({
                "agent": "LogicValidator",
                "check": f"予算評価ラベル({dest}/{budget}円)",
                "status": "PASS" if ok else "FAIL",
                "detail": f"期待:'{expected_label}', 実際:'{actual}'",
            })
    except Exception as e:
        results.append({
            "agent": "LogicValidator", "check": "予算評価ラベル",
            "status": "ERROR", "detail": str(e),
        })

    # ── 日程の日数が入力と一致するか ──
    try:
        for days in [1, 3, 5, 7, 14]:
            raw = create_itinerary("バリ島", days, "バランス型")
            data = json.loads(raw)
            actual_days = len(data["日程表"])
            ok = actual_days == days
            results.append({
                "agent": "LogicValidator",
                "check": f"日程日数の一致({days}日)",
                "status": "PASS" if ok else "FAIL",
                "detail": f"期待:{days}日, 実際:{actual_days}日",
            })
    except Exception as e:
        results.append({
            "agent": "LogicValidator", "check": "日程日数",
            "status": "ERROR", "detail": str(e),
        })

    # ── 予算レベル分類の境界値 ──
    try:
        cases = [
            (14_999, "中予算"),
            (15_000, "高予算"),
            (7_999,  "低予算"),
            (8_000,  "中予算"),
        ]
        for daily_budget, expected_level in cases:
            raw = find_experiences("バリ島", "グルメ", daily_budget)
            data = json.loads(raw)
            actual = data.get("予算レベル", "")
            ok = actual == expected_level
            results.append({
                "agent": "LogicValidator",
                "check": f"予算レベル境界値({daily_budget}円)",
                "status": "PASS" if ok else "FAIL",
                "detail": f"期待:'{expected_level}', 実際:'{actual}'",
            })
    except Exception as e:
        results.append({
            "agent": "LogicValidator", "check": "予算レベル境界値",
            "status": "ERROR", "detail": str(e),
        })

    # ── バリ島・パリ固有データの使用確認 ──
    try:
        for dest, expected_highlight in [("バリ島", "ウブド芸術村"), ("パリ", "エッフェル塔")]:
            raw = research_destination(dest, "2024-01-01")
            data = json.loads(raw)
            ok = expected_highlight in data.get("highlights", [])
            results.append({
                "agent": "LogicValidator",
                "check": f"{dest}の固有データ使用",
                "status": "PASS" if ok else "FAIL",
                "detail": f"'{expected_highlight}' が highlights に{'含まれる' if ok else '含まれない'}",
            })
    except Exception as e:
        results.append({
            "agent": "LogicValidator", "check": "固有データ使用",
            "status": "ERROR", "detail": str(e),
        })

    # ── 興味マッチング: 存在しない興味のフォールバック ──
    try:
        raw = find_experiences("バリ島", "存在しない興味カテゴリ", 10_000)
        data = json.loads(raw)
        recs = data.get("おすすめ体験", {})
        ok = len(recs) > 0  # フォールバックで何かしら返るはず
        results.append({
            "agent": "LogicValidator",
            "check": "不明な興味のフォールバック",
            "status": "PASS" if ok else "FAIL",
            "detail": f"フォールバック後の体験数: {len(recs)}",
        })
    except Exception as e:
        results.append({
            "agent": "LogicValidator", "check": "不明な興味のフォールバック",
            "status": "ERROR", "detail": str(e),
        })

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    return json.dumps({
        "summary": f"Logic Validation: {pass_count}/{len(results)} PASS",
        "results": results,
    }, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════
# QA Agent 4: Frontend & API Schema Inspector
# ════════════════════════════════════════════════════════
@beta_tool
def inspect_frontend_and_api() -> str:
    """HTML/JS フロントエンドと FastAPI スキーマを静的検査する。
    必須UI要素の存在、フォームフィールドと API の対応、JS エラーパターンを確認する。
    """
    results = []

    # ── HTML ファイル読み込み ──
    try:
        with open("static/index.html", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        return json.dumps({
            "summary": "ERROR: static/index.html が見つかりません",
            "results": [],
        }, ensure_ascii=False)

    # 必須 UI 要素チェック
    ui_checks = [
        ("旅行先入力フィールド",  'id="destination"'),
        ("日数入力フィールド",    'id="duration_days"'),
        ("予算入力フィールド",    'id="budget_jpy"'),
        ("人数入力フィールド",    'id="num_people"'),
        ("旅行スタイルセレクト",  'id="travel_style"'),
        ("追加リクエストtextarea", 'id="additional_requests"'),
        ("送信ボタン",            'id="submitBtn"'),
        ("ローディング表示",      'id="loading"'),
        ("結果表示エリア",        'id="result"'),
        ("エラー表示エリア",      'id="error"'),
        ("プランコンテンツ",      'id="planContent"'),
        ("marked.js 読み込み",   "marked"),
        ("プリセット: バリ島",    "applyPreset('bali')"),
        ("プリセット: パリ",      "applyPreset('paris')"),
        ("プリセット: 国内旅行",  "applyPreset('domestic')"),
        ("SSE エンドポイント呼び出し", "/api/plan/stream"),
    ]
    for name, pattern in ui_checks:
        ok = pattern in html
        results.append({
            "agent": "FrontendInspector",
            "check": name,
            "status": "PASS" if ok else "FAIL",
            "detail": f"'{pattern}' {'存在する' if ok else '存在しない'}",
        })

    # フォームフィールドと API ペイロードの対応チェック
    api_fields = ["destination", "duration_days", "budget_jpy",
                  "num_people", "interests", "travel_style", "additional_requests"]
    for field in api_fields:
        ok = field in html
        results.append({
            "agent": "FrontendInspector",
            "check": f"APIフィールド対応: {field}",
            "status": "PASS" if ok else "FAIL",
            "detail": f"'{field}' が HTML に{'存在する' if ok else '存在しない'}",
        })

    # JS: JSON.parse のエラーハンドリング確認
    has_try_catch = "try {" in html and "catch" in html
    results.append({
        "agent": "FrontendInspector",
        "check": "JS try-catch エラーハンドリング",
        "status": "PASS" if has_try_catch else "FAIL",
        "detail": "try-catch ブロックが存在する" if has_try_catch else "エラーハンドリングなし",
    })

    # SSE: ReadableStream の実装確認
    has_reader = "getReader()" in html
    results.append({
        "agent": "FrontendInspector",
        "check": "ReadableStream による SSE 受信",
        "status": "PASS" if has_reader else "FAIL",
        "detail": "getReader() が存在する" if has_reader else "SSE 受信実装が見つからない",
    })

    # ── main.py の FastAPI スキーマ確認 ──
    try:
        with open("main.py", encoding="utf-8") as f:
            main_py = f.read()
    except FileNotFoundError:
        results.append({
            "agent": "FrontendInspector", "check": "main.py 読み込み",
            "status": "ERROR", "detail": "main.py が見つかりません",
        })
        main_py = ""

    if main_py:
        api_checks = [
            ("GET / ルート",             "@app.get(\"/\")"),
            ("POST /api/plan",           "@app.post(\"/api/plan\")"),
            ("POST /api/plan/stream",    "@app.post(\"/api/plan/stream\")"),
            ("GET /health",              "@app.get(\"/health\")"),
            ("static ファイル配信",       "StaticFiles"),
            ("非同期エクスキュータ使用",  "run_in_executor"),
            ("StreamingResponse",        "StreamingResponse"),
        ]
        for name, pattern in api_checks:
            ok = pattern in main_py
            results.append({
                "agent": "FrontendInspector",
                "check": f"API: {name}",
                "status": "PASS" if ok else "FAIL",
                "detail": f"'{pattern}' {'存在する' if ok else '存在しない'}",
            })

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    return json.dumps({
        "summary": f"Frontend & API Inspection: {pass_count}/{len(results)} PASS",
        "results": results,
    }, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════
# QA Leader (オーケストレーター)
# ════════════════════════════════════════════════════════
def run_qa_team() -> str:
    """QA Agent Team を起動し、全テストを実行してレポートを生成する"""

    print("=" * 60)
    print("🔍 QA Agent Team 起動")
    print("=" * 60)

    system_prompt = """あなたはシニアQAエンジニアです。
4つの専門QAエージェント（ユニットテスト・エッジケース・ロジック検証・フロントエンド検査）
のツールを全て使って旅行プランナーアプリをテストしてください。

全ツールを必ず実行した後、以下の形式でMarkdownレポートを出力してください：

# 🧪 QA Agent Team テストレポート

## 📊 総合サマリー
（全体のPASS/FAIL/ERROR件数、総合評価）

## ✅ Unit Test Agent の結果
（各関数のテスト結果一覧）

## ⚠️ Edge Case Agent の結果
（境界値・異常系テスト結果。FAILしたものは特に詳しく）

## 🔍 Logic Validator の結果
（ビジネスロジックの整合性検証結果）

## 🖥️ Frontend & API Inspector の結果
（HTML/JS/APIスキーマの検査結果）

## 🐛 発見されたバグ・問題点
（FAIL/ERRORになった項目を重要度別に整理）

## 💡 改善提案
（優先度高い順に具体的な修正方法を提示）

必ず日本語で、具体的かつ明確に書いてください。"""

    runner = client.beta.messages.tool_runner(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=system_prompt,
        tools=[
            run_unit_tests,
            run_edge_case_tests,
            validate_business_logic,
            inspect_frontend_and_api,
        ],
        messages=[{
            "role": "user",
            "content": "AI旅行プランナーアプリの全QAテストを実行し、詳細なレポートを作成してください。"
        }],
    )

    print("\n各QAエージェントを実行中...\n")
    final_message = None
    for i, message in enumerate(runner):
        print(f"  → Agent ステップ {i+1} 完了")
        final_message = message

    if final_message is None:
        return "QAテストの実行に失敗しました。"

    for block in final_message.content:
        if hasattr(block, "type") and block.type == "text":
            return block.text

    return "レポートの生成に失敗しました。"


# ════════════════════════════════════════════════════════
# エントリーポイント
# ════════════════════════════════════════════════════════
if __name__ == "__main__":
    report = run_qa_team()

    print("\n" + "=" * 60)
    print("📋 QA REPORT")
    print("=" * 60 + "\n")
    print(report)

    # レポートをファイルに保存
    with open("qa_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("\n" + "=" * 60)
    print("✅ レポートを qa_report.md に保存しました")
    print("=" * 60)
