#!/usr/bin/env python3
import json
import os
import re
import sys
from glob import glob

SYSTEM_TAG_PATTERN = re.compile(
    r'<(?:ide_selection|ide_opened_file|system-reminder|command-name)[^>]*>.*?</(?:ide_selection|ide_opened_file|system-reminder|command-name)>',
    re.DOTALL,
)


def extract_user_text(content):
    parts = []
    for block in content:
        if block.get('type') != 'text':
            continue
        text = SYSTEM_TAG_PATTERN.sub('', block.get('text', ''))
        text = text.strip()
        if text:
            parts.append(text)
    return '\n\n'.join(parts)


def extract_assistant_text(content):
    parts = []
    for block in content:
        if block.get('type') != 'text':
            continue
        text = block.get('text', '').strip()
        if text:
            parts.append(text)
    return '\n\n'.join(parts)


def convert(jsonl_path):
    messages = []
    with open(jsonl_path, encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            if obj.get('isSidechain'):
                continue
            t = obj.get('type')
            if t not in ('user', 'assistant'):
                continue
            content = obj.get('message', {}).get('content', [])
            if isinstance(content, str):
                content = [{'type': 'text', 'text': content}]
            if t == 'user':
                text = extract_user_text(content)
            else:
                text = extract_assistant_text(content)
            if text:
                messages.append((t, text))

    out = []
    for role, text in messages:
        heading = '## 私：' if role == 'user' else '## Claude:'
        out.append(f'{heading}\n{text}')

    print('\n\n'.join(out))


def list_sessions():
    projects_dir = os.path.expanduser('~/.claude/projects')
    # subagents/ holds forked-agent transcripts, not top-level sessions - excluded from the listing
    jsonl_files = [
        path
        for path in glob(os.path.join(projects_dir, '**', '*.jsonl'), recursive=True)
        if f'{os.sep}subagents{os.sep}' not in path
    ]

    sessions = []
    for path in jsonl_files:
        session_id = os.path.splitext(os.path.basename(path))[0]
        ai_title = ''
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    obj = json.loads(line)
                    if obj.get('type') == 'ai-title':
                        ai_title = obj.get('aiTitle', '')
        except Exception:
            continue
        # mtime = time of the last write to this session file (last-appended message)
        sessions.append((os.path.getmtime(path), session_id, ai_title))

    sessions.sort(reverse=True)

    col_id = max(len(s[1]) for s in sessions) if sessions else 36
    col_title = max((len(s[2]) for s in sessions), default=5)
    header = f"{'SESSION ID':<{col_id}}  {'TITLE'}"
    print(header)
    print('-' * (col_id + 2 + col_title))
    for _, session_id, title in sessions:
        print(f'{session_id:<{col_id}}  {title}')


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--list':
        list_sessions()
    elif len(sys.argv) == 2:
        convert(sys.argv[1])
    else:
        print(f'usage: {sys.argv[0]} <jsonl_path>', file=sys.stderr)
        print(f'       {sys.argv[0]} --list', file=sys.stderr)
        sys.exit(1)
