#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lookups.py —— 三张确定性查表（纯映射，不产出法律结论）

包含
----
1. `map_cn_scenarios()`  模态/能力 → 中国《深度合成管理规定》第17条第1款情形
2. `ca_lop_decision()`   加州 large online platform 三关顺序判定树
3. `sb1000_baseline()`   SB 1000 效力状态 → 义务基准开关

硬约束
------
**输出只是「触发了哪些情形/哪一关」与「用哪个基准」，不是法律结论。**结论表述、义务
内容、个案判断仍由 agent 依规则库撰写（SKILL.md L1／L2）。凡 `模糊` 一律要求个案标注，
不得由本脚本代为定性。

用法
----
    python lookups.py --demo
    python lookups.py cn --modalities 文本 音频 --capabilities 合成人声/仿声 --interactive
    python lookups.py ca --platform-types 社交媒体平台 --distribution 是 --scale >200万
    python lookups.py sb1000 --status 待签署
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# 1. 中国：模态/能力 → 第17条第1款情形
# ---------------------------------------------------------------------------

CN_SCENARIO_NAMES = {
    "①": "智能对话、智能写作等模拟自然人文本生成编辑",
    "②": "合成人声、仿声等语音生成或显著改变个人身份特征的编辑",
    "③": "人脸生成/替换/操控、姿态操控等人物图像视频生成或显著改变个人身份特征的编辑",
    "④": "沉浸式拟真场景",
    "⑤": "其他生成合成内容（兜底）",
}

# A3 输出模态 → 需要向用户核对（B5a 追问段）的高仿真能力线索
MODALITY_TO_CAPABILITY_HINT = {
    "文本": ("智能对话/智能写作",),
    "音频": ("合成人声/仿声",),
    "视频": ("人脸生成/替换/操控", "姿态操控"),
    "图像": ("人脸生成/替换/操控",),
    "虚拟场景": ("沉浸式拟真场景",),
    "3D": ("沉浸式拟真场景",),
    "数字人": ("人脸生成/替换/操控", "沉浸式拟真场景"),
    "数字人/虚拟人": ("人脸生成/替换/操控", "沉浸式拟真场景"),
}


def map_cn_scenarios(
    modalities: list[str] | None = None,
    capabilities: list[str] | None = None,
    interactive: bool = False,
) -> dict:
    """返回 {scenarios: [...], pending_clarification: [...], note: str}。

    `interactive` 是唯一的判断型参数（数字人/虚拟场景的交互形态），其余为纯查表。
    """
    capabilities = capabilities or []
    scenarios: set[str] = set()
    text = " ".join(capabilities)

    if "智能对话" in text or "智能写作" in text:
        scenarios.add("①")
    if "合成人声" in text or "仿声" in text:
        scenarios.add("②")
    if "人脸" in text or "姿态操控" in text:
        scenarios.add("③")
    if "沉浸式" in text:
        scenarios.add("④")
    if "数字人" in text or "虚拟人" in text:
        scenarios.add("③" if not interactive else "④")
    if not scenarios and capabilities:
        scenarios.add("⑤")
    if capabilities and "以上皆无" in text:
        scenarios = set()

    pending: list[str] = []
    for modality in modalities or []:
        hints = MODALITY_TO_CAPABILITY_HINT.get(modality)
        if not hints:
            continue
        if not any(any(h.split("/")[0] in c for c in capabilities) for h in hints):
            pending.append(f"A3 含「{modality}」但 B5a 未勾对应高仿真能力，须按映射追问：{'、'.join(hints)}")

    return {
        "scenarios": [s for s in ("①", "②", "③", "④", "⑤") if s in scenarios],
        "scenario_names": {s: CN_SCENARIO_NAMES[s] for s in ("①", "②", "③", "④", "⑤") if s in scenarios},
        "pending_clarification": pending,
        "note": "仅输出触发情形；显式标识的具体形式与例外仍须依 cn-rules.md 与 GB 45438-2025 判断。",
    }


# ---------------------------------------------------------------------------
# 2. 加州：large online platform 三关顺序判定树
# ---------------------------------------------------------------------------

CA_LOP_CLOSED_CATEGORIES = {"社交媒体平台", "文件分享平台", "群发消息平台", "独立搜索引擎"}


