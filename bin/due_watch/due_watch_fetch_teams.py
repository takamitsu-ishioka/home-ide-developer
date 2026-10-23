"""imc が Maildir に保存した Teams メッセージを読み、交換形式のJSON配列を stdout へ出す。
due_watch_fetch_teams.sh から呼ぶ。引数: <imc_dir>。

imc との契約(imc の公開出力だけを使う):
  - imc_mail_list.sh <query> json の各レコードの path(mail_root = <imc_dir>/_var/maildir からの相対)
  - 1メッセージ1ファイル(RFC 5322)。ヘッダ X-Imc-Team / X-Imc-Channel /
    X-Imc-Addressed-To-Me(Graph のメンション構造で判定済み)、本文 = 投稿本文 + 空行 + Teams のリンク
対象: teams_channels.tsv のチャネル、直近 MAX_AGE_DAYS 日。

契約(poll に対して):
  - imc の一覧が取れない => exit 1(fetch 失敗。poll は teams を飛ばし、既存キャッシュを消さない)
  - 対象0件              => [] を出して exit 0(「今は Teams 案件なし」= 正常)
"""

import email
import email.utils
import email.policy
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

import due_watch_lib as lib

PROG = os.path.basename(__file__)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(SCRIPT_DIR, "teams_channels.local.tsv")
MAX_AGE_DAYS = 7
SUMMARY_MAX = 120


def fail(msg: str) -> None:
    print(f"{PROG}: {msg}", file=sys.stderr)
    sys.exit(1)


def read_channels() -> set:
    channels = set()
    with open(CHANNELS_FILE, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) != 2 or not all(cols):
                fail(f"{CHANNELS_FILE} {n}行目が team<TAB>channel ではありません: {line!r}")
            channels.add((cols[0], cols[1]))
    if not channels:
        fail(f"{CHANNELS_FILE} にチャネルがありません")
    return channels


def split_body(body: str):
    """imc の本文 = 投稿本文 + 空行 + リンク。末尾の https 行をリンクとして分ける。"""
    lines = body.rstrip("\n").split("\n")
    url = None
    if lines and lines[-1].startswith("https://"):
        url = lines.pop()
    return " ".join(" ".join(lines).split()), url


def to_exchange(msg, message_id: str):
    frm = str(msg.get("From", ""))
    sender = email.utils.parseaddr(frm)[0] or frm
    chat = str(msg.get("X-Imc-Channel", ""))
    part = msg.get_body(preferencelist=("plain",))
    text, url = split_body(part.get_content() if part else "")
    head = " ".join(p for p in (f"[{chat}]" if chat else "", f"{sender}:" if sender else "") if p)
    summary = f"{head} {text}".strip() or "(本文なし)"
    if len(summary) > SUMMARY_MAX:
        summary = summary[: SUMMARY_MAX - 1] + "…"
    posted = email.utils.parsedate_to_datetime(str(msg["Date"])).astimezone(lib.JST)
    return {
        "source": "teams",
        # imc の Message-ID のローカル部(<メッセージid>.<チャネルhash>)。Teams のメッセージ id は
        # 作成時刻のミリ秒なので、チャネルをまたぐと衝突しうる。チャネル hash 付きで一意にする
        "id": message_id.split("@", 1)[0],
        "summary": summary,
        "deadline": None,
        "url": url,
        "posted_at": posted.isoformat(timespec="seconds"),
        "addressed_to_me": str(msg.get("X-Imc-Addressed-To-Me", "")).lower() == "true",
    }


def main() -> None:
    imc_dir = sys.argv[1]
    channels = read_channels()
    cutoff = lib.now_jst() - timedelta(days=MAX_AGE_DAYS)
    query = f"folder:/teams-.*/ and date:@{int(cutoff.timestamp())}.."
    result = subprocess.run([os.path.join(imc_dir, "imc_mail_list.sh"), query, "json"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        fail("imc_mail_list.sh が失敗しました")
    rows = json.loads(result.stdout or "[]")

    mail_root = os.path.join(imc_dir, "_var", "maildir")
    records, other = [], 0
    for row in rows:
        try:
            with open(os.path.join(mail_root, row["path"]), "rb") as f:
                msg = email.message_from_binary_file(f, policy=email.policy.default)
        except OSError:
            continue  # 一覧の後に移動された(cur/ への移動等)。次回拾われる
        if (str(msg.get("X-Imc-Team", "")), str(msg.get("X-Imc-Channel", ""))) not in channels:
            other += 1
            continue
        records.append(to_exchange(msg, row["message_id"]))

    try:
        lib.validate_exchange(records)
    except ValueError as e:
        fail(f"生成した交換形式が不正です(imc の形式変更?): {e}")
    print(json.dumps(records, ensure_ascii=False))
    print(f"{PROG}: imc の Teams {len(rows)}件(直近{MAX_AGE_DAYS}日) => {len(records)}件"
          f"(対象外チャネル {other}件)", file=sys.stderr)


if __name__ == "__main__":
    main()
