#!/usr/bin/env python3
"""lhg-fullstack 确定性后端审计：24 条规则，零第三方依赖。

扫描目标目录的后端文件（API 路由、服务、脚本），输出 JSON 与人类可读报告；
有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 backend_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创（思路受 supabase/vercel agent-skills 与 OWASP
API 安全实践启发，未复制任何第三方原文）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-fullstack/backend-audit"

SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", "coverage",
    "__pycache__", "vendor", ".turbo", "out", "fixtures",
}
SCAN_EXTS = {".ts", ".tsx", ".js", ".jsx", ".py"}
PLACEHOLDER_RE = re.compile(r"xxx|your-|changeme|example|test|demo|placeholder|password123", re.I)


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


def _line_hits(rule_id, lines, text, path, ctx, pattern, flags=0):
    rule = _RULE_BY_ID[rule_id]
    rx = re.compile(pattern, flags)
    return [
        Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                path, i + 1, lines[i].strip()[:160], rule["detail"])
        for i, ln in enumerate(lines) if rx.search(ln)
    ]


def _text_hits(rule_id, text, path, lines, pattern, flags=0):
    """在全文上匹配（可跨行），按匹配起始位置算行号。"""
    rule = _RULE_BY_ID[rule_id]
    rx = re.compile(pattern, flags)
    out = []
    for m in rx.finditer(text):
        lineno = text[:m.start()].count("\n") + 1
        snippet = lines[lineno - 1].strip()[:160] if lineno - 1 < len(lines) else ""
        out.append(Finding(rule["id"], rule["severity"], rule["category"], rule["title"],
                           path, lineno, snippet, rule["detail"]))
    return out


RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity,
             "category": category, "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


# ---------------- 安全基线 ----------------

@rule("BE-SEC-001", "blocker", "安全", "硬编码密钥",
      "代码里直接写密钥/密码/token。走环境变量，仓库里只留 .env.example 模板。")
def r_sec_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if "process.env" in ln or "os.environ" in ln or "os.getenv" in ln:
            continue
        m = re.search(
            r"\b(api_key|apikey|secret|password|passwd|private_key|client_secret|db_password|db_pass)\b"
            r"\s*[:=]\s*[\"']([^\"']+)[\"']", ln, re.I)
        if m and len(m.group(2)) >= 4 and not PLACEHOLDER_RE.search(m.group(2)):
            out.append(Finding("BE-SEC-001", "blocker", "安全", "硬编码密钥",
                               path, i + 1, ln.strip()[:40] + "...",
                               "代码里直接写密钥/密码/token。走环境变量，仓库里只留 .env.example 模板。"))
    out += _line_hits("BE-SEC-001", lines, text, path, ctx, r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}")
    return out


@rule("BE-SEC-002", "blocker", "安全", "SQL 字符串拼接",
      "SQL 语句里拼变量，注入风险。改参数化查询 / ORM 参数绑定。")
def r_sec_002(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", ln, re.I):
            if re.search(r"\+\s*\w|__\w+__|\$\{|\"\.format\(|%\s*\(|f[\"']", ln):
                out.append(Finding("BE-SEC-002", "blocker", "安全", "SQL 字符串拼接",
                                   path, i + 1, ln.strip()[:160],
                                   "SQL 语句里拼变量，注入风险。改参数化查询 / ORM 参数绑定。"))
    return out


@rule("BE-SEC-003", "blocker", "安全", "明文密码处理",
      "密码直接比较或直接入库。用 bcrypt/argon2 哈希后存储，登录时哈希比较。")
def r_sec_003(lines, text, path, ctx):
    out = _line_hits("BE-SEC-003", lines, text, path, ctx,
                     r"\bpassword\b\s*(===|==)\s*")
    out += _line_hits("BE-SEC-003", lines, text, path, ctx,
                      r"password\s*:\s*(req\.body\.password|request\.password|body\.password)\b")
    return out


@rule("BE-SEC-004", "blocker", "安全", "无条件删除/更新",
      "DELETE/UPDATE 不带 WHERE，或 deleteMany() 传空条件。先写 WHERE 再写 DELETE，顺序不能反。")
def r_sec_004(lines, text, path, ctx):
    out = _line_hits("BE-SEC-004", lines, text, path, ctx, r"deleteMany\(\s*(\{\s*\})?\s*\)")
    for i, ln in enumerate(lines):
        if re.search(r"\bDELETE\s+FROM\s+\w+\s*;?\s*$", ln.strip(), re.I):
            out.append(Finding("BE-SEC-004", "blocker", "安全", "无条件删除/更新",
                               path, i + 1, ln.strip()[:160],
                               "DELETE/UPDATE 不带 WHERE，或 deleteMany() 传空条件。先写 WHERE 再写 DELETE，顺序不能反。"))
    return out


@rule("BE-SEC-005", "blocker", "安全", ".env 疑似未被忽略",
      "仓库根有 .env 但 .gitignore 未忽略它，密钥会被提交。立即检查 git 状态。")
def r_sec_005(lines, text, path, ctx):
    if os.path.basename(path) != ".env":
        return []
    gi = os.path.join(ctx["target"], ".gitignore")
    ignored = False
    if os.path.isfile(gi):
        ignored = any(re.match(r"^\s*\.env(\s|$)", ln) for ln in read_text(gi).split("\n"))
    if not ignored:
        return [Finding("BE-SEC-005", "blocker", "安全", ".env 疑似未被忽略",
                        path, 1, ".env",
                        "仓库根有 .env 但 .gitignore 未忽略它，密钥会被提交。立即检查 git 状态。")]
    return []


@rule("BE-SEC-006", "warning", "安全", "CORS 通配",
      "Access-Control-Allow-Origin 为 *。收紧到明确域名，纯公开 API 除外。")
def r_sec_006(lines, text, path, ctx):
    return _line_hits("BE-SEC-006", lines, text, path, ctx,
                      r"Access-Control-Allow-Origin[\"']?\s*[:=]\s*[\"']\*|origin\s*:\s*[\"']\*['\"]")


@rule("BE-SEC-007", "warning", "安全", "敏感信息进日志",
      "日志里出现 password/secret/token。日志脱敏后再记。")
def r_sec_007(lines, text, path, ctx):
    return _line_hits("BE-SEC-007", lines, text, path, ctx,
                      r"console\.(log|info|debug|warn|error)\([^)]*(password|secret|token|authorization|api_key)",
                      re.I)


@rule("BE-SEC-008", "warning", "安全", "Math.random 用于安全场景",
      "Math.random 不可预测性不够，不能用于 token/密码/会话。改密码学安全随机数。")
def r_sec_008(lines, text, path, ctx):
    if "Math.random" in text and re.search(r"token|password|secret|session", text, re.I):
        i = next((i for i, ln in enumerate(lines) if "Math.random" in ln), 0)
        return [Finding("BE-SEC-008", "warning", "安全", "Math.random 用于安全场景",
                        path, i + 1, lines[i].strip()[:160],
                        "Math.random 不可预测性不够，不能用于 token/密码/会话。改密码学安全随机数。")]
    return []


@rule("BE-SEC-009", "warning", "安全", "返回密码哈希",
      "接口返回里带了 password_hash。查询时剔除敏感字段再返回。")
def r_sec_009(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"password_hash|hashedPassword", ln) and re.search(r"return|json\(", ln):
            out.append(Finding("BE-SEC-009", "warning", "安全", "返回密码哈希",
                               path, i + 1, ln.strip()[:160],
                               "接口返回里带了 password_hash。查询时剔除敏感字段再返回。"))
    return out


# ---------------- API 设计 ----------------

@rule("BE-API-001", "warning", "API 设计", "错误形状不统一",
      "错误直接返回字符串。统一为 {code, message} 形状，code 用大写下划线。")
def r_api_001(lines, text, path, ctx):
    return _line_hits("BE-API-001", lines, text, path, ctx, r"\.json\(\{\s*error\s*:\s*[\"']")


@rule("BE-API-002", "warning", "API 设计", "列表查询无分页",
      "findMany()/SELECT 无 take/limit。所有列表接口必须分页，limit 默认 20、最大 200。")
def r_api_002(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if "findMany(" in ln:
            # 按括号配平收集完整调用块，再判断有无分页参数
            depth = 0
            block_lines = []
            for k in range(i, min(i + 15, len(lines))):
                block_lines.append(lines[k])
                depth += lines[k].count("(") - lines[k].count(")")
                if depth <= 0 and k > i:
                    break
            block = "\n".join(block_lines)
            if not re.search(r"\btake\b|\bcursor\b|\bskip\b", block):
                out.append(Finding("BE-API-002", "warning", "API 设计", "列表查询无分页",
                                   path, i + 1, ln.strip()[:160],
                                   "findMany()/SELECT 无 take/limit。所有列表接口必须分页，limit 默认 20、最大 200。"))
        elif re.search(r"['\"`]\s*SELECT\b", ln, re.I) and "LIMIT" not in ln.upper():
            out.append(Finding("BE-API-002", "warning", "API 设计", "列表查询无分页",
                               path, i + 1, ln.strip()[:160],
                               "findMany()/SELECT 无 take/limit。所有列表接口必须分页，limit 默认 20、最大 200。"))
    return out


@rule("BE-API-003", "warning", "API 设计", "错误走了 200",
      "错误响应用了 200 状态码。按语义用 400/401/403/404/409/422/429/500。")
def r_api_003(lines, text, path, ctx):
    return _line_hits("BE-API-003", lines, text, path, ctx,
                      r"error.{0,80}status\s*:\s*200|status\s*:\s*200.{0,80}error")


@rule("BE-API-004", "warning", "API 设计", "async handler 缺 try/catch",
      "异步接口函数体内无 try/catch，未捕获异常会变成 500 裸奔。包一层并走统一错误形状。")
def r_api_004(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.search(r"export\s+async\s+function\s+(GET|POST|PUT|PATCH|DELETE)\b", ln):
            end = len(lines)
            for k in range(i + 1, min(i + 80, len(lines))):
                if re.match(r"export\s+", lines[k]):
                    end = k
                    break
            block = "\n".join(lines[i:end])
            if "try" not in block:
                out.append(Finding("BE-API-004", "warning", "API 设计", "async handler 缺 try/catch",
                                   path, i + 1, ln.strip()[:160],
                                   "异步接口函数体内无 try/catch，未捕获异常会变成 500 裸奔。包一层并走统一错误形状。"))
    return out


@rule("BE-API-005", "nit", "API 设计", "创建接口无幂等",
      "POST 创建接口未见幂等键处理。建议支持 Idempotency-Key 头，防重复创建。")
def r_api_005(lines, text, path, ctx):
    if re.search(r"export\s+async\s+function\s+POST\b", text) and \
       "idempotency" not in text.lower():
        i = next((i for i, ln in enumerate(lines)
                  if re.search(r"export\s+async\s+function\s+POST\b", ln)), 0)
        return [Finding("BE-API-005", "nit", "API 设计", "创建接口无幂等",
                        path, i + 1, lines[i].strip()[:160],
                        "POST 创建接口未见幂等键处理。建议支持 Idempotency-Key 头，防重复创建。")]
    return []


@rule("BE-API-006", "warning", "API 设计", "原始错误透出给客户端",
      "把 error.message/error 对象直接返回给客户端，会泄露堆栈与内部信息。转统一错误形状。")
def r_api_006(lines, text, path, ctx):
    return _line_hits("BE-API-006", lines, text, path, ctx,
                      r"\.json\(\s*(error|err)\s*\)|error\s*:\s*error\.message|message\s*:\s*err\.message")


# ---------------- 数据库 ----------------

@rule("BE-DB-001", "warning", "数据库", "疑似 N+1 查询",
      "循环体内 await 数据库查询。改批量查询（where in / join），一次取完。")
def r_db_001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        if re.match(r"\s*for\s*\(", ln):
            window = "\n".join(lines[i:i + 12])
            if re.search(r"await\s+[\w.]*\.(find|query|select|get)\w*\(", window):
                out.append(Finding("BE-DB-001", "warning", "数据库", "疑似 N+1 查询",
                                   path, i + 1, ln.strip()[:160],
                                   "循环体内 await 数据库查询。改批量查询（where in / join），一次取完。"))
    return out


@rule("BE-DB-002", "warning", "数据库", "SELECT *",
      "SELECT * 会拖回无用列（含敏感字段风险）。明确列出需要的列。")
def r_db_002(lines, text, path, ctx):
    return _line_hits("BE-DB-002", lines, text, path, ctx, r"\bSELECT\s+\*", re.I)


@rule("BE-DB-003", "warning", "数据库", "用了 Supabase 但未见 RLS",
      "项目用 Supabase 但扫描范围内未见 RLS 相关代码。多用户表必须开行级安全并写越权测试。")
def r_db_003(lines, text, path, ctx):
    if ctx.get("_rls_checked"):
        return []
    ctx["_rls_checked"] = True
    if ctx.get("uses_supabase") and not ctx.get("has_rls"):
        return [Finding("BE-DB-003", "warning", "数据库", "用了 Supabase 但未见 RLS",
                        ctx["target"], 1, "project-level",
                        "项目用 Supabase 但扫描范围内未见 RLS 相关代码。多用户表必须开行级安全并写越权测试。")]
    return []


# ---------------- 卫生 ----------------

@rule("BE-HYG-001", "warning", "卫生", "console.log 残留",
      "调试输出未清理。提交前删掉，或换成正式日志。")
def r_hyg_001(lines, text, path, ctx):
    return _line_hits("BE-HYG-001", lines, text, path, ctx, r"console\.(log|debug|info)\(")


@rule("BE-HYG-002", "blocker", "卫生", "错误被吞没",
      "空 catch / except: pass，把错误吃了。至少记日志，业务错误走统一错误形状返回。")
def r_hyg_002(lines, text, path, ctx):
    out = _text_hits("BE-HYG-002", text, path, lines, r"catch\s*(\([^)]*\))?\s*\{\s*\}")
    out += _line_hits("BE-HYG-002", lines, text, path, ctx, r"except[^:]*:\s*pass\s*$")
    out += _line_hits("BE-HYG-002", lines, text, path, ctx, r"\.catch\(\s*\(\s*\)\s*=>\s*\{\s*\}\s*\)")
    return out


@rule("BE-HYG-003", "warning", "卫生", "debugger 残留",
      "debugger 语句未删。提交前清掉。")
def r_hyg_003(lines, text, path, ctx):
    return _line_hits("BE-HYG-003", lines, text, path, ctx, r"\bdebugger\b")


@rule("BE-HYG-004", "warning", "卫生", "硬编码 localhost",
      "代码里写死 http://localhost，上生产会炸。走环境变量区分环境。")
def r_hyg_004(lines, text, path, ctx):
    if "test" in path.lower():
        return []
    return _line_hits("BE-HYG-004", lines, text, path, ctx, r"http://localhost")


# ---------------- 输入校验 ----------------

@rule("BE-VAL-001", "warning", "输入校验", "读 body 无校验",
      "读了请求 body 但文件内未见 schema 校验（zod/yup/joi 等）。所有外部输入先校验再用。")
def r_val_001(lines, text, path, ctx):
    reads_body = re.search(r"await\s+req\.json\(\)|req\.body\b", text)
    has_validator = re.search(r"\bzod\b|\.parse\(|\.safeParse\(|validator\b|joi\b|yup\b", text, re.I)
    if reads_body and not has_validator:
        i = next((i for i, ln in enumerate(lines)
                  if re.search(r"await\s+req\.json\(\)|req\.body\b", ln)), 0)
        return [Finding("BE-VAL-001", "warning", "输入校验", "读 body 无校验",
                        path, i + 1, lines[i].strip()[:160],
                        "读了请求 body 但文件内未见 schema 校验（zod/yup/joi 等）。所有外部输入先校验再用。")]
    return []


@rule("BE-VAL-002", "warning", "输入校验", "动态路由参数未校验",
      "用了 params.xxx 但未见校验。路径参数同样是外部输入，先校验再用。")
def r_val_002(lines, text, path, ctx):
    if re.search(r"params\.\w+", text) and not re.search(
            r"\bzod\b|\.parse\(|validator\b|Number\.is|isNaN", text, re.I):
        i = next((i for i, ln in enumerate(lines) if re.search(r"params\.\w+", ln)), 0)
        return [Finding("BE-VAL-002", "warning", "输入校验", "动态路由参数未校验",
                        path, i + 1, lines[i].strip()[:160],
                        "用了 params.xxx 但未见校验。路径参数同样是外部输入，先校验再用。")]
    return []


def _handler_blocks(lines):
    """切出每个 export async function Handler 的代码块：(起始行号, 方法名, 块文本)。"""
    blocks = []
    starts = [(i, m.group(1)) for i, ln in enumerate(lines)
              for m in [re.search(r"export\s+async\s+function\s+(GET|POST|PUT|PATCH|DELETE)\b", ln)] if m]
    for idx, (i, name) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        blocks.append((i + 1, name, "\n".join(lines[i:end])))
    return blocks


@rule("BE-SEC-010", "warning", "安全", "JWT 无过期时间",
      "签发 token 未设 expiresIn，泄露后长期有效。所有 token 必须设过期时间，刷新 token 另算。")
def r_sec_010(lines, text, path, ctx):
    if re.search(r"jsonwebtoken|jwt\.sign\(", text) and "expiresIn" not in text:
        i = next((i for i, ln in enumerate(lines)
                  if re.search(r"jsonwebtoken|jwt\.sign\(", ln)), 0)
        return [Finding("BE-SEC-010", "warning", "安全", "JWT 无过期时间",
                        path, i + 1, lines[i].strip()[:160],
                        "签发 token 未设 expiresIn，泄露后长期有效。所有 token 必须设过期时间，刷新 token 另算。")]
    return []


@rule("BE-API-007", "warning", "API 设计", "GET 接口读 body",
      "GET handler 里读 req.json()/req.body。GET 不应带 body，参数走 querystring。")
def r_api_007(lines, text, path, ctx):
    out = []
    for lineno, name, block in _handler_blocks(lines):
        if name == "GET" and re.search(r"await\s+req\.json\(\)|req\.body\b", block):
            out.append(Finding("BE-API-007", "warning", "API 设计", "GET 接口读 body",
                               path, lineno, "export async function GET",
                               "GET handler 里读 req.json()/req.body。GET 不应带 body，参数走 querystring。"))
    return out


@rule("BE-DB-004", "warning", "数据库", "多写操作无事务",
      "同一 handler 内 2 次以上写操作（create/update/delete/upsert）且无事务，一个失败会留脏数据。包 transaction。")
def r_db_004(lines, text, path, ctx):
    out = []
    for lineno, name, block in _handler_blocks(lines):
        writes = re.findall(r"\b\w+\.(create|update|delete|upsert)\s*\(", block)
        if len(writes) >= 2 and "transaction" not in block:
            out.append(Finding("BE-DB-004", "warning", "数据库", "多写操作无事务",
                               path, lineno, "export async function %s（%d 次写操作）" % (name, len(writes)),
                               "同一 handler 内 2 次以上写操作（create/update/delete/upsert）且无事务，一个失败会留脏数据。包 transaction。"))
    return out


# ---------------------------------------------------------------- 运行器

def run(target):
    files = collect_files(target)
    all_text = ""
    ctx = {"target": target, "uses_supabase": False, "has_rls": False}
    texts = {}
    for path in files:
        t = read_text(path)
        texts[path] = t
        all_text += "\n" + t
    ctx["uses_supabase"] = bool(re.search(r"supabase|createClient", all_text, re.I))
    ctx["has_rls"] = bool(re.search(r"\brls\b|ROW LEVEL SECURITY", all_text, re.I))

    findings = []
    for path in files:
        text = texts[path]
        lines = text.split("\n")
        rel = os.path.relpath(path, target)
        for r in RULES:
            if r["id"] in ("BE-SEC-005", "BE-DB-003"):
                continue
            try:
                for f in r["check"](lines, text, path, ctx) or []:
                    f.file = rel
                    findings.append(f)
            except Exception:
                continue
    # .env 走项目级规则（BE-SEC-005 需要读 .gitignore）
    env_path = os.path.join(target, ".env")
    if os.path.isfile(env_path):
        env_text = read_text(env_path)
        for r in RULES:
            if r["id"] == "BE-SEC-005":
                try:
                    for f in r["check"](env_text.split("\n"), env_text, env_path, ctx) or []:
                        f.file = ".env"
                        findings.append(f)
                except Exception:
                    pass
        files.append(env_path)
    # 项目级规则（BE-DB-003）只跑一次
    for r in RULES:
        if r["id"] == "BE-DB-003":
            try:
                for f in r["check"]([], "", target, ctx) or []:
                    findings.append(f)
            except Exception:
                pass
    return files, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-fullstack 确定性后端审计")
    ap.add_argument("--target", default=".", help="扫描目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"], default="blocker")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print("target 不是目录：%s" % args.target, file=sys.stderr)
        return 1

    # .env 已在 run() 内纳入扫描与计数
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
        print("后端审计：扫描 %d 文件，运行 %d 条规则" % (s["files_scanned"], s["rules_run"]))
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
