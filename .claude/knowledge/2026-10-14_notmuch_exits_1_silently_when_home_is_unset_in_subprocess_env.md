---
id: KB-000003
tags:
  - notmuch
  - Python
  - subprocess
  - 環境変数
  - 段差
related:
  - KB-000002
---

# notmuchはHOMEが無いと何も言わずにexit 1する（最小envを組むと踏む）

## 症状

`inbox_tag_apply.py` から `notmuch tag --batch` を呼ぶと、常に exit code 1。
**stderr は空**。stdout も空。エラーメッセージが一切出ない。

同じ内容を同じ設定ファイルでシェルから流すと成功する。

```bash
# 成功する
echo '+actionable -- id:"m1@example.com"' \
  | env NOTMUCH_CONFIG=/path/to/notmuch-config notmuch tag --batch; echo $?   # 0
```

## 原因（確定）

シェルの `env VAR=x cmd` は**既存の環境に追加する**ため `HOME` が残っていた。
Python の `subprocess.run(..., env={...})` は**環境を完全に置き換える**。

```python
env = {"NOTMUCH_CONFIG": config_path, "PATH": "/usr/bin:/bin"}  # HOMEが無い
```

notmuch は `NOTMUCH_CONFIG` が指定されていても `HOME` を参照する。
未設定だと診断メッセージを出さずに 1 を返す。`env -i` で再現する。

```bash
echo '+t -- id:"x"' | env -i NOTMUCH_CONFIG=... PATH=/usr/bin:/bin notmuch tag --batch; echo $?        # 1
echo '+t -- id:"x"' | env -i NOTMUCH_CONFIG=... PATH=/usr/bin:/bin HOME=$HOME notmuch tag --batch; echo $?  # 0
```

これは「バグは段差に湧く」の一例である。段差はシェルの env と Python の env の
**追加 vs 置換**という意味論の違いにある。

## 対処 / 復旧手順

最小 env を手で組まず、継承して上書きする。

```python
env = dict(os.environ)
env["NOTMUCH_CONFIG"] = config_path
```

## 検証方法

`~/imc/imc_tag_apply.py`（独立リポジトリ）を上記の形に直し、合成Maildir 5通に対して
タグ付与・冪等再実行・ルール削除時のタグ剥がしが期待通り動くことを確認済み。

## 備考

- stderr が空のまま非ゼロ終了するコマンドを見たら、まず env の欠落を疑う。
- 逆に「シェルでは動くのにスクリプトからは動かない」も同じ段差である。
- `env VAR=x cmd` と `env -i VAR=x cmd` を並べて試すのが最短の切り分けになる。
