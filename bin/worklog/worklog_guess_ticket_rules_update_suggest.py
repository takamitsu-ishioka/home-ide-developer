import json
import math
import os
import re
import sqlite3
import subprocess
import sys
from collections import Counter

PROG = os.path.basename(__file__)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
CORPUS_DB_PATH = os.path.join(SCRIPT_DIR, "_ticket_corpus.sqlite3")
NONDETERMINISTIC_TICKET = "_nondeterministic_"
KEYWORD_RE = re.compile(r"[゠-ヿ一-鿿]{2,}|[A-Za-z0-9][A-Za-z0-9_-]{2,}")


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def load_generator_config() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)
    except OSError as e:
        fail(f"{CONFIG_PATH}を読み取れません: {e}")
    except json.JSONDecodeError as e:
        fail(f"{CONFIG_PATH}: JSONとして読み取れません: {e}")

    generator = config.get("rule_generator")
    if not generator or "threshold_min" not in generator:
        fail(f"{CONFIG_PATH}: rule_generator.threshold_minが必要です")
    return generator


def fetch_tickets(script_dir: str) -> list[dict]:
    """自分の担当チケット一覧(key/summary)を取得する。"""
    result = subprocess.run(
        [os.path.join(script_dir, "worklog_jira_ticket_list.sh"), "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(f"worklog_jira_ticket_list.shが失敗しました: {result.stderr.strip()}")
    return json.loads(result.stdout)


def extract_keyword_set(text: str) -> set[str]:
    """テキストから、キーワード候補(カタカナ・漢字の連続、または英数字の連続)の集合を
    抽出する。形態素解析器(MeCab等)を使わずに済ませるための簡易ヒューリスティック。
    turnのuser発言・ticketのsummaryの両方に同じ抽出方法を使うことで、
    「キーワード集合 対 キーワード集合」の比較にする(生の全文同士の比較はしない)。
    """
    return set(KEYWORD_RE.findall(text))


def extract_frequent_keywords(turns: list[dict]) -> list[str]:
    """ticketが_nondeterministic_のturnのuser発言から、頻出するキーワード候補を
    頻度降順で抽出する。
    """
    counter: Counter[str] = Counter()
    for turn in turns:
        if turn.get("ticket") != NONDETERMINISTIC_TICKET:
            continue
        for line in turn.get("user", []):
            counter.update(KEYWORD_RE.findall(line))
    return [word for word, _ in counter.most_common()]


def char_bigrams(text: str) -> set[str]:
    if len(text) < 2:
        return {text} if text else set()
    return {text[i : i + 2] for i in range(len(text) - 1)}


def similarity(a: str, b: str) -> float:
    """文字bigramのJaccard類似度を0-100で返す。日本語形態素解析器が無くても動く、
    「意味空間での距離」の簡易な代用(パチモン)。部分文字列一致による特別扱いはしない
    (短い数字列・一般語が長い語にたまたま含まれるだけで満点になるのを避けるため)。
    """
    if not a or not b:
        return 0.0
    bigrams_a = char_bigrams(a)
    bigrams_b = char_bigrams(b)
    union = len(bigrams_a | bigrams_b)
    if not union:
        return 0.0
    return 100.0 * len(bigrams_a & bigrams_b) / union


def best_similarity(keyword: str, ticket_keywords: set[str]) -> float:
    """keyword(turn側の1語)と、ticket_keywords(ticket summary側のキーワード集合)の
    中で最も近いものとの類似度を返す(集合同士の比較)。"""
    if not ticket_keywords:
        return 0.0
    return max(similarity(keyword, tk) for tk in ticket_keywords)


def open_corpus(db_path: str) -> tuple[sqlite3.Connection, int] | tuple[None, None]:
    """worklog_ticket_corpus_build.shが作るdocument frequency DBを開く。
    無ければ(None, None)を返し、呼び出し側は特異度による重み付けをしない(1.0固定)。
    """
    if not os.path.isfile(db_path):
        return None, None
    conn = sqlite3.connect(db_path)
    total_docs = conn.execute("SELECT total_docs FROM corpus_meta").fetchone()[0]
    return conn, total_docs


def specificity_weight(word: str, conn: sqlite3.Connection | None, total_docs: int | None) -> float:
    """単語の特異度を0-1で返す(多くのticketに出現する一般語ほど0に近く、稀な語ほど1に近い)。
    加算スムージング付きIDF(log((N+1)/(df+1)))を、最大値(log(N+1)、df=0相当)で正規化する。
    corpus DBが無い場合は重み付けをしない(常に1.0)。
    """
    if conn is None or not total_docs:
        return 1.0
    row = conn.execute("SELECT doc_count FROM word_freq WHERE word = ?", (word,)).fetchone()
    doc_count = row[0] if row else 0
    max_idf = math.log(total_docs + 1)
    if max_idf <= 0:
        return 1.0
    idf = math.log((total_docs + 1) / (doc_count + 1))
    return idf / max_idf


def suggest_rules(turns: list[dict], tickets: list[dict], threshold_min: float) -> list[dict]:
    ticket_keyword_sets = {ticket["key"]: extract_keyword_set(ticket.get("summary", "")) for ticket in tickets}
    corpus_conn, total_docs = open_corpus(CORPUS_DB_PATH)
    try:
        rules = []
        for keyword in extract_frequent_keywords(turns):
            weight = specificity_weight(keyword, corpus_conn, total_docs)
            best_ticket = None
            best_score = 0.0
            for ticket in tickets:
                score = best_similarity(keyword, ticket_keyword_sets[ticket["key"]]) * weight
                if score > best_score:
                    best_score, best_ticket = score, ticket
            if best_ticket and best_score > threshold_min:
                rules.append(
                    {
                        "_comment": f"自動生成(worklog_guess_ticket_rules_update_suggest.py): "
                        f"キーワード{keyword!r}と{best_ticket['key']}の類似度(特異度加重後){best_score:.0f}"
                        f"(特異度{weight:.2f})",
                        "if": {"property": "user", "regex": re.escape(keyword)},
                        "ticket": best_ticket["key"],
                    }
                )
        return rules
    finally:
        if corpus_conn is not None:
            corpus_conn.close()


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 2:
        fail(f"usage: {PROG} <turns_file> <rules_file>")
    turns_path, rules_path = args

    for path in (turns_path, rules_path):
        if not os.path.isfile(path):
            fail(f"file not found: {path}")

    generator = load_generator_config()
    tickets = fetch_tickets(SCRIPT_DIR)

    with open(turns_path, encoding="utf-8") as f:
        turns = json.load(f)
    with open(rules_path, encoding="utf-8") as f:
        rules_text = f.read()

    new_rules = suggest_rules(turns, tickets, generator["threshold_min"])

    print(rules_text, end="" if rules_text.endswith("\n") else "\n")
    for rule in new_rules:
        print(json.dumps(rule, ensure_ascii=False))

    print(f"{PROG}: {len(new_rules)}件のルール案を追加しました(既存{len(rules_text.splitlines())}行 + 新規)", file=sys.stderr)
    print(f"次にすべきこと: 目視確認の上、必要な行だけ{rules_path}へ反映してください", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
