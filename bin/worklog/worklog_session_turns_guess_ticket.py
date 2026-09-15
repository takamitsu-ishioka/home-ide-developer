import json
import os
import re
import sys

PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def match_condition(cond, turn: dict) -> bool:
    if cond is True:
        return True
    if "and" in cond:
        return all(match_condition(c, turn) for c in cond["and"])
    if "or" in cond:
        return any(match_condition(c, turn) for c in cond["or"])
    if "not" in cond:
        return not match_condition(cond["not"], turn)
    if "property" in cond and "regex" in cond:
        value = turn.get(cond["property"])
        pattern = cond["regex"]
        if isinstance(value, str):
            return re.search(pattern, value) is not None
        if isinstance(value, list):
            return any(isinstance(v, str) and re.search(pattern, v) for v in value)
        return False
    fail(f"不正な条件です(and/or/not/property+regexのいずれでもありません): {cond!r}")


def load_rules(path: str) -> list[dict]:
    """ルールファイルを読む。1行1JSON(JSONL)・複数行に渡る整形済みJSONのどちらでも、
    空白区切りで連続するJSON値として読み取れる(jsonl_pretty_print_convert.shで
    整形しても読めるようにするため)。
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        fail(f"{path}を読み取れません: {e}")

    decoder = json.JSONDecoder()
    rules = []
    idx = 0
    length = len(text)
    while True:
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break
        lineno = text.count("\n", 0, idx) + 1
        try:
            rule, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError as e:
            fail(f"{path}:{lineno}: JSONとして読み取れません: {e}")
        if "if" not in rule or "ticket" not in rule:
            fail(f"{path}:{lineno}: 'if'と'ticket'の両方が必要です: {rule!r}")
        rules.append(rule)
        idx = end
    return rules


def resolve_ticket(turn: dict, rules: list[dict]) -> str | None:
    """ルールを先頭から順に評価し、最初にマッチしたルールのticketを返す(先勝ち。
    1件もマッチしなければNone)。"if": trueは無条件マッチの通常ルールとして扱う
    (特別扱いしない。ファイルの末尾に置けば「他に何もマッチしなければこれ」という
    最低優先度のルールとして機能する)。
    """
    for rule in rules:
        if match_condition(rule["if"], turn):
            return rule["ticket"]
    return None


def apply_rules(turns: list[dict], rules: list[dict]) -> int:
    """ルールをturnsへ順に適用する(turnsを直接書き換える)。戻り値は変更件数。

    このスクリプトは、turnの既存プロパティ(cwd/repo/ticket/user/agent)だけを見て
    ルールを適用する以外の推論を一切行わない。マッチするルールが無ければticketは
    変更しない(cwd解決済みの値であれ、regularizeで付与された特殊ticket
    (_nondeterministic_・_gap_等)であれ、そのまま素通りする)。休憩の特別扱い・
    継続・フォールバック階層といった状態を持つ拡張は持たせない。特殊ticketを
    実ticketへ変換するのはルールの責務であり、ルールで解決できなければ
    worklog_lint.shが検知し、人間が解決する。
    """
    changed = 0

    for turn in turns:
        original = turn.get("ticket")
        matched = resolve_ticket(turn, rules)
        if matched is not None:
            turn["ticket"] = matched
        if turn.get("ticket") != original:
            changed += 1

    return changed


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 1:
        fail(f"usage: {PROG} <rules_file>")
    rules = load_rules(args[0])

    try:
        turns = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        fail(f"stdinのJSONを読み取れません: {e}")

    changed = apply_rules(turns, rules)

    print(json.dumps(turns, ensure_ascii=False))
    print(f"{PROG}: {len(turns)}件中{changed}件のticketを書き換えました({len(rules)}ルール)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