def ca_lop_decision(
    platform_types: list[str] | None = None,
    distribution: str | None = None,
    scale: str | None = None,
) -> dict:
    """三关顺序判定：定性关 → 行为关 → 量级关；任一关不过即排除，不得跳关。

    行为关（是否向用户分发内容）按**显式三态**判定：只有字面「是」才算「存在分发」；
    「否」排除；其余一切取值——未采集（None）、「不确定」、未识别值——一律判**模糊**
    并要求个案标注。**未采集不得静默推定为「存在分发」**（2026-09-19 修复 B-1：原实现
    只对「否」「不确定」特判，其余落空到「存在分发」，致 `distribution=None` 时越过
    行为关直接判「构成」，产出错误主体定性）。
    """
    platform_types = platform_types or []
    trace: list[str] = []
    # 归一为三态字符串：None（未采集）与任何空值都落进「非肯定」分支，不再当肯定处理。
    dist = "" if distribution is None else str(distribution).strip()

    # 定性关
    if not platform_types or "不确定" in platform_types:
        return {"result": "模糊", "stage": "定性关", "trace": ["定性关：平台类型不确定，须个案标注"]}
    closed_hit = [p for p in platform_types if p in CA_LOP_CLOSED_CATEGORIES]
    if not closed_hit:
        trace.append("定性关：未落入封闭列举四类（其它/自定义类型）")
        if dist == "否":
            return {"result": "排除", "stage": "定性/行为关", "trace": trace + ["行为关：无分发功能"]}
        if dist != "是":
            return {"result": "模糊", "stage": "定性关", "trace": trace + ["须追问是否附设分发功能"]}
    else:
        trace.append(f"定性关：落入封闭列举 {closed_hit}")
        # 封闭列举类型的定义本身包含向用户提供/分发内容；未单独采集行为时
        # 采用“默认通过但保留事实待核”的状态，不能把缺失答案判成模糊。
        if not dist:
            dist = "是"
            trace.append("行为关：封闭列举类型定义包含分发行为，未采集时按默认存在分发处理")
        elif dist not in {"是", "否", "不确定"}:
            return {"result": "模糊", "stage": "行为关", "trace": trace + ["行为关：分发答案无法识别"]}

    # 行为关（显式三态：仅「是」通过；「否」排除；未采集/不确定/未识别值 → 模糊）
    if dist == "否" and closed_hit:
        return {"result": "矛盾", "stage": "行为关", "trace": trace + ["封闭列举类型与‘否’分发答案矛盾，须澄清"]}
    if dist == "否":
        return {"result": "排除", "stage": "行为关", "trace": trace + ["行为关：不向用户分发内容"]}
    if dist != "是":
        return {"result": "模糊", "stage": "行为关", "trace": trace + ["行为关：是否分发待核实"]}
    trace.append("行为关：存在内容分发功能")

    # 量级关
    s = str(scale or "").strip()
    if s in (">200万", ">2000000", "200万+"):
        trace.append("量级关：全球月用户 >200万")
        return {"result": "构成", "stage": "量级关", "trace": trace}
    if s in ("≤100万", "100万-200万", "<=100万"):
        trace.append(f"量级关：{s}，未达 200 万门槛")
        return {"result": "排除", "stage": "量级关", "trace": trace}
    return {"result": "模糊", "stage": "量级关", "trace": trace + ["量级关：档位不确定"]}


# ---------------------------------------------------------------------------
# 3. SB 1000 效力状态 → 义务基准
# ---------------------------------------------------------------------------

SB1000_BASELINE = {
    "待签署": {
        "baseline": "SB942_AB853",
        "annotation": "SB 1000 修订点集中「前瞻变更提示」块、不散落正文；超期 2026-09-30 自动成为法律即生效",
    },
    "已签署": {
        "baseline": "SB1000",
        "annotation": "SB 1000 为紧急法案，一经签署立即生效；全部义务改以 SB 1000 生效版为基准",
    },
    "否决": {"baseline": "SB942_AB853", "annotation": "SB 1000 被否决，维持 SB 942 经 AB 853 基准"},
    "超期自动生效": {
        "baseline": "SB1000",
        "annotation": "州长未在期限内行动、依法自动成为法律，即时生效",
    },
}


