#!/usr/bin/env python3
"""lhg-fullstack 确定性前端审计：32 条规则，零第三方依赖。

扫描目标目录的前端文件，输出 JSON 与人类可读报告；
有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 frontend_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创（思路受 impeccable/taste-skill 等开源项目启发，
未复制任何第三方原文）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-fullstack/frontend-audit"

SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", "coverage",
    "__pycache__", "vendor", ".turbo", "out",
}
SCAN_EXTS = {".tsx", ".jsx", ".ts", ".js", ".css", ".scss", ".html"}
TOKEN_FILE_RES = [re.compile(r"token", re.I), re.compile(r"theme", re.I),
                  re.compile(r"globals\.css$", re.I), re.compile(r"tailwind\.config", re.I)]


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line, snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


def is_token_file(path):
    base = os.path.basename(path)
    return any(r.search(base) for r in TOKEN_FILE_RES)


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------- 规则定义
# 每条规则：id / severity / category / title / detail / check(lines, text, path, ctx)

def _line_hits(rule_id, lines, text, path, ctx, pattern, flags=0):
    rule = _RULE_BY_ID[rule_id]
    rx = re.compile(pattern, flags)
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, i + 1, lines[i].strip()[:160], rule["detail"])
        for i, ln in enumerate(lines) if rx.search(ln)
    ]


RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity, "category": category,
             "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


# ---------------- 模板相（anti-slop） ----------------

@rule("FE-SLP-001", "blocker", "模板相", "紫粉渐变",
      "紫→粉/紫罗兰渐变是 AI 生成落地页最泛滥的配色，用户一眼可辨。改用品牌色系小面积点缀。")
def r_slp_001(lines, text, path, ctx):
    hits = _line_hits("FE-SLP-001", lines, text, path, ctx,
                      r"from-(purple|violet|fuchsia|pink)-\d|via-(purple|violet|fuchsia|pink)-\d|to-(purple|violet|fuchsia|pink)-\d")
    hits += _line_hits("FE-SLP-001", lines, text, path, ctx,
                       r"linear-gradient\([^)]*#(?:a855f7|8b5cf6|d946ef|ec4899|c084fc|e879f9|a78bfa)", re.I)
    return hits


@rule("FE-SLP-002", "blocker", "模板相", "霓虹暗黑模板",
      "纯黑背景配彩色发光阴影，除非产品本身是开发者工具/游戏，否则与真实业务不搭。")
def r_slp_002(lines, text, path, ctx):
    dark = re.search(r"bg-(black|neutral-9\d\d|zinc-9\d\d|slate-9\d\d|gray-900)\b", text)
    neon = re.search(r"shadow-(purple|violet|fuchsia|pink)|neon|text-glow|drop-shadow.*(purple|fuchsia)", text, re.I)
    if dark and neon:
        return [Finding("FE-SLP-002", "blocker", "模板相", "霓虹暗黑模板",
                        path, 1, dark.group(0)[:160],
                        "纯黑背景配彩色发光阴影，除非产品本身是开发者工具/游戏，否则与真实业务不搭。")]
    return []


@rule("FE-SLP-003", "warning", "模板相", "玻璃拟态滥用",
      "backdrop-blur 在单文件出现超过 5 次，大概率是装饰性堆砌。只在有真实理由处使用。")
def r_slp_003(lines, text, path, ctx):
    n = len(re.findall(r"backdrop-blur", text))
    if n > 5:
        return [Finding("FE-SLP-003", "warning", "模板相", "玻璃拟态滥用",
                        path, 1, "backdrop-blur 出现 %d 次" % n,
                        "backdrop-blur 在单文件出现超过 5 次，大概率是装饰性堆砌。只在有真实理由处使用。")]
    return []


@rule("FE-SLP-004", "warning", "模板相", "渐变标题字",
      "bg-clip-text 彩虹渐变标题可读性差且模板味重。标题用纯色，强调靠字重字号对比。")
def r_slp_004(lines, text, path, ctx):
    if "bg-clip-text" in text and "text-transparent" in text:
        i = next((i for i, ln in enumerate(lines) if "bg-clip-text" in ln), 0)
        return [Finding("FE-SLP-004", "warning", "模板相", "渐变标题字",
                        path, i + 1, lines[i].strip()[:160],
                        "bg-clip-text 彩虹渐变标题可读性差且模板味重。标题用纯色，强调靠字重字号对比。")]
    return []


@rule("FE-SLP-005", "blocker", "模板相", "疑似编造的用户评价",
      "检测到 testimonial 数据含典型编造话术。没有真实用户反馈就不要写评价区，或标为待补充。")
def r_slp_005(lines, text, path, ctx):
    if re.search(r"testimonial", text, re.I) and re.search(
            r"非常好用|强烈推荐|改变了我的|五星好评|★★★★★|用户都说好", text):
        i = next((i for i, ln in enumerate(lines) if re.search(r"testimonial", ln, re.I)), 0)
        return [Finding("FE-SLP-005", "blocker", "模板相", "疑似编造的用户评价",
                        path, i + 1, lines[i].strip()[:160],
                        "检测到 testimonial 数据含典型编造话术。没有真实用户反馈就不要写评价区，或标为待补充。")]
    return []


@rule("FE-SLP-006", "warning", "模板相", "疑似冒充的客户墙",
      "出现知名公司名且上下文像'客户/合作伙伴'展示。请确认确有合作，否则删除。")
def r_slp_006(lines, text, path, ctx):
    if re.search(r"深受.*信赖|trusted by|合作伙伴|客户墙", text) and re.search(
            r"Google|Microsoft|Apple|Tencent|腾讯|Alibaba|阿里|字节跳动|ByteDance|百度|华为", text):
        return [Finding("FE-SLP-006", "warning", "模板相", "疑似冒充的客户墙",
                        path, 1, "知名公司名出现在客户展示上下文",
                        "出现知名公司名且上下文像'客户/合作伙伴'展示。请确认确有合作，否则删除。")]
    return []


# ---------------- 设计令牌 ----------------

@rule("FE-TKN-001", "blocker", "设计令牌", "硬编码十六进制色值",
      "组件里直接写 #rrggbb。所有颜色必须走设计令牌（CSS 变量 / Tailwind theme）。")
def r_tkn_001(lines, text, path, ctx):
    if is_token_file(path):
        return []
    return _line_hits("FE-TKN-001", lines, text, path, ctx,
                      r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


@rule("FE-TKN-002", "blocker", "设计令牌", "硬编码 rgb/hsl 色值",
      "组件里直接写 rgb()/hsl()。颜色必须走设计令牌。")
def r_tkn_002(lines, text, path, ctx):
    if is_token_file(path):
        return []
    return _line_hits("FE-TKN-002", lines, text, path, ctx, r"\brgba?\([^)]*\)|\bhsla?\([^)]*\)")


@rule("FE-TKN-003", "warning", "设计令牌", "Tailwind 任意值泛滥",
      "单文件任意值类（text-[...]/w-[...]）超过 8 个，说明该沉淀为设计令牌或复用类。")
def r_tkn_003(lines, text, path, ctx):
    n = len(re.findall(r"(?:text|w|h|min-w|max-w|p|px|py|m|gap|rounded|bg|border|leading|tracking)-\[", text))
    if n > 8:
        return [Finding("FE-TKN-003", "warning", "设计令牌", "Tailwind 任意值泛滥",
                        path, 1, "任意值类出现 %d 次" % n,
                        "单文件任意值类（text-[...]/w-[...]）超过 8 个，说明该沉淀为设计令牌或复用类。")]
    return []


@rule("FE-TKN-004", "warning", "设计令牌", "硬编码字体",
      "直接写 font-family 或 font-[...]。字体走设计令牌统一管理。")
def r_tkn_004(lines, text, path, ctx):
    if is_token_file(path):
        return []
    return _line_hits("FE-TKN-004", lines, text, path, ctx, r"font-family\s*:|font-\[")


# ---------------- 内容诚实 ----------------

@rule("FE-HON-001", "blocker", "内容诚实", "lorem ipsum 残留",
      "占位文案未替换。用诚实的中性占位（灰块 + '待补充'），不要留拉丁文。")
def r_hon_001(lines, text, path, ctx):
    return _line_hits("FE-HON-001", lines, text, path, ctx, r"lorem ipsum", re.I)


@rule("FE-HON-002", "blocker", "内容诚实", "TODO/FIXME 残留",
      "代码里还有 TODO/FIXME/XXX/HACK。完工前清掉，或转成正式 issue。")
def r_hon_002(lines, text, path, ctx):
    return _line_hits("FE-HON-002", lines, text, path, ctx, r"\b(TODO|FIXME|XXX|HACK)\b")


@rule("FE-HON-003", "warning", "内容诚实", "空链接",
      'href="#" 或空 href 的"假按钮"。没目标就先不用 a 标签，或标待补充。')
def r_hon_003(lines, text, path, ctx):
    return _line_hits("FE-HON-003", lines, text, path, ctx, r'href="#"|href=""|href=\'\'')


@rule("FE-HON-004", "warning", "内容诚实", "占位图片服务",
      "用了外部占位图服务。上线前换成真实图片或诚实的中性占位。")
def r_hon_004(lines, text, path, ctx):
    return _line_hits("FE-HON-004", lines, text, path, ctx,
                      r"via\.placeholder\.com|placehold\.co|picsum\.photos|loremflickr")


# ---------------- 可访问性 ----------------

@rule("FE-A11Y-001", "blocker", "可访问性", "图片缺 alt",
      "<img>/<Image> 没有 alt。装饰图 alt 留空字符串，内容图写清含义。")
def r_a11y_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"<img\b", ln) and "alt=" not in ln:
            out.append(Finding("FE-A11Y-001", "blocker", "可访问性", "图片缺 alt",
                               path, i + 1, ln.strip()[:160],
                               "<img>/<Image> 没有 alt。装饰图 alt 留空字符串，内容图写清含义。"))
        if re.search(r"<Image\b", ln) and "alt=" not in ln:
            out.append(Finding("FE-A11Y-001", "blocker", "可访问性", "图片缺 alt",
                               path, i + 1, ln.strip()[:160],
                               "<img>/<Image> 没有 alt。装饰图 alt 留空字符串，内容图写清含义。"))
    return out


@rule("FE-A11Y-002", "warning", "可访问性", "div 冒充按钮",
      "div 套 onClick 做可点击元素。用原生 button/a，保证键盘可达。")
def r_a11y_002(lines, text, path, ctx):
    return _line_hits("FE-A11Y-002", lines, text, path, ctx, r"<div[^>]*onClick")


@rule("FE-A11Y-003", "warning", "可访问性", "输入框无标签",
      "<input> 缺少 aria-label 且附近无 label。读屏用户无法知道这是什么输入框。")
def r_a11y_003(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if "<input" in ln and "aria-label" not in ln and "aria-labelledby" not in ln:
            near = "\n".join(lines[max(0, i - 3):i + 1])
            if "<label" not in near:
                out.append(Finding("FE-A11Y-003", "warning", "可访问性", "输入框无标签",
                                   path, i + 1, ln.strip()[:160],
                                   "<input> 缺少 aria-label 且附近无 label。读屏用户无法知道这是什么输入框。"))
    return out


@rule("FE-A11Y-004", "warning", "可访问性", "图片无尺寸",
      "<img> 未声明宽高，会引起 CLS（累积布局偏移）。补 width/height 或用 next/image。")
def r_a11y_004(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"<img\b", ln) and "width" not in ln:
            out.append(Finding("FE-A11Y-004", "warning", "可访问性", "图片无尺寸",
                               path, i + 1, ln.strip()[:160],
                               "<img> 未声明宽高，会引起 CLS（累积布局偏移）。补 width/height 或用 next/image。"))
    return out


@rule("FE-A11Y-005", "warning", "可访问性", "对比度可疑",
      "浅色文字疑似落在浅色背景上。请实测对比度达到 WCAG AA（正文 4.5:1）。")
def r_a11y_005(lines, text, path, ctx):
    if re.search(r"text-(white|yellow-100|amber-100|lime-100|slate-100)\b", text) and \
       re.search(r"bg-(yellow|amber|lime)-(200|300|400)\b", text):
        return [Finding("FE-A11Y-005", "warning", "可访问性", "对比度可疑",
                        path, 1, "浅色文字 + 浅色背景并存",
                        "浅色文字疑似落在浅色背景上。请实测对比度达到 WCAG AA（正文 4.5:1）。")]
    return []


# ---------------- 响应式 ----------------

@rule("FE-RSP-001", "blocker", "响应式", "固定大宽度",
      "写死了 ≥900px 的固定宽度，移动端必横向溢出。改 max-w-* + 响应式断点。")
def r_rsp_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        for m in re.finditer(r"w-\[(\d+)px\]", ln):
            if int(m.group(1)) >= 900:
                out.append(Finding("FE-RSP-001", "blocker", "响应式", "固定大宽度",
                                   path, i + 1, ln.strip()[:160],
                                   "写死了 ≥900px 的固定宽度，移动端必横向溢出。改 max-w-* + 响应式断点。"))
    return out


@rule("FE-RSP-002", "warning", "响应式", "缺 viewport 声明",
      "Next.js 应用未声明 viewport，移动端缩放会错乱。在 layout metadata 中声明。")
def r_rsp_002(lines, text, path, ctx):
    base = os.path.basename(path)
    if base in ("layout.tsx", "layout.jsx", "layout.js", "_app.tsx", "_app.js"):
        if "viewport" not in text:
            return [Finding("FE-RSP-002", "warning", "响应式", "缺 viewport 声明",
                            path, 1, base,
                            "Next.js 应用未声明 viewport，移动端缩放会错乱。在 layout metadata 中声明。")]
    return []


@rule("FE-RSP-003", "warning", "响应式", "固定多列无响应式",
      "grid-cols-5 及以上未配响应式前缀，小屏会被挤爆。按断点递减列数。")
def r_rsp_003(lines, text, path, ctx):
    return _line_hits("FE-RSP-003", lines, text, path, ctx,
                      r"(?<![\w:-])grid-cols-([5-9]|1[0-2])\b")


# ---------------- 卫生 ----------------

@rule("FE-HYG-001", "blocker", "卫生", "dangerouslySetInnerHTML",
      "直接渲染 HTML，有 XSS 风险。必须用时先做 HTML 清洗并注释理由。")
def r_hyg_001(lines, text, path, ctx):
    return _line_hits("FE-HYG-001", lines, text, path, ctx, r"dangerouslySetInnerHTML")


@rule("FE-HYG-002", "blocker", "卫生", "console.log 残留",
      "调试输出未清理。提交前删掉，或换成正式日志。")
def r_hyg_002(lines, text, path, ctx):
    return _line_hits("FE-HYG-002", lines, text, path, ctx, r"console\.(log|debug|info)\(")


@rule("FE-HYG-003", "warning", "卫生", "key 用了 index",
      "列表 key={index} 在增删排序时会出渲染 bug。用稳定唯一 id。")
def r_hyg_003(lines, text, path, ctx):
    return _line_hits("FE-HYG-003", lines, text, path, ctx, r"key=\{(index|i|idx)\}")


@rule("FE-HYG-004", "warning", "卫生", "alert/confirm/prompt",
      "用了原生弹窗 API，体验差且不可定制。换成应用内对话框组件。")
def r_hyg_004(lines, text, path, ctx):
    return _line_hits("FE-HYG-004", lines, text, path, ctx, r"\b(alert|confirm|prompt)\(")


@rule("FE-HYG-005", "warning", "卫生", "!important",
      "CSS 里用了 !important，说明选择器权重已失控。重构选择器，不要加 important。")
def r_hyg_005(lines, text, path, ctx):
    if os.path.splitext(path)[1] in (".css", ".scss"):
        return _line_hits("FE-HYG-005", lines, text, path, ctx, r"!important")
    return []


@rule("FE-HYG-006", "nit", "卫生", "注释掉的代码",
      "大段注释掉的代码。删掉它，git 里找得回来。")
def r_hyg_006(lines, text, path, ctx):
    return _line_hits("FE-HYG-006", lines, text, path, ctx,
                      r"^\s*//\s*<(div|span|button|p|h1|section)|\{/\*.*<(div|span|button)")


# ---------------- 性能 ----------------

@rule("FE-PRF-001", "warning", "性能", "裸 img 标签",
      "Next.js 项目里直接用 <img>，放弃了图片优化。改用 next/image。")
def r_prf_001(lines, text, path, ctx):
    if not ctx.get("is_next"):
        return []
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"<img\b", ln):
            out.append(Finding("FE-PRF-001", "warning", "性能", "裸 img 标签",
                               path, i + 1, ln.strip()[:160],
                               "Next.js 项目里直接用 <img>，放弃了图片优化。改用 next/image。"))
    return out


@rule("FE-PRF-002", "warning", "性能", "link 直引字体",
      "用 <link> 直引 Google Fonts。改用 next/font，免除外部请求与布局抖动。")
def r_prf_002(lines, text, path, ctx):
    return _line_hits("FE-PRF-002", lines, text, path, ctx, r"<link[^>]*fonts\.googleapis\.com")


# ---------------- 安全 ----------------

@rule("FE-SEC-001", "blocker", "安全", "前端硬编码密钥",
      "前端代码里出现疑似密钥。密钥走环境变量/后端，前端 bundle 对所有人可见。")
def r_sec_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if "process.env" in ln or "import.meta.env" in ln:
            continue
        m = re.search(r"(api[_-]?key|secret|private[_-]?key|access[_-]?token)\s*[:=]\s*[\"']([^\"']+)[\"']", ln, re.I)
        if m and not re.search(r"xxx|your-|test|example|changeme|demo|placeholder", m.group(2), re.I):
            out.append(Finding("FE-SEC-001", "blocker", "安全", "前端硬编码密钥",
                               path, i + 1, ln.strip()[:60] + "...",
                               "前端代码里出现疑似密钥。密钥走环境变量/后端，前端 bundle 对所有人可见。"))
    return out


@rule("FE-SEC-002", "blocker", "安全", 'target="_blank" 无 rel',
      'target="_blank" 缺少 rel="noopener"，新页面可通过 window.opener 控制原页面。补上 rel。')
def r_sec_002(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if 'target="_blank"' in ln and "rel=" not in ln:
            out.append(Finding("FE-SEC-002", "blocker", "安全", 'target="_blank" 无 rel',
                               path, i + 1, ln.strip()[:160],
                               'target="_blank" 缺少 rel="noopener"，新页面可通过 window.opener 控制原页面。补上 rel。'))
    return out


@rule("FE-SLP-007", "warning", "模板相", "标题 emoji 堆砌",
      "标题行塞 2 个以上 emoji 是典型的 AI 模板味。标题靠文案本身吸引人，emoji 最多点缀 1 个。")
def r_slp_007(lines, text, path, ctx):
    out = []
    emoji_re = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]")
    for i, ln in enumerate(lines):
        if re.search(r"<h[12]\b", ln) and len(emoji_re.findall(ln)) >= 2:
            out.append(Finding("FE-SLP-007", "warning", "模板相", "标题 emoji 堆砌",
                               path, i + 1, ln.strip()[:160],
                               "标题行塞 2 个以上 emoji 是典型的 AI 模板味。标题靠文案本身吸引人，emoji 最多点缀 1 个。"))
    return out


@rule("FE-A11Y-006", "warning", "可访问性", "焦点样式被清零",
      "outline-none 去掉了键盘焦点可见性。改用 focus-visible 的自定义焦点环，不要直接清零。")
def r_a11y_006(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if "outline-none" in ln and "focus:" not in ln:
            out.append(Finding("FE-A11Y-006", "warning", "可访问性", "焦点样式被清零",
                               path, i + 1, ln.strip()[:160],
                               "outline-none 去掉了键盘焦点可见性。改用 focus-visible 的自定义焦点环，不要直接清零。"))
    return out


@rule("FE-HYG-007", "nit", "卫生", "魔法 z-index",
      "z-index 手写超大值（≥100）。用设计令牌的层级档位（如下拉/弹窗/通知），不要拍脑袋。")
def r_hyg_007(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        for m in re.finditer(r"z-\[(\d+)\]", ln):
            if int(m.group(1)) >= 100:
                out.append(Finding("FE-HYG-007", "nit", "卫生", "魔法 z-index",
                                   path, i + 1, ln.strip()[:160],
                                   "z-index 手写超大值（≥100）。用设计令牌的层级档位（如下拉/弹窗/通知），不要拍脑袋。"))
        m2 = re.search(r"z-index\s*:\s*(\d+)", ln)
        if m2 and int(m2.group(1)) >= 100:
            out.append(Finding("FE-HYG-007", "nit", "卫生", "魔法 z-index",
                               path, i + 1, ln.strip()[:160],
                               "z-index 手写超大值（≥100）。用设计令牌的层级档位（如下拉/弹窗/通知），不要拍脑袋。"))
    return out


# ---------------------------------------------------------------- 运行器

def run(target):
    files = collect_files(target)
    ctx = {"is_next": any(os.path.basename(f).startswith("next.config.") for f in files)}
    findings = []
    for path in files:
        text = read_text(path)
        lines = text.split("\n")
        rel = os.path.relpath(path, target)
        for r in RULES:
            try:
                for f in r["check"](lines, text, path, ctx) or []:
                    f.file = rel
                    findings.append(f)
            except Exception:
                continue  # 单条规则异常不影响整体
    return files, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-fullstack 确定性前端审计")
    ap.add_argument("--target", default=".", help="扫描目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"], default="blocker")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print("target 不是目录：%s" % args.target, file=sys.stderr)
        return 1

    files, findings = run(target)
    sev_rank = {"blocker": 3, "warning": 2, "nit": 1}
    counts = {"blocker": 0, "warning": 0, "nit": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    result = {
        "tool": TOOL,
        "version": VERSION,
        "target": args.target,
        "summary": {
            "files_scanned": len(files),
            "rules_run": len(RULES),
            "blocker": counts["blocker"],
            "warning": counts["warning"],
            "nit": counts["nit"],
        },
        "findings": [f.to_dict() for f in sorted(
            findings, key=lambda x: (-sev_rank.get(x.severity, 0), x.file, x.line))],
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        print("前端审计：扫描 %d 文件，运行 %d 条规则" % (s["files_scanned"], s["rules_run"]))
        print("blocker=%d warning=%d nit=%d" % (s["blocker"], s["warning"], s["nit"]))
        for f in result["findings"]:
            print("[%s][%s] %s:%d %s" % (
                f["severity"].upper(), f["rule_id"], f["file"], f["line"], f["title"]))
            print("    %s" % f["detail"])
            if f["snippet"]:
                print("    → %s" % f["snippet"])

    level = sev_rank[args.fail_on]
    bad = any(sev_rank.get(f.severity, 0) >= level for f in findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
