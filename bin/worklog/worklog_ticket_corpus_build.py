import os
import re
import sqlite3
import sys
from collections import Counter

import worklog_jira_query

PROG = os.path.basename(__file__)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "_ticket_corpus.sqlite3")
KEYWORD_RE = re.compile(r"[゠-ヿ一-鿿]{2,}|[A-Za-z0-9][A-Za-z0-9_-]{2,}")


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def fetch_issue_texts(jql: str, email: str, token: str) -> list[str]:
    """jqlにマッチする全issueについて、summary+description(ADFはプレーンテキスト化)を
    結合した1本のテキストを、issueごとに1件返す。
    """
    body = {"jql": jql, "fields": ["summary", "description"], "maxResults": 100}
    texts = []
    while True:
        data = worklog_jira_query.api_post("/rest/api/3/search/jql", email, token, body)
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            summary = fields.get("summary", "") or ""
            description = worklog_jira_query.adf_text(fields.get("description") or "")
            texts.append(f"{summary}\n{description}")
        if data.get("isLast", True) or not data.get("nextPageToken"):
            break
        body["nextPageToken"] = data["nextPageToken"]
    return texts


def build_doc_frequency(texts: list[str]) -> Counter:
    """キーワードごとに、それを含むissueの件数(document frequency)を数える。"""
    doc_freq: Counter[str] = Counter()
    for text in texts:
        keywords = set(KEYWORD_RE.findall(text))
        doc_freq.update(keywords)
    return doc_freq


def write_db(path: str, total_docs: int, doc_freq: Counter) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("DROP TABLE IF EXISTS word_freq")
        conn.execute("DROP TABLE IF EXISTS corpus_meta")
        conn.execute("CREATE TABLE corpus_meta (total_docs INTEGER NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE word_freq (word TEXT PRIMARY KEY, doc_count INTEGER NOT NULL)")
        conn.execute(
            "INSERT INTO corpus_meta (total_docs, updated_at) VALUES (?, datetime('now'))",
            (total_docs,),
        )
        conn.executemany("INSERT INTO word_freq (word, doc_count) VALUES (?, ?)", doc_freq.items())
        conn.commit()
    finally:
        conn.close()


def confirm_start() -> bool:
    print("corpusを再構築しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
    answer = sys.stdin.readline()
    if not answer:
        print("Cancelled: no input available (non-interactive)", file=sys.stderr)
        return False
    return answer.strip().lower() in ("", "y", "yes")


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    confirm = "--confirm" in args
    positional = [a for a in args if a not in ("--dry-run", "--confirm")]

    if len(positional) != 1:
        fail(f"usage: {PROG} <jql> [--dry-run] [--confirm]")
    jql = positional[0]

    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")

    print("入力:", file=sys.stderr)
    print(f"  jql   : {jql}", file=sys.stderr)
    print(f"  出力先: {DB_PATH}", file=sys.stderr)
    print(file=sys.stderr)

    try:
        texts = fetch_issue_texts(jql, email, token)
    except worklog_jira_query.JiraApiError as e:
        fail(str(e))

    doc_freq = build_doc_frequency(texts)
    total_docs = len(texts)

    print(f"{PROG}: {total_docs}件のissueから{len(doc_freq)}種類のキーワードを集計しました", file=sys.stderr)

    if dry_run:
        print("[dry-run] DBへの書き込みは行いません", file=sys.stderr)
        return 0

    if confirm and not confirm_start():
        print("Cancelled.", file=sys.stderr)
        return 1

    write_db(DB_PATH, total_docs, doc_freq)
    print(f"{PROG}: {DB_PATH}へ書き込みました", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