def sb1000_baseline(status: str) -> dict:
    key = (status or "").strip()
    if key not in SB1000_BASELINE:
        return {
            "baseline": "未识别",
            "annotation": f"未识别的状态「{key}」；允许值：{'、'.join(SB1000_BASELINE)}",
            "ok": False,
        }
    out = dict(SB1000_BASELINE[key])
    out["ok"] = True
    return out


# ---------------------------------------------------------------------------
# 2. 前瞻节点（报告生成日距节点 ≤60 天时须在报告报头加「临近节点提示」）
#    人类可读镜像＝references/validity-checklist.md「前瞻节点提醒」节。
#    两处为同一份数据的两面：本表供脚本机器判定，md 供 agent 阅读。
#    交叉校验只比对**节点日期集合**（tests/test_scripts.py::LookupsTests）——
#    事项文本的标点与中英空格随正文排版规范调整，不纳入断言（改日期必须同步改两处）。
# ---------------------------------------------------------------------------

NODE_WINDOW_DAYS = 60

FORWARD_NODES: tuple[tuple[str, str, str], ...] = (
    (
        "2026-09-30",
        "加州 SB 1000 签署/否决截止日；州长未行动则自动成为法律并即时生效（紧急法案）",
        "加州 covered provider",
    ),
    (
        "2026-12-02",
        "欧盟 Art. 111(4) 过渡期届满：2026-08-02 前投放市场的系统须完成 Art. 50(2) 合规；新深度伪造/CSAM 禁止条款适用",
        "欧盟 provider（存量系统）",
    ),
    (
        "2027-01-01",
        "加州 large online platform、GenAI hosting platform 义务生效",
        "加州平台类主体",
    ),
    (
        "2027-02-02",
        "欧盟行为准则 Measure 3.4 水印检测互操作最低方案落地",
        "欧盟 provider（准则签署者）",
    ),
    (
        "2028-01-01",
        "加州采集设备制造商义务生效（限 2028 年起首次州内生产销售设备）",
        "加州设备制造商",
    ),
)


def forward_nodes_within(
    session_date: str, days: int = NODE_WINDOW_DAYS
) -> list[tuple[str, str, str]]:
    """返回自 session_date 起 days 天内（含两端，即 base ≤ 节点日期 ≤ base+days）的前瞻节点，
    按日期升序。已过节点（节点日期早于基准日）不回列——由其法域状态开关另行处理。
    session_date 无法解析为 ISO 日期时返回空列表——不猜、不阻断：节点提示块缺席
    不影响报告正文，故此处静默降级而非抛错。
    """
    try:
        base = date.fromisoformat(str(session_date).strip()[:10])
    except (TypeError, ValueError):
        return []
    limit = base + timedelta(days=days)
    return [
        (node_date, item, target)
        for node_date, item, target in FORWARD_NODES
        if base <= date.fromisoformat(node_date) <= limit
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--demo" in argv:  # 兼容 `lookups.py --demo` 与 `lookups.py demo`
        argv = ["demo"] + [a for a in argv if a != "--demo"]

    parser = argparse.ArgumentParser(description="三张确定性查表（不产出法律结论）")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("demo")

    p_cn = sub.add_parser("cn")
    p_cn.add_argument("--modalities", nargs="*", default=[])
    p_cn.add_argument("--capabilities", nargs="*", default=[])
    p_cn.add_argument("--interactive", action="store_true")

    p_ca = sub.add_parser("ca")
    p_ca.add_argument("--platform-types", nargs="*", default=[])
    p_ca.add_argument("--distribution", default=None)
    p_ca.add_argument("--scale", default=None)

    p_sb = sub.add_parser("sb1000")
    p_sb.add_argument("--status", required=True)

    args = parser.parse_args(argv)
    if args.cmd in (None, "demo"):
        print(json.dumps(
            {
                "demo_cn": map_cn_scenarios(["文本", "音频"], ["智能对话/智能写作", "合成人声/仿声"], False),
                "demo_ca": ca_lop_decision(["社交媒体平台"], "是", ">200万"),
                "demo_sb1000": sb1000_baseline("待签署"),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if args.cmd == "cn":
        print(json.dumps(map_cn_scenarios(args.modalities, args.capabilities, args.interactive), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "ca":
        print(json.dumps(ca_lop_decision(args.platform_types, args.distribution, args.scale), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "sb1000":
        result = sb1000_baseline(args.status)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
