#!/usr/bin/env python3
"""lhg-rental 硬门②：写入疑似租赁合同文本时，提醒跑审计 + 核对三必须。

触发：PostToolUse / Write|Edit。只看写入的文件名与内容是否像租赁合同，
不是则静默放行；是则给出一次性提醒（additionalContext）。

逃生方式：LHG_RENTAL_HOOKS_OFF=1（本次会话不再提醒），
或 /plugin disable lhg-rental。

设计原则：内部出错 fail-open；零第三方依赖。
"""

import json
import os
import re
import sys

NAME_RES = [re.compile(p) for p in
            (r"合同", r"contract", r"租赁", r"rental", r"租房", r"补充协议")]
CONTENT_RES = [re.compile(p) for p in
               (r"租赁合同", r"出租人", r"承租人", r"押金", r"月租金")]


def main() -> int:
    if os.environ.get("LHG_RENTAL_HOOKS_OFF") == "1":
        return 0
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # fail-open

    tool_input = payload.get("tool_input", {}) or {}
    path = tool_input.get("file_path", "") or ""
    base = os.path.basename(path)

    looks_like = any(r.search(base) for r in NAME_RES)
    if not looks_like and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                head = f.read(4000)
            looks_like = sum(1 for r in CONTENT_RES if r.search(head)) >= 2
        except Exception:
            return 0  # fail-open

    if not looks_like:
        return 0

    msg = (
        "lhg-rental 提醒：你刚写入的文件疑似租赁合同文本。签字前请跑一遍审计：\n"
        "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/contract_audit.py "
        "--target <目录> --format text\n"
        "并核对三必须：①押金≤1个月租金 ②出租人身份+房屋权属可验证 "
        "③《交接清单》附件齐全。本提醒非法律意见。"
    )
    out = {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                 "additionalContext": msg}}
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
