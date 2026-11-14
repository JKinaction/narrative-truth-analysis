#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语用层（--implicature）测试集。

重点测三件事：
1. 真阳性：确实有话里有话的句子，该检出的有没有检出
2. 真阴性：完全字面表达的句子，不该被过度解读（最重要的误报测试）
3. 边界：空输入、单字、超长、非中文

判定标准不是"检出几项"，而是"有没有把字面表达误判成有话里有话"。
"""

import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "..", "scripts"))
from analyze_narrative import analyze_pragmatic, interpret_pragmatic

# (句子, 期望, 说明)
# 期望: "hit" = 该检出言外动作；"clean" = 字面表达，不该有言外动作
CASES = [
    # ---------- 真阳性：应检出 ----------
    ("这个方案我们内部再讨论一下。", "hit", "典型拖延，无日期无主体"),
    ("说实话，不是我说你，你这个思路还是有点问题。", "hit", "元话语+否定缓冲+预设"),
    ("你为什么还没交？大家都等着呢。", "hit", "预设'你该交'"),
    ("上面要求这么做的，我们也没办法，等通知吧。", "hit", "责任转移+拖延"),
    ("不是嫌贵，是觉得不值。", "hit", "否定式缓冲"),
    ("我个人认为可以再看看，具体看情况吧。", "hit", "元话语+弱化+回避"),
    ("我们会尽快研究，有机会再沟通。", "hit", "弱化评价+承诺缺失"),
    ("这个事得走流程，你等通知。", "hit", "流程挡箭牌"),
    ("按理说这个不符合规定，但这次就算了。", "hit", "元话语（准备破例）"),
    ("我考虑考虑。", "hit", "语用标尺最低档，明确的不打算"),

    # ---------- 真阴性：字面表达，不该误判 ----------
    ("我明天下午三点把报告发到你邮箱。", "clean", "日期+时间+具体动作，承诺完整"),
    ("这个月工资已经到账了，你看一下。", "clean", "纯事实陈述"),
    ("我不同意这个方案，因为成本超预算30%。", "clean", "明确拒绝且给理由，是字面"),
    ("会议改到周四上午十点，地点还是三楼。", "clean", "纯通知"),
    ("我昨天去医院了，所以没回消息。", "clean", "给出原因的解释"),
    ("这份合同的违约金是合同总额的20%。", "clean", "纯条款陈述"),
    ("他今天迟到了半小时，我们等了他很久。", "clean", "事实描述+轻微评价"),
    ("我不太会做这个，你能教我吗？", "clean", "直接求助"),
    ("孩子发烧到39度，我先带他去医院。", "clean", "事实+行动"),
    ("这个月业绩比上个月涨了15%。", "clean", "数据陈述"),

    # ---------- 边界 ----------
    ("", "edge", "空输入"),
    ("好", "edge", "单字"),
    ("嗯。", "edge", "语气词"),
    ("OK", "edge", "纯英文"),
    ("今天天气不错。" * 60, "edge", "超长重复"),
]


def run():
    print("=" * 66)
    print("语用层测试 · analyze_narrative.py --implicature")
    print("=" * 66)

    hit_ok = hit_total = 0
    clean_ok = clean_total = 0
    edge_ok = edge_total = 0
    failures = []

    for text, expect, note in CASES:
        try:
            m = analyze_pragmatic(text)
            f = interpret_pragmatic(m)
        except Exception as e:
            failures.append((text, expect, f"异常: {e}", note))
            continue

        acts = m["inferred_acts"]
        has_act = len(acts) > 0

        if expect == "hit":
            hit_total += 1
            if has_act:
                hit_ok += 1
            else:
                failures.append((text, "hit", "未检出任何言外动作", note))
        elif expect == "clean":
            clean_total += 1
            if not has_act:
                clean_ok += 1
            else:
                failures.append((text, "clean", f"误报: {'/'.join(acts)}", note))
        else:
            edge_total += 1
            edge_ok += 1  # 边界只要求不崩溃

    total_ok = hit_ok + clean_ok + edge_ok
    total = hit_total + clean_total + edge_total
    print(f"\n真阳性   {hit_ok}/{hit_total}  （该检出的）")
    print(f"真阴性   {clean_ok}/{clean_total}  （不该误报的）← 最关键")
    print(f"边界     {edge_ok}/{edge_total}  （不崩溃即可）")
    print(f"\n总计 {total_ok}/{total} = {total_ok/total*100:.0f}%")

    if failures:
        print("\n" + "-" * 66)
        print("未通过:")
        for text, expect, reason, note in failures:
            t = (text[:34] + "…") if len(text) > 34 else text
            print(f"  [{expect}] {t}")
            print(f"        {reason}")
            print(f"        注: {note}")
    else:
        print("\n全部通过")

    return total_ok, total


if __name__ == "__main__":
    ok, total = run()
    sys.exit(0 if ok == total else 1)
