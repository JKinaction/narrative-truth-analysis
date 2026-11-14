#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
叙事语言信号量化分析器。

把"读语言细节"从直觉变成可复核的数字。
仅输出信号，不下结论 —— 结论需要结合 references/signal-catalog.md 人工研判。

用法:
    python3 analyze_narrative.py <文本文件>
    python3 analyze_narrative.py <文本文件> --json
    cat 文本 | python3 analyze_narrative.py -
"""

import argparse
import json
import re
import statistics
import sys

# ---------------------------------------------------------------- 词表

# 模糊限定词：确定性缺失
HEDGE = [
    "可能", "大概", "也许", "好像", "似乎", "差不多", "基本上", "应该是", "应该是吧",
    "记不太清", "记不清", "不太确定", "不确定", "好像吧", "大概吧", "反正", "反正就是",
    "之类的", "什么的", "有一说一", "我觉得吧", "印象中", "依稀", "仿佛", "似乎有点",
    "多少", "有点", "稍微", "有点像是", "不排除", "据说", "听说", "据说", "好像在",
]
# 强断言：确定性过强
ASSERTIVE = [
    "一定", "绝对", "肯定", "必然", "毫无疑问", "百分之百", "从来", "每次", "所有人",
    "根本", "压根", "就是", "完全", "明确", "铁证", "确凿", "板上钉钉",
]
# 情绪/评价词
EMOTION = [
    "愤怒", "生气", "气死", "恼火", "失望", "心寒", "寒心", "委屈", "难受", "崩溃",
    "绝望", "痛心", "恐惧", "害怕", "焦虑", "失望透顶", "太过分", "过分", "荒谬",
    "可笑", "无耻", "恶劣", "恶心", "糟糕", "倒霉", "受不了", "忍不了", "感动",
    "欣慰", "感谢", "开心", "高兴", "满意", "踏实", "安心", "莫名其妙",
]
# 抽象名词：代替具体动作，常用于免责
# 注意："问题""情况""方面"单用过于常见（"这个问题""情况很复杂"），
# 会把普通叙述也判成免责型。此处只取有明确免责语义的组合。
ABSTRACT_NOUN = [
    "沟通不畅", "沟通成本", "对接", "机制", "流程上", "流程问题", "统筹", "协调",
    "客观原因", "客观因素", "实际情况", "实际情况", "大方向", "整体方向",
    "上面", "上层", "大环境", "形势", "系统性的", "生态", "节奏", "协作",
    "处理", "安排", "部署", "推进", "落地", "资源", "大环境",
]
# 责任稀释结构
PASSIVE_MARK = [
    "被", "遭到", "受到", "得以", "加以", "予以", "进行", "实施", "遭到", "遭遇",
    "引发", "导致", "被推", "被安排", "被要求", "被通知", "被叫去", "被拉",
]
# 无主语归因：把结果推给抽象方
DIFFUSE_AGENT = [
    "上面", "公司", "团队", "部门", "领导", "组织", "对方", "那边", "上面的人",
    "公司方面", "业务线", "大环境", "形势", "制度", "流程上", "客观", "现实",
]
# 感官碎片：真实回忆的信号
# 注意：只用不易误匹配的组合词。单字（如"听""干""白""红""冷""热"）会命中
# "听话""干嘛""明白""热闹"等常用语，造成感官密度虚高。
SENSORY = [
    "闻起来", "闻见", "闻到", "尝到", "摸到", "触到", "碰到",
    "听见", "听到", "看到", "看见", "瞥见", "瞄到",
    "味道", "气味", "声响", "声音很", "噪音", "空调", "暖气",
    "灯光", "阳光", "影子", "脚印", "颜色", "灰色", "发黄", "褪色",
    "冰凉", "滚烫", "烫手", "发麻", "起泡", "湿的", "干的", "黏手", "褶皱",
    "外套", "袖子", "袖口", "衣角", "领子", "鞋带", "皮鞋",
    "桌角", "杯子", "椅子", "烟味", "窗帘", "空调声", "风扇",
]
# 自我指涉的失误/难堪动作：真实信号
SELF_IMPERFECT = [
    "我错了", "我承认", "是我的问题", "我搞砸", "我没做到", "我犹豫", "我怂了",
    "我也没", "我说错", "我搞错", "我后来才", "我拖了", "我漏了", "我当时懵",
]
# 时间锚点
TIME_ANCHOR = [
    "当天", "那天", "当天晚上", "第二天", "昨天", "前天", "上周", "上个月", "今年",
    "三点", "四点", "五点", "六点", "七点", "八点", "九点", "十点", "十一点",
    "十二点", "一点", "两点", "凌晨", "早上", "中午", "下午", "傍晚", "晚上",
    "礼拜", "周一", "周二", "周三", "周四", "周五", "周六", "周日", "周末",
    "季度", "月", "号", "日", "点", "半", "月初", "月底", "年初", "年底",
]
# 结尾升华
MORALIZING = [
    "总之", "所以说", "归根结底", "说到底", "总结一下", "后来我才明白", "这件事让我",
    "这就是", "所以我选择了", "我学会了", "成长了", "值得反思", "教训",
]
# 模糊数量
VAGUE_NUM = [
    "三五个", "几个", "一些", "一点", "好多", "很多", "不少", "个别", "某些",
    "三三两两", "零零散散", "一大帮", "很多人", "不少人",
]
# 精确数字模式
PRECISE_NUM = re.compile(r"\d+")

# ---------------------------------------------------------------- 分析


# ---------------------------------------------------------------- 短文本模式

# 直播连麦、访谈、聊天记录这类"口述原始陈述"通常只有一两句，
# 上面基于密度的指标全部失效（分母太小）。短文本改用另一套判据：
# 这些指标不依赖文本长度，靠结构特征而非统计量。

# 第三方指称（把当事人替换成他人）
THIRD_PARTY = ["我有一个朋友", "我有个朋友", "我有一个表哥", "我有个表哥",
                "我有一个亲戚", "我有个亲戚", "我有一个同事", "我有个同事",
                "我有一个朋友", "我朋友", "我表哥", "我亲戚", "我同事", "我室友",
                "我一个朋友", "我一个表哥", "我一个亲戚", "我有个朋友",
                "听我朋友说", "我听说"]
# 自身不利披露
SELF_EXPOSE = ["我打", "我先打", "我错了", "我不该", "我承认", "我确实",
                "我也打了", "我动了手", "我喝了", "我赌了"]
# 对方先行（把责任前置）
BLAME_SHIFT = ["她先", "他先", "是她先", "是他先", "她之前也", "他之前也",
                "她先打", "他先打", "她先动手", "我为了她", "我为了他",
                "为了她", "为了他", "她骂我", "他骂我"]
# 逐句陈述标记（口语节奏）
DISCOURSE = ["然后", "就", "但是", "所以", "因为", "而且", "我说", "我跟他说"]
# 财产/债务/利益词（利益导向的诉求）
PROPERTY = ["彩礼", "房子", "房产", "房贷", "贷款", "欠条", "债务", "钱", "遗产",
            "继承", "分", "转", "账户", "存款", "股权", "婚前", "婚后", "补偿",
            "折价", "定金", "借条", "银行", "转账", "流水", "工资", "财产", "钱"]
# 权益型诉求词：指向"我受了损害"而非"我要分到钱"
EMOTION_CLAIM = ["孩子", "抚养", "家暴", "出轨", "伤害", "净身出户", "委屈",
                  "保护", "陪伴", "老人", "生病", "可怜", "不容易", "抚养费",
                  "探视", "虐待", "殴打", "未尽", "责任", "义务", "赡养", "孝顺",
                  "抚养费", "断绝", "关系", "伤心", "寒心", "没人管"]
# "两头占"模式：想取得权利但不愿承担对应义务
FREE_RIDER = ["不想承担", "不想还", "不想接手", "不用还", "不承担", "不想管",
              "只想在这住", "不用过户", "不想办手续", "不想负责", "甩给我"]
# 信息不对称词：不知道对方有什么资产 —— 与"利益型"并列的第三种诉求
INFO_GAP = ["不知道", "不清楚", "不了解", "完全不知道", "查不到", "没法查",
            "查一下", "调查令", "怎么查", "有多少钱", "多少财产", "不清楚老公"]
# 防御性/预防性表述：指向"防止对方占我便宜"或"防止我吃亏"
DEFENSIVE = ["预防", "防他", "防他", "保护", "保住", "别让他", "不让他", "怎么防",
              "怕他", "提防", "别被他", "不让对方", "避免被他", "防止他", "被占",
              "吃亏", "防止", "避免"]
# 攻击性/算计性表述：指向"我要占对方便宜"或"设计对方"
CALCULATING = ["图谋", "骗", "算计", "钻空子", "套", "白拿", "白嫖", "要回来",
                "退彩礼", "坑", "套路", "设计", "空手套", "占便宜", "分我一半",
                "让女方还", "帮我还", "让她还"]

# ---------------------------------------------------------------- 语用层（话里有话）
# 对应 references/implicature-playbook.md
# 这一组不判断"他在想什么"，只标注"这句话在做什么动作"。

# 元话语标记：为后面的话铺路，本身不承载信息
METADISCOURSE = ["说实话", "说句实话", "讲真", "讲道理", "不是我说你", "我就直说了",
                 "直说吧", "按理说", "我个人认为", "先说好", "先说清楚", "丑话说在前",
                 "有句话不知当讲", "不是我要说", "照我说", "说白了", "坦白说",
                 "不瞒你说", "老实说"]
# 否定式缓冲："不是A，而是B" —— A 是顾虑，B 是真意
NEG_BUFFER = ["不是嫌", "不是不", "不是针对", "不是我说", "不是不想", "不是不愿意",
              "不是钱的问题", "不是因为钱", "不是因为", "倒不是", "并不是说",
              "不是说", "不在于", "重点不在", "关键不在"]
# 弱化评价：用弱词就是在说弱评价
HEDGED_EVAL = ["还不错", "挺好的", "挺好", "有点意思", "很有想法", "很有特色",
               "再研究", "研究一下", "考虑考虑", "再说吧", "看情况", "看吧",
               "有机会", "回头再说", "以后再说", "走流程", "按流程", "再说",
               "尽量", "争取", "努力", "应该可以", "差不多", "大概没问题",
               "值得考虑", "可以理解", "有难度", "不太好说", "有点复杂"]
# 预设触发词：一句话夹带的、未经证明的前提
PRESUPPOSITION = ["为什么还没", "怎么还没", "为什么没", "为什么不能", "还是",
                  "又", "连他", "连你", "居然", "竟然", "既然", "你不是",
                  "你没", "你从来", "你一直", "早就", "早就说", "当初"]
# 回避/拖延标记：不给日期、不给主体、不给下一步
AVOIDANCE = ["这个再说", "回头聊", "到时候", "到时候看", "具体情况", "具体看",
             "再说吧", "再说", "看情况", "有条件", "在推进", "在走", "流程中",
             "还在研究", "再研究", "研究研究", "研究一下", "需要讨论", "内部讨论",
             "内部再讨论", "再讨论", "再议", "讨论一下", "上面", "领导",
             "公司决定", "集体决策", "不是我能定", "不是我定", "不好说",
             "等通知", "没办法", "也没办法"]
# 人称滑动：责任摊薄的痕迹
AGENT_SHIFT = ["我们", "大家", "有人", "上面", "公司", "领导", "团队", "部门",
               "组织", "有关方面", "相关方"]


def analyze_pragmatic(text):
    """语用层分析：拆'话里有话'。

    只标注言语行为与语言形式，不推断动机。
    """
    s = text.strip()
    n_chars = max(len(s), 1)

    meta = [w for w in METADISCOURSE if w in s]
    negbuf = [w for w in NEG_BUFFER if w in s]
    hedged = [w for w in HEDGED_EVAL if w in s]
    presupp = [w for w in PRESUPPOSITION if w in s]
    avoid = [w for w in AVOIDANCE if w in s]
    shift = [w for w in AGENT_SHIFT if w in s]

    # 言外动作推断（基于形式组合，非动机判断）
    acts = []
    if avoid:
        acts.append("回避/拖延")
    if hedged:
        acts.append("降温/保留")
    if negbuf:
        acts.append("否定式缓冲")
    if shift and not any(p in s for p in ["我决定", "我负责", "我来"]):
        acts.append("责任转移")
    if presupp:
        acts.append("预设植入")

    # 是否有具体承诺要素：日期、人名、数字
    has_date = bool(re.search(r"\d+[月日号]|下周|明天|后天|本周|这周|月底|季度|周[一二三四五六日]", s))
    # 人名检测：要求「姓氏+称谓」或「某某」，避免"方案""对方""方面"等词误命中
    _surname = "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤"
    has_owner = bool(re.search(f"[{_surname}](总|经理|老师|主任|律师|总监|主管|工|先生|女士|哥|姐|某某|某)", s)) or bool(re.search(r"某某|哪位|谁负责|谁定", s))
    has_number = bool(re.search(r"\d+", s))

    m = {
        "_raw": s,
        "chars": len(s),
        "metadiscourse": meta,
        "neg_buffer": negbuf,
        "hedged_eval": hedged,
        "presupposition": presupp,
        "avoidance": avoid,
        "agent_shift": shift,
        "inferred_acts": acts,
        "has_date": has_date,
        "has_owner": has_owner,
        "has_number": has_number,
        "commitment_score": int(has_date) + int(has_owner) + int(has_number),
    }
    return m


def interpret_pragmatic(m):
    """把语用信号转成可读的观察。只用'看起来''可能'，不下断言。"""
    out = []

    def add(dim, signal, reading):
        out.append({"dim": dim, "signal": signal, "reading": reading})

    if m["metadiscourse"]:
        add("元话语", "出现 " + "、".join(m["metadiscourse"]),
            "这类词是为后面的话铺路 —— 往后一到两句通常才是真正想说的内容")

    if m["neg_buffer"]:
        add("缓冲", "出现 " + "、".join(m["neg_buffer"]),
            "否定式缓冲：被否掉的那半句往往是对方的顾虑，后半句才是真实障碍")

    if m["hedged_eval"]:
        add("强度", "出现弱化词 " + "、".join(m["hedged_eval"]),
            "语用标尺上的弱词 —— 弱词通常对应弱评价，不宜按字面理解")

    if m["presupposition"]:
        add("预设", "出现预设触发 " + "、".join(m["presupposition"]),
            "这句话默认了某个没被证明的前提，摊开它再判断整句话是否成立")

    if m["avoidance"]:
        add("回避", "出现 " + "、".join(m["avoidance"]),
            "没有具体日期、主体或下一步 —— 这是拖延/回避的典型形态")

    if m["agent_shift"]:
        add("主体", "出现 " + "、".join(m["agent_shift"]),
            "责任被摊到集体或在场外的主体上，追责时通常无人认领")

    # 仅当句子确实在做表态/承诺时，才提示承诺要素缺失
    _commit_verbs = ["会", "将", "尽量", "争取", "努力", "研究", "推进", "安排",
                     "处理", "解决", "考虑", "商量", "讨论", "协调", "落实", "跟进"]
    if (m["commitment_score"] == 0 and m["chars"] >= 10
            and any(v in m["_raw"] for v in _commit_verbs)):
        add("承诺", "全句无日期、无人名、无数字",
            "承诺三要素为零 —— 这类表态通常不产生任何可执行义务")

    return out


def analyze_short(text):
    """短文本（口述/连麦/聊天）专用分析。"""
    s = text.strip()
    n_chars = max(len(s), 1)

    third = sum(s.count(w) for w in THIRD_PARTY)
    self_exp = sum(s.count(w) for w in SELF_EXPOSE)
    blame = sum(s.count(w) for w in BLAME_SHIFT)
    discourse = sum(s.count(w) for w in DISCOURSE)
    prop = sum(s.count(w) for w in PROPERTY)
    emo_claim = sum(s.count(w) for w in EMOTION_CLAIM)
    info_gap = sum(s.count(w) for w in INFO_GAP)
    defensive = sum(s.count(w) for w in DEFENSIVE)
    calculating = sum(s.count(w) for w in CALCULATING)
    free_rider = sum(s.count(w) for w in FREE_RIDER)

    # 疑问句密度：连麦咨询几乎全是问句
    q_marks = s.count("？") + s.count("?")
    q_density = q_marks * 1000 / n_chars

    # 人称密度
    first = sum(s.count(w) for w in ["我", "我的", "我们"])
    second = sum(s.count(w) for w in ["她", "他", "老婆", "老公", "女朋友", "男朋友"])
    third_person = sum(s.count(w) for w in ["他们", "她们", "对方"])

    # 时间顺序标记：是否在讲"已经发生的事"还是"计划"
    past = sum(s.count(w) for w in ["了", "过", "当时", "之前", "去年", "前年",
                                    "最近", "当年", "一直"])
    future = sum(s.count(w) for w in ["能不能", "可不可以", "要不要", "怎么办",
                                      "怎么会", "有没有可能", "可不可行", "如何",
                                      "怎么", "吗"])

    m = {
        "chars": len(s),
        "third_party_count": third,
        "self_expose_count": self_exp,
        "blame_shift_count": blame,
        "discourse_marker_count": discourse,
        "property_count": prop,
        "emotion_claim_count": emo_claim,
        "info_gap_count": info_gap,
        "defensive_count": defensive,
        "calculating_count": calculating,
        "free_rider_count": free_rider,
        "question_density": round(q_density, 2),
        "first_person": first,
        "second_person": second,
        "third_person": third_person,
        "past_marker_count": past,
        "future_marker_count": future,
    }
    return m


def interpret_short(m):
    out = []

    def add(dim, signal, reading):
        out.append({"dim": dim, "signal": signal, "reading": reading})

    if m["third_person"] >= 0 and m["third_party_count"] > 0:
        add("身份", f"出现第三方指称 {m['third_party_count']} 次",
            "把自己替换成他人叙述 —— 直播连麦的高频模式，指向不愿承担陈述主体身份")

    if m["blame_shift_count"] > 0:
        add("归因", f"责任前置标记 {m['blame_shift_count']} 处"
            f"（'她先''之前也''我为了她'）",
            "把因果起点前移到对方 —— 常见于为自身行为寻找减责叙事")

    if m["self_expose_count"] > 0:
        add("可信度", f"自身不利披露 {m['self_expose_count']} 处",
            "主动说出对自己不利的事实，是可信度信号")

    if m["property_count"] >= 2 and m["emotion_claim_count"] == 0 and m["info_gap_count"] == 0:
        if m["calculating_count"] > m["defensive_count"]:
            add("目的", f"财产/债务词 {m['property_count']} 处、权益型诉求 0 处、"
                f"算计性表述 {m['calculating_count']} 处 > 防御性 {m['defensive_count']} 处",
                "诉求完全落在利益分配上，且方向是'占对方便宜' —— 算计型")
        elif m["defensive_count"] > 0:
            add("目的", f"财产/债务词 {m['property_count']} 处、防御性表述 {m['defensive_count']} 处",
                "诉求落在利益分配上，但方向是'防止对方占我便宜' —— 防御型，非算计")
        else:
            add("目的", f"财产/债务词 {m['property_count']} 处、权益型诉求 0 处",
                "利益导向，但未检出方向词 —— 需人工判断是防御还是算计")

    if m["property_count"] >= 2 and m["emotion_claim_count"] >= 2:
        add("目的", f"财产词 {m['property_count']} 处、权益型诉求 {m['emotion_claim_count']} 处",
            "利益与伤害并存 —— 维权型或混合型诉求")

    if m["property_count"] == 0 and m["emotion_claim_count"] >= 2:
        add("目的", f"权益型诉求 {m['emotion_claim_count']} 处、财产词 0 处",
            "纯权益型诉求：诉求是关系、抚养、赡养或责任，不是钱 —— 与利益型截然不同")

    if m["free_rider_count"] >= 1:
        add("目的", f"'两头占'标记 {m['free_rider_count']} 处"
            f"（要权利但明示不愿承担对应义务）",
            "诉求结构本身自相矛盾 —— 对方无权时通常直接驳回，这是最省时的识别点")

    if m["info_gap_count"] >= 1:
        add("目的", f"信息不对称标记 {m['info_gap_count']} 处",
            "核心诉求是'我不知道对方有什么' —— 信息获取型，通常伴随真实困境")

    if m["future_marker_count"] >= 2 and m["past_marker_count"] <= 1:
        add("时态", "几乎全是将来/可能句式，无已发生事实",
            "陈述重心在计划与设想，而非已经发生的事 —— 属方案咨询而非事实咨询")

    if m["past_marker_count"] >= 3:
        add("时态", f"已发生事实标记 {m['past_marker_count']} 处",
            "以既成事实为主 —— 属事实咨询，核实有抓手")

    if m["question_density"] >= 20:
        add("结构", f"疑问密度 {m['question_density']}/千字",
            "以提问组织陈述：当事人要的是答案，不是叙事")

    if m["first_person"] >= 3 and m["second_person"] >= 2:
        add("结构", "第一人称与第二人称都高",
            "同时讲'我'和'对方' —— 双线陈述，注意两条线的详细度是否对称")

    if m["second_person"] >= 2 and m["first_person"] <= 1:
        add("结构", "几乎只讲对方，很少讲自己",
            "自我叙述被压缩 —— 与'第三方指称'同源，指向对自身动机的回避")

    return out


# ---------------------------------------------------------------- 分析


def split_sentences(text):
    """按中文/英文句读切分，保留标点。"""
    raw = re.split(r"(?<=[。！？!?；;…])|\n+", text)
    return [s.strip() for s in raw if s and s.strip()]


def count_hits(sentence, table):
    n = 0
    for w in table:
        if w and w in sentence:
            n += sentence.count(w)
    return n


def analyze(text):
    sentences = split_sentences(text)
    n = max(len(sentences), 1)

    per_sentence = []
    for i, s in enumerate(sentences):
        pos = len(s)
        hedge = count_hits(s, HEDGE)
        assertive = count_hits(s, ASSERTIVE)
        emotion = count_hits(s, EMOTION)
        abstract = count_hits(s, ABSTRACT_NOUN)
        passive = count_hits(s, PASSIVE_MARK)
        diffuse = count_hits(s, DIFFUSE_AGENT)
        sensory = count_hits(s, SENSORY)
        self_bad = count_hits(s, SELF_IMPERFECT)
        time_a = count_hits(s, TIME_ANCHOR)
        moral = count_hits(s, MORALIZING)
        vague_num = count_hits(s, VAGUE_NUM)
        precise_num = len(PRECISE_NUM.findall(s))
        quotes = len(re.findall(r"[\"“”「」『』]", s))

        per_sentence.append({
            "idx": i,
            "len": pos,
            "hedge": hedge,
            "assertive": assertive,
            "emotion": emotion,
            "abstract_noun": abstract,
            "passive": passive,
            "diffuse_agent": diffuse,
            "sensory": sensory,
            "self_imperfect": self_bad,
            "time_anchor": time_a,
            "moralizing": moral,
            "vague_num": vague_num,
            "precise_num": precise_num,
            "quotes": quotes,
            "text": s,
        })

    total = lambda k: sum(x[k] for x in per_sentence)
    char_total = max(total("len"), 1)

    # 句长方差
    lens = [x["len"] for x in per_sentence]
    len_mean = statistics.mean(lens)
    len_stdev = statistics.pstdev(lens) if len(lens) > 1 else 0.0

    # 情绪词位置：越靠后/越集中在结尾，越可能是"总结性情绪标注"
    emotion_positions = [x["idx"] for x in per_sentence if x["emotion"] > 0]
    emotion_center = (sum(emotion_positions) / len(emotion_positions) / max(n - 1, 1)) if emotion_positions else None

    # 细节碎屑密度：感官词 + 自我失误，按千字
    debris = total("sensory") + total("self_imperfect")
    debris_density = debris / char_total * 1000

    # 主张-支撑配比：强断言 / 感官+时间锚点
    claims = total("assertive")
    support = total("sensory") + total("time_anchor") + total("self_imperfect")

    # 归因集中度：责任稀释标记占比
    dilution = total("passive") + total("diffuse_agent")

    # 被动句比例（近似：以含被动标记的句子占比）
    passive_sent_ratio = sum(1 for x in per_sentence if x["passive"] > 0) / n

    metrics = {
        "sentences": n,
        "chars": char_total,
        "sentence_len_mean": round(len_mean, 1),
        "sentence_len_stdev": round(len_stdev, 1),
        "passive_sentence_ratio": round(passive_sent_ratio, 3),
        "dilution_marker_density": round(dilution / char_total * 1000, 2),
        "hedge_density": round(total("hedge") / char_total * 1000, 2),
        "assertive_count": claims,
        "abstract_noun_density": round(total("abstract_noun") / char_total * 1000, 2),
        "emotion_count": total("emotion"),
        "emotion_center": round(emotion_center, 3) if emotion_center is not None else None,
        "debris_density_per_1k": round(debris_density, 2),
        "sensory_count": total("sensory"),
        "self_imperfect_count": total("self_imperfect"),
        "time_anchor_count": total("time_anchor"),
        "moralizing_count": total("moralizing"),
        "vague_num_count": total("vague_num"),
        "precise_num_count": total("precise_num"),
        "quote_marks": total("quotes"),
        "claim_support_ratio": round(claims / support, 2) if support else None,
    }

    return metrics, per_sentence


# ---------------------------------------------------------------- 解读


def interpret(m):
    """把指标转成有保留的观察。绝不下真假结论。"""
    out = []

    def add(dim, signal, reading):
        out.append({"dim": dim, "signal": signal, "reading": reading})

    # 被动与归因稀释
    if m["passive_sentence_ratio"] >= 0.4:
        add("归因", f"被动/含被动结构句占 {m['passive_sentence_ratio']:.0%}",
            "责任被系统性稀释，指向免责或自保动机")
    elif m["passive_sentence_ratio"] <= 0.15:
        add("归因", f"被动结构句仅 {m['passive_sentence_ratio']:.0%}",
            "主动语态为主，责任指向较明确")

    # 抽象名词
    if m["abstract_noun_density"] >= 8:
        add("归因", f"抽象名词密度 {m['abstract_noun_density']}/千字",
            "用'流程''机制''对接'等词替代具体动作，常见于免责叙述")
    elif m["abstract_noun_density"] <= 3:
        add("归因", f"抽象名词密度 {m['abstract_noun_density']}/千字（低）",
            "较少用抽象词遮蔽具体行为")

    # 模糊限定
    if m["hedge_density"] >= 6:
        add("确定性", f"模糊限定词密度 {m['hedge_density']}/千字",
            "关键处确定性不足；注意模糊是否集中在核心主张上")
    elif m["hedge_density"] <= 1:
        add("确定性", f"模糊限定词密度 {m['hedge_density']}/千字（低）",
            "叙述确定性强，也可能是模板化或立场驱动")

    # 情绪位置
    if m["emotion_center"] is not None:
        if m["emotion_center"] >= 0.6:
            add("情绪", f"情绪词集中在叙述 {m['emotion_center']:.0%} 位置",
                "情绪落在戏剧点/结尾，符合'加工痕迹'的典型形态")
        elif m["emotion_center"] <= 0.35:
            add("情绪", f"情绪词集中在叙述前段（{m['emotion_center']:.0%}）",
                "情绪出现在事件当时而非事后总结，偏向真实回忆")

    # 细节碎屑
    if m["debris_density_per_1k"] >= 12:
        add("细节", f"感官/自我失误碎屑密度 {m['debris_density_per_1k']}/千字（高）",
            "存在不服务于结论的细节，指向真实回忆")
    elif m["debris_density_per_1k"] <= 4:
        add("细节", f"感官/自我失误碎屑密度 {m['debris_density_per_1k']}/千字（低）",
            "细节几乎全部服务于结论，缺少无关碎屑 —— 需人工确认是精简还是编造")

    # 句长方差
    if m["sentence_len_stdev"] / max(m["sentence_len_mean"], 1) < 0.45:
        add("结构", f"句长变异系数 {m['sentence_len_stdev']/max(m['sentence_len_mean'],1):.2f}（低）",
            "句式整齐，可能为事先编排")
    elif m["sentence_len_stdev"] / max(m["sentence_len_mean"], 1) > 0.9:
        add("结构", f"句长变异系数 {m['sentence_len_stdev']/max(m['sentence_len_mean'],1):.2f}（高）",
            "句长参差，偏向真实回忆或口语转录")

    # 时间锚点
    if m["time_anchor_count"] == 0 and m["chars"] > 200:
        add("时间", "无时间锚点",
            "没有任何时间定位，无法验证时间线一致性 —— 这是重大缺口")
    elif m["time_anchor_count"] >= 6:
        add("时间", f"时间锚点 {m['time_anchor_count']} 处（密集）",
            "时间定位丰富；再检查锚点是否互相交错、是否有空洞")

    # 数字形态
    if m["vague_num_count"] >= 3 and m["precise_num_count"] == 0:
        add("数字", f"模糊量词 {m['vague_num_count']} 处、无精确数字",
            "数量被概括化，符合加工形态")
    elif m["precise_num_count"] >= 3:
        add("数字", f"精确数字 {m['precise_num_count']} 处",
            "检查这些数字是否为孤立出现 —— 孤立精确数字反而常是真实信号")

    # 主张与支撑
    if m["claim_support_ratio"] is None and m["assertive_count"] >= 2:
        add("结构", f"强断言 {m['assertive_count']} 处、支撑细节 0 处",
            "有断言无任何可核对的细节支撑，符合空话型立场表达")
    elif m["claim_support_ratio"] is not None and m["claim_support_ratio"] >= 1.5:
        add("结构", f"强断言/支撑 比值 {m['claim_support_ratio']}",
            "主张多、支撑少，倾向情绪勒索或立场表达")

    # 结尾升华
    if m["moralizing_count"] >= 2:
        add("结构", f"出现 {m['moralizing_count']} 处总结升华表达",
            "叙述被'写给人看'过，加工成分上升")

    # 自我不利细节
    if m["self_imperfect_count"] >= 2:
        add("可信度", f"主动交代自身失误 {m['self_imperfect_count']} 处",
            "自曝不利事实是可信度信号（编造者很少这么做）")

    # 引语
    if m["quote_marks"] == 0 and m["chars"] > 150:
        add("语言", "无直接引语",
            "全部转述式叙述，无可核对的原话 —— 事实主张缺少可证伪锚点")

    return out


def render(m, per, findings):
    L = []
    L.append("=" * 58)
    L.append("叙事语言信号量化分析")
    L.append("=" * 58)
    L.append(f"句数 {m['sentences']}　字符 {m['chars']}　平均句长 {m['sentence_len_mean']}")
    L.append("")
    L.append("— 基础指标 " + "-" * 44)
    rows = [
        ("被动/含被动句占比", f"{m['passive_sentence_ratio']:.1%}"),
        ("归因稀释标记密度", f"{m['dilution_marker_density']}/千字"),
        ("模糊限定词密度", f"{m['hedge_density']}/千字"),
        ("强断言次数", m["assertive_count"]),
        ("抽象名词密度", f"{m['abstract_noun_density']}/千字"),
        ("情绪词总数 / 位置重心", f"{m['emotion_count']} / "
            + (f"{m['emotion_center']:.0%}" if m["emotion_center"] is not None else "无")),
        ("细节碎屑密度", f"{m['debris_density_per_1k']}/千字（感官 {m['sensory_count']}，"
            f"自曝失误 {m['self_imperfect_count']}）"),
        ("句长标准差 / 变异系数", f"{m['sentence_len_stdev']} / "
            f"{m['sentence_len_stdev']/max(m['sentence_len_mean'],1):.2f}"),
        ("时间锚点数", m["time_anchor_count"]),
        ("模糊量词 / 精确数字", f"{m['vague_num_count']} / {m['precise_num_count']}"),
        ("引号数", m["quote_marks"]),
        ("强断言 / 支撑 比值", m["claim_support_ratio"]),
    ]
    for k, v in rows:
        L.append(f"  {k:<22} {v}")
    L.append("")
    L.append("— 观察项 " + "-" * 46)
    if not findings:
        L.append("  未触发任何阈值项 —— 请逐句人工研判，指标只作辅助。")
    for f in findings:
        L.append(f"  [{f['dim']}] {f['signal']}")
        L.append(f"      → {f['reading']}")
    L.append("")
    L.append("— 逐句明细 " + "-" * 44)
    L.append(f"  {'#':>3} {'长':>4} {'情':>3} {'限':>3} {'被':>3} {'感':>3} {'时':>3} {'引':>3}  文本")
    for x in per:
        t = x["text"]
        if len(t) > 42:
            t = t[:42] + "…"
        L.append(f"  {x['idx']:>3} {x['len']:>4} {x['emotion']:>3} {x['hedge']:>3} "
                 f"{x['passive']:>3} {x['sensory']:>3} {x['time_anchor']:>3} {x['quotes']:>3}  {t}")
    L.append("")
    L.append("—" * 58)
    L.append("提示：以上全部为信号，不是结论。判定需结合 signal-catalog.md 逐项研判，")
    L.append("并对每个猜测给出区分性检验（见 verification-playbook.md）。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="叙事语言信号量化分析器")
    ap.add_argument("path", help="文本文件路径，'-' 表示从标准输入读取")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--short", action="store_true",
                    help="短文本/口述模式（连麦、访谈、聊天记录等一两句陈述）")
    ap.add_argument("--implicature", action="store_true",
                    help="语用模式：拆'话里有话'（言外动作、预设、回避、语用标尺）")
    args = ap.parse_args()

    if args.path == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(args.path, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"找不到文件: {args.path}", file=sys.stderr)
            sys.exit(1)

    if not text.strip():
        print("输入为空。", file=sys.stderr)
        sys.exit(1)

    if args.implicature:
        m = analyze_pragmatic(text)
        findings = interpret_pragmatic(m)
        if args.json:
            _pub = {k: v for k, v in m.items() if not k.startswith("_")}
            print(json.dumps({"mode": "implicature", "metrics": _pub,
                              "findings": findings}, ensure_ascii=False, indent=2))
        else:
            print("=" * 58)
            print("语用层分析 · 拆「话里有话」")
            print("=" * 58)
            print(f"原话（{m['chars']} 字）：{text.strip()}")
            print("")
            print("— 形式信号 " + "-" * 45)
            def fmt(lst):
                return "、".join(lst) if lst else "无"
            print(f"  元话语标记      {fmt(m['metadiscourse'])}")
            print(f"  否定式缓冲      {fmt(m['neg_buffer'])}")
            print(f"  弱化评价词      {fmt(m['hedged_eval'])}")
            print(f"  预设触发词      {fmt(m['presupposition'])}")
            print(f"  回避/拖延标记    {fmt(m['avoidance'])}")
            print(f"  人称滑动        {fmt(m['agent_shift'])}")
            print("")
            print("— 推断的言外动作 " + "-" * 40)
            if m["inferred_acts"]:
                for a in m["inferred_acts"]:
                    print(f"  · {a}")
            else:
                print("  未检出明显的言外动作，可能是一句字面表达")
            print("")
            print("— 承诺要素 " + "-" * 45)
            print(f"  日期 {'有' if m['has_date'] else '无'}"
                  f"　人名 {'有' if m['has_owner'] else '无'}"
                  f"　数字 {'有' if m['has_number'] else '无'}"
                  f"　（{m['commitment_score']}/3）")
            print("")
            print("— 观察项 " + "-" * 46)
            if not findings:
                print("  未触发 —— 这句话可能是字面表达，不必过度解读。")
            for f in findings:
                print(f"  [{f['dim']}] {f['signal']}")
                print(f"      → {f['reading']}")
            print("")
            print("—" * 58)
            print("提示：以上标注的是语言动作，不是对方的动机。")
            print("推断依赖语境，纯文本场景有效；若有语气/表情，可能推翻上述判断。")
        return

    if args.short:
        m = analyze_short(text)
        findings = interpret_short(m)
        if args.json:
            print(json.dumps({"mode": "short", "metrics": m, "findings": findings},
                             ensure_ascii=False, indent=2))
        else:
            print("=" * 58)
            print("叙事语言信号 · 短文本/口述模式")
            print("=" * 58)
            print(f"字符数 {m['chars']}")
            print("")
            print("— 基础指标 " + "-" * 44)
            rows = [
                ("第三方指称", f"{m['third_party_count']} 处"),
                ("自身不利披露", f"{m['self_expose_count']} 处"),
                ("责任前置标记", f"{m['blame_shift_count']} 处"),
                ("口语衔接标记", f"{m['discourse_marker_count']} 处"),
                ("财产/债务词", f"{m['property_count']} 处"),
                ("权益型诉求词", f"{m['emotion_claim_count']} 处"),
                ("信息不对称标记", f"{m['info_gap_count']} 处"),
                ("防御性表述", f"{m['defensive_count']} 处"),
                ("算计性表述", f"{m['calculating_count']} 处"),
                ("两头占标记", f"{m['free_rider_count']} 处"),
                ("疑问密度", f"{m['question_density']}/千字"),
                ("第一人称", f"{m['first_person']} 处"),
                ("第二人称", f"{m['second_person']} 处"),
                ("第三人称", f"{m['third_person']} 处"),
                ("已发生事实标记", f"{m['past_marker_count']} 处"),
                ("将来/可能标记", f"{m['future_marker_count']} 处"),
            ]
            for k, v in rows:
                print(f"  {k:<16} {v}")
            print("")
            print("— 观察项 " + "-" * 46)
            if not findings:
                print("  未触发任何阈值项 —— 请逐句人工研判，指标只作辅助。")
            for f in findings:
                print(f"  [{f['dim']}] {f['signal']}")
                print(f"      → {f['reading']}")
            print("")
            print("—" * 58)
            print("提示：短文本模式不依赖统计量，指标基于结构特征。")
            print("仍需结合 signal-catalog.md 人工研判；口述场景尤重目的层。")
        return

    metrics, per = analyze(text)
    findings = interpret(metrics)

    if args.json:
        print(json.dumps({"metrics": metrics, "findings": findings, "sentences": per},
                         ensure_ascii=False, indent=2))
    else:
        print(render(metrics, per, findings))


if __name__ == "__main__":
    main()
