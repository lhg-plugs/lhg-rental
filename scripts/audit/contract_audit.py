#!/usr/bin/env python3
"""lhg-rental 确定性租赁合同审计：扫描合同文本中的风险信号，零第三方依赖。

扫描目标目录下的 .txt / .md 文件（视作合同文本），输出 JSON 与人类可读报告；
有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 contract_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创（思路受开源合同审查工具启发，未复制任何第三方原文）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-rental/contract-audit"

SCAN_EXTS = {".txt", ".md"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}

MONEY_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*元")

# 押金 / 月租金额抓取（中文合同常用表述）
DEPOSIT_RES = [
    re.compile(r"(?:押金|保证金|履约保证金)\s*[:：为]?\s*(?:人民币)?\s*(\d[\d,]*)\s*元"),
    re.compile(r"交付.*?押金\s*(\d[\d,]*)\s*元"),
]
RENT_RES = [
    re.compile(r"(?:月租金|每月租金|租金为每月|月租)\s*[:：为]?\s*(?:人民币)?\s*(\d[\d,]*)\s*元"),
    re.compile(r"租金\s*(\d[\d,]*)\s*元\s*/\s*月"),
]


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line",
                 "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
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
            if os.path.splitext(f)[1].lower() in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().splitlines()
    except UnicodeDecodeError:
        with open(path, encoding="gbk", errors="ignore") as f:
            return f.read().splitlines()


def num(s):
    return float(s.replace(",", ""))


def first_money(patterns, text):
    for p in patterns:
        m = p.search(text)
        if m:
            try:
                return num(m.group(1))
            except ValueError:
                continue
    return None


class Rule:
    def __init__(self, rule_id, severity, category, title, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.detail = detail
        RULES.append(self)

    def run(self, path, lines, text, ctx):
        raise NotImplementedError


RULES = []


class KeywordRule(Rule):
    """正文出现霸王条款关键词即命中。"""

    def __init__(self, rule_id, severity, category, title, detail, keywords,
                 exclude=None):
        super().__init__(rule_id, severity, category, title, detail)
        self.res = [re.compile(k) for k in keywords]
        self.exclude = [re.compile(e) for e in (exclude or [])]

    def run(self, path, lines, text, ctx):
        for i, ln in enumerate(lines, 1):
            if any(e.search(ln) for e in self.exclude):
                continue  # 否定表述（如"押金不直接抵扣"）不算命中
            for r in self.res:
                if r.search(ln):
                    yield Finding(self.rule_id, self.severity, self.category,
                                  self.title, path, i,
                                  ln.strip()[:120], self.detail)
                    break


class MissingRule(Rule):
    """正文缺少某类关键信息即命中一次。"""

    def __init__(self, rule_id, severity, category, title, detail, present_res):
        super().__init__(rule_id, severity, category, title, detail)
        self.present = [re.compile(p) for p in present_res]

    def run(self, path, lines, text, ctx):
        if not any(r.search(text) for r in self.present):
            yield Finding(self.rule_id, self.severity, self.category,
                          self.title, path, 0,
                          "(全文未检出相关表述)", self.detail)


# ---------------------------------------------------------------- 霸王条款
KeywordRule(
    "RC-T001", "blocker", "霸王条款", "疑似霸王条款：押金无条件不退",
    "合同出现\"押金不退/概不退还\"类表述。押金是担保性质的预付款，"
    "租期届满无违约无欠费时出租方应退还，无条件不退属于加重承租方责任的格式条款，"
    "按《民法典》第 497 条可能被认定无效——但真打官司成本在你，建议签约前删掉或改写。",
    [r"押金.{0,6}(不退|概不退还|不予退还)", r"(不退|概不退还).{0,6}押金",
     r"押金.*转为违约金.*无条件"],
)
KeywordRule(
    "RC-T002", "blocker", "霸王条款", "疑似霸王条款：出租方单方任意涨价",
    "合同允许出租方在租期内\"随时/任意\"调整租金。租金是合同核心对价，"
    "单方调价权等于把定价权完全交给对方，建议改为：租期内租金固定，"
    "续租涨幅写死上限（如不超过 X%），或约定双方协商一致方可调整。",
    [r"任意.{0,4}(涨价|调价|调整租金)", r"随时.{0,4}(涨价|调价|调整租金)",
     r"出租方有权.{0,10}调整租金.{0,10}(无需|不需).{0,6}同意",
     r"租金涨幅不受限制"],
)
KeywordRule(
    "RC-T003", "blocker", "霸王条款", "疑似霸王条款：维修责任全部转嫁承租方",
    "合同把房屋/设施的全部维修责任推给承租方。按《民法典》第 712 条，"
    "出租人有维修租赁物的义务（当事人另有约定的除外），"
    "\"全部由乙方承担\"的写法把自然损耗、结构老化也甩给你，"
    "建议改为：自然损耗与结构性维修由出租方负责，人为损坏由承租方负责。",
    [r"维修.{0,8}全部由.{0,4}(乙方|承租方)", r"所有维修.{0,8}由.{0,4}(乙方|承租方)承担",
     r"(乙方|承租方).{0,8}承担一切维修"],
)
KeywordRule(
    "RC-T004", "blocker", "霸王条款", "疑似霸王条款：押金扣除标准任由出租方解释",
    "合同对押金扣除写了\"出租方有权酌情扣除\"\"解释权归出租方\"类表述，"
    "等于退多少对方说了算。建议改为：列明可扣项清单与扣款标准"
    "（如保洁费 X 元/次、墙面修复按实际发票），并约定退租验收时双方共同确认。",
    [r"押金.{0,10}(酌情|任意|随意).{0,6}扣除", r"解释权归.{0,6}(甲方|出租方)",
     r"扣除标准由.{0,6}(甲方|出租方).{0,6}(决定|说了算)"],
)
KeywordRule(
    "RC-T005", "blocker", "霸王条款", "疑似霸王条款：违约金只约束承租方",
    "合同只写了承租方违约要赔，没写出租方违约（如提前收房、房屋被查封）"
    "要承担什么责任。权利义务不对等，建议补上出租方违约责任"
    "（如双倍返还押金或按剩余租期比例赔偿搬家损失）。",
    [r"(乙方|承租方).{0,10}违约.{0,30}(违约金|赔偿)"],
)
# RC-T005 用关键词+反查实现：命中"承租方违约金"且全文无"出租方违约"时告警
# （在 run 阶段做二次过滤）
_T005 = RULES[-1]


def _t005_filter(findings, text):
    # 全文有"出租方违约要付出代价"的实质条款 → 权利义务对等，RC-T005 剔除
    if re.search(r"(甲方|出租方)(提前.{0,6})?(违约|收回房屋|解除合同)"
                 r".{0,40}(赔偿|双倍|承担.{0,10}责任)", text):
        return [f for f in findings if f.rule_id != "RC-T005"]
    return findings


KeywordRule(
    "RC-T006", "warning", "霸王条款", "风险：押金可直接抵作违约金且无上限",
    "合同允许押金直接抵扣违约金但未设上限，纠纷时对方可能把全部押金"
    "\"一键没收\"。建议：违约金写具体金额或计算方式，押金抵扣后多退少补。",
    [r"押金.{0,10}(抵作|抵扣|冲抵).{0,6}违约金"],
    exclude=[r"不.{0,2}(直接)?(抵作|抵扣|冲抵)", r"不得(抵作|抵扣|冲抵)"],
)
KeywordRule(
    "RC-T007", "warning", "霸王条款", "风险：禁止转租但无例外说明",
    "合同一刀切禁止转租/合租。年轻人合租、短期出差转租是高频场景，"
    "建议改为：经出租方书面同意可转租，或明确允许合租人数上限。",
    [r"不得.{0,6}(转租|分租|合租)", r"禁止.{0,6}(转租|分租|合租)"],
)

# ---------------------------------------------------------------- 关键信息缺失
MissingRule(
    "RC-I001", "blocker", "信息缺失", "缺失：出租人身份信息",
    "全文未检出出租人姓名+身份证号（或公司营业执照号）。签约对象都写不清，"
    "收钱的是谁、告谁都成问题。签约前必须补：个人房东要身份证复印件签字，"
    "二房东/公司要营业执照+原房东的转租授权链。",
    [r"身份证.{0,4}号?\s*[:：]?\s*\d{15,18}", r"营业执照.{0,8}(统一信用代码|\d{15,18})",
     r"出租人.{0,10}姓名"],
)
MissingRule(
    "RC-I002", "blocker", "信息缺失", "缺失：房屋权属证明",
    "全文未检出房产证号/不动产权证/租赁许可证/转租授权。没有权属证明，"
    "你无法确认对方有没有出租权——查封房、抵押房、二房东跑路的重灾区。"
    "签约时要求出示原件并拍照留存，复印件写明\"仅供租房签约使用\"。",
    [r"房产证.{0,6}(号|编号)", r"不动产.{0,6}(权证|登记)", r"房屋所有权证",
     r"转租.{0,6}(授权|同意)书", r"租赁许可证"],
)
MissingRule(
    "RC-I003", "blocker", "信息缺失", "缺失：交房标准/设施交接清单",
    "全文未检出设施交接清单/房屋交割单。没有入住时的家电家具状态记录，"
    "退租时\"这个划痕是你弄的\"百口莫辩。签约当天逐项拍照+视频，"
    "清单双方签字，电子版云端备份。",
    [r"交接清单|设施清单|房屋交割|物品清单|交房标准"],
)
MissingRule(
    "RC-I004", "blocker", "信息缺失", "缺失：租赁期限起止日期",
    "全文未检出租止起止日期。没有明确租期，押金退还、提前解约、续租涨幅"
    "全都无从谈起。必须写死：自 X 年 X 月 X 日至 X 年 X 月 X 日。",
    [r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日.{0,20}(至|到)\s*\d{4}"],
)
MissingRule(
    "RC-I005", "warning", "信息缺失", "缺失：月租金额明确表述",
    "全文未检出明确的月租金金额。口头约定的租金=没约定，涨价纠纷时吃亏。"
    "建议写清：月租金 X 元，支付方式（月付/季付/年付），到账日期。",
    [r"(月租金|每月租金).{0,10}\d[\d,]*\s*元", r"租金.{0,10}\d[\d,]*\s*元\s*/\s*月"],
)
MissingRule(
    "RC-I006", "warning", "信息缺失", "缺失：提前解约/退租条件",
    "全文未检出提前解约、退租通知期的约定。年轻人换工作/换城市高频，"
    "建议约定：提前 30 日书面通知可解约，违约金不超过 1 个月租金；"
    "并写清退租验收流程与押金退还时限。",
    [r"提前.{0,6}(解约|退租|解除)", r"通知期.{0,10}\d+\s*日"],
)
MissingRule(
    "RC-I007", "warning", "信息缺失", "缺失：维修责任划分",
    "全文未检出维修责任划分。家电坏了谁修、费用谁出，"
    "入住前不写清=入住后扯皮。建议：自然损耗出租方修，人为损坏承租方修，"
    "并约定报修响应时限。",
    [r"自然损耗", r"维修.{0,6}(责任.{0,6})?划分",
     r"(?<!不)负责.{0,6}维修", r"人为损坏.{0,10}(乙方|承租方)"],
)
MissingRule(
    "RC-I008", "warning", "信息缺失", "缺失：押金退还时限",
    "全文未检出退租后押金的退还时限。\"尽快退还\"=无限期拖延，"
    "建议写死：验收合格后 X 日内（如 7 日/15 日）原路退还，逾期按日计息。",
    [r"押金.{0,20}(\d+\s*日|日内).{0,10}退还", r"退还押金.{0,20}\d+\s*日",
     r"\d+\s*日内.{0,10}押金.{0,10}退还"],
)


class DepositRatioRule(Rule):
    """押金超过 1 个月租金预警（常见合规上限）。"""

    def __init__(self):
        super().__init__(
            "RC-W001", "warning", "金额异常", "预警：押金超过 1 个月租金",
            "押金金额超过 1 个月租金。多数城市租赁条例/住建提示押金不超过 1 个月"
            "（如北京、上海等地明确倡导），超额部分退还风险高。建议谈到 1 个月以内，"
            "多出的转为预付租金或直接砍掉。",
        )

    def run(self, path, lines, text, ctx):
        dep = first_money(DEPOSIT_RES, text)
        rent = first_money(RENT_RES, text)
        if dep and rent and rent > 0 and dep > rent * 1.0:
            yield Finding(self.rule_id, self.severity, self.category,
                          self.title, path, 0,
                          "押金 %g 元 / 月租 %g 元" % (dep, rent), self.detail)


DepositRatioRule()


class BigDepositRule(Rule):
    """押金绝对值过大（超过 3 个月租金）升级为 blocker。"""

    def __init__(self):
        super().__init__(
            "RC-W002", "blocker", "金额异常", "高危：押金超过 3 个月租金",
            "押金超过 3 个月租金，远超常规水平，常见于\"押 X 付 Y\"套路"
            "或二房东卷款跑路前兆。建议：拒绝签约，或要求押金托管/分期。",
        )

    def run(self, path, lines, text, ctx):
        dep = first_money(DEPOSIT_RES, text)
        rent = first_money(RENT_RES, text)
        if dep and rent and rent > 0 and dep > rent * 3.0:
            yield Finding(self.rule_id, self.severity, self.category,
                          self.title, path, 0,
                          "押金 %g 元 / 月租 %g 元（%.1f 倍）" % (dep, rent, dep / rent),
                          self.detail)


BigDepositRule()


def analyze_file(path):
    lines = read_lines(path)
    text = "\n".join(lines)
    ctx = {}
    findings = []
    for r in RULES:
        findings.extend(r.run(path, lines, text, ctx))
    findings = _t005_filter(findings, text)
    return findings


SEV_ORDER = {"blocker": 0, "warning": 1, "nit": 2}


def main():
    ap = argparse.ArgumentParser(description="lhg-rental 租赁合同确定性审计")
    ap.add_argument("--target", required=True, help="待扫描目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"],
                    default="blocker")
    args = ap.parse_args()

    files = collect_files(args.target)
    findings = []
    for p in files:
        findings.extend(analyze_file(p))
    findings.sort(key=lambda f: (SEV_ORDER[f.severity], f.rule_id))

    summary = {
        "tool": TOOL, "version": VERSION,
        "files_scanned": len(files), "rules_run": len(RULES),
        "blocker": sum(1 for f in findings if f.severity == "blocker"),
        "warning": sum(1 for f in findings if f.severity == "warning"),
        "nit": sum(1 for f in findings if f.severity == "nit"),
    }

    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [f.to_dict() for f in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("lhg-rental 合同审计报告（v%s）" % VERSION)
        print("扫描文件 %d 个，规则 %d 条" % (len(files), len(RULES)))
        print("blocker=%d warning=%d nit=%d"
              % (summary["blocker"], summary["warning"], summary["nit"]))
        print("=" * 60)
        for f in findings:
            loc = f.file if f.line == 0 else "%s:%d" % (f.file, f.line)
            print("[%s][%s] %s" % (f.severity.upper(), f.rule_id, f.title))
            print("  位置: %s" % loc)
            print("  片段: %s" % f.snippet)
            print("  建议: %s" % f.detail)
            print()
        if not findings:
            print("未发现风险信号。注意：脚本只做关键词级扫描，签字前仍建议人工逐条核对。")

    fail_level = SEV_ORDER[args.fail_on]
    bad = any(SEV_ORDER[f.severity] <= fail_level for f in findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
