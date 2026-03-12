import json
import os
import re
import time
from typing import Any, Dict, List

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


SYSTEM_PROMPT = """
你是一个专门服务短剧/漫剧策划的中文创意编辑，不是学术分析助手。

你的任务是把“关键词/题材/IP”转成适合短剧创作的爆点设定。

硬性要求：
1. 全部输出中文。
2. 强调短剧感、戏剧性、冲突、反差、钩子、网感。
3. 不要写得像论文、百科、课堂分析。
4. 不要空话套话，要具体、能拍、能宣发。
5. 即使用户输入很短，也尽量给出可用结果。
6. 输出固定结构化文本，不要输出 JSON，不要输出 Markdown 代码块，不要补充格式说明。
7. 优先追求“新颖、够炸、像短剧榜单会出现的设定”，其次才是稳妥和完整。
8. 不要只给出普通的“重生后逆袭”“黑化复仇”老套路，必须做热点机制嫁接。
9. 设定必须清楚，用户看一遍就能懂，不要故弄玄虚。
10. 优先单核设定，不要堆太多机制。
11. 优先情绪爽感和戏剧冲突，不要往刑侦、推理、世界观解释上跑偏。
12. 如果去掉输入物本身，故事仍然成立，说明设定失败，必须重做。
""".strip()


TEXT_PROTOCOL_PROMPT = """
请严格按下面的固定文本协议输出，不能多也不能少：

[INPUT_INFO]
topic: ...
hot_keywords: 关键词1 | 关键词2 | 关键词3
input_type: ...

[ANALYSIS]
核心标签: 条目1 | 条目2 | 条目3
基础属性_显性特征: 条目1 | 条目2 | 条目3
人物_世界观_题材元素: 条目1 | 条目2 | 条目3
可延展的反差点: 条目1 | 条目2 | 条目3
潜在戏剧冲突: 条目1 | 条目2 | 条目3
可结合的热点方向: 条目1 | 条目2 | 条目3
推荐热点嫁接机制: 条目1 | 条目2 | 条目3
该输入不可替代的独有规则: 条目1 | 条目2 | 条目3

[CANDIDATE_1]
设定名: ...
一句话卖点: ...
爆点标题: ...
核心反差_金手指_爆点: ...
主要冲突: ...
热点嫁接说明: ...
受众倾向: ...
是否适合短剧节奏: ...
适合理由: ...
short_drama_score: 1-10整数
novelty_score: 1-10整数
hook_score: 1-10整数
trend_fit_score: 1-10整数
起: 环境规则：...；主角登场：...；激励事件：...；外部目标：...；走出舒适区：...；困境：...
承: 初识红利：...；伙伴爱情：...；起始对手：...；阻力对抗：...；故事拐点：...
转: 调整目标：...；确认对手：...；冲突升级：...；第一次决战：...；遭受重挫：...
合: 疗伤反省：...；解决方案：...；韧性成长：...；最终决战：...；回到原点：...；续作伏笔：...

[CANDIDATE_2]
... 同上

[CANDIDATE_3]
... 同上

[SELECTED]
选中设定名: ...
主角设定: ...
核心矛盾: ...
开篇爆点: ...
剧情主线: ...
十集内推进: 1-2集... || 3-4集... || 5-6集... || 7-8集... || 9-10集...
收尾钩子: ...
起: 环境规则：...；主角登场：...；激励事件：...；外部目标：...；走出舒适区：...；困境：...
承: 初识红利：...；伙伴爱情：...；起始对手：...；阻力对抗：...；故事拐点：...
转: 调整目标：...；确认对手：...；冲突升级：...；第一次决战：...；遭受重挫：...
合: 疗伤反省：...；解决方案：...；韧性成长：...；最终决战：...；回到原点：...；续作伏笔：...

硬性要求：
1. 所有列表字段一律用 ` | ` 分隔。
2. 十集内推进一律用 ` || ` 分隔五段。
3. 必须输出 3 个候选，不多不少。
4. 对于“贩卖机”这类物体，设定必须体现投币、扫码、出货口、货道、固定地点、等待别人触发中的至少 2 项，否则判失败重写。
5. 如果把输入物替换成手机、电脑、系统面板后故事还成立，则判失败重写。
6. 优先新颖、够炸、像短剧榜单感；但一句话也必须能讲清。
7. 每个候选和最终选中方案都必须补全“起/承/转/合”四段骨架，每段只写单行文本，并严格保留字段内的小标签顺序。
""".strip()


ANALYSIS_PROTOCOL_PROMPT = """
请严格按下面的固定文本协议输出，不能多也不能少：

[INPUT_INFO]
topic: ...
hot_keywords: 关键词1 | 关键词2 | 关键词3
input_type: ...

[ANALYSIS]
核心标签: 条目1 | 条目2 | 条目3
基础属性_显性特征: 条目1 | 条目2 | 条目3
人物_世界观_题材元素: 条目1 | 条目2 | 条目3
可延展的反差点: 条目1 | 条目2 | 条目3
潜在戏剧冲突: 条目1 | 条目2 | 条目3
可结合的热点方向: 条目1 | 条目2 | 条目3
推荐热点嫁接机制: 条目1 | 条目2 | 条目3
该输入不可替代的独有规则: 条目1 | 条目2 | 条目3

硬性要求：
1. 所有列表字段一律用 ` | ` 分隔。
2. 每个字段给 3 到 5 条，尽量短，不要写成长段解释。
3. 全部输出中文。
""".strip()


SECOND_ROUND_PROTOCOL_PROMPT = """
请严格按下面的固定文本协议输出，不能多也不能少：

[SECOND_ROUND]
标题: ...
核心设定: ...
主要人物关系: ...
核心冲突/看点: ...
简短梗概: ...

硬性要求：
1. 全部输出中文。
2. 每个字段只输出单行文本，不要换行，不要加列表序号。
3. 必须保留基础版本的核心亮点，只根据用户修改意见做优化。
4. 风格要更聚焦、更适合短剧宣发和梗概展示。
5. 如果用户修改意见为空，也要基于基础版本直接做一版更完整的优化稿。
""".strip()


ANALYSIS_DEVELOPER_PROMPT = """
你的任务是只输出“设定拆解”，不要输出候选设定和梗概。

输出部分仅包含：
1. input_info
2. analysis

analysis 至少包含以下字段：
- 核心标签
- 基础属性_显性特征
- 人物_世界观_题材元素
- 可延展的反差点
- 潜在戏剧冲突
- 可结合的热点方向
- 推荐热点嫁接机制
- 该输入不可替代的独有规则

要求：
- 如果输入更像“贩卖机”这类物体/概念，就偏属性拆解
- 如果输入更像“红楼梦”这类已有IP，就偏角色、关系、气质、故事框架拆解
- 如果输入更像“大女主/校园复仇/豪门/重生”这类题材母题，就偏人设、关系、爽点、冲突拆解
- 每个字段给 3 到 5 条，便于用户后续勾选
- 要有创意筛选价值，避免空话
""".strip()


DEVELOPER_PROMPT = """
请按以下流程生成结果：

第1部分 input_info：
- topic: 用户输入的关键词/题材/IP
- hot_keywords: 用户输入的热点/风格关键词，没有就给空数组
- input_type: "物体/概念"、"题材/母题"、"已有IP" 三选一，按最合适的判断

第2部分 analysis：
至少包含以下字段，字段值都用中文数组或中文字符串：
- 核心标签
- 基础属性_显性特征
- 人物_世界观_题材元素
- 可延展的反差点
- 潜在戏剧冲突
- 可结合的热点方向
- 推荐热点嫁接机制
- 该输入不可替代的独有规则

如果输入更像“贩卖机”这类物体/概念，就偏属性拆解。
如果输入更像“红楼梦”这类已有IP，就偏角色、关系、气质、故事框架拆解。
如果输入更像“大女主/校园复仇/豪门/重生”这类题材母题，就偏人设、关系、爽点、冲突拆解。

第3部分 candidates：
输出 3 到 5 个短剧向新颖设定候选。每个候选都必须包含：
- 设定名
- 一句话卖点
- 爆点标题
- 核心反差_金手指_爆点
- 主要冲突
- 热点嫁接说明
- 受众倾向
- 是否适合短剧节奏
- 适合理由
- short_drama_score: 1 到 10 的整数
- novelty_score: 1 到 10 的整数
- hook_score: 1 到 10 的整数
- trend_fit_score: 1 到 10 的整数
- 起：必须包含“环境规则、主角登场、激励事件、外部目标、走出舒适区、困境”
- 承：必须包含“初识红利、伙伴爱情、起始对手、阻力对抗、故事拐点”
- 转：必须包含“调整目标、确认对手、冲突升级、第一次决战、遭受重挫”
- 合：必须包含“疗伤反省、解决方案、韧性成长、最终决战、回到原点、续作伏笔”

要求：
- 候选不要太像普通网文简介，要像短剧宣发设定
- 要有反差感、爆点感、可视化感
- 结合热点关键词，但不要生硬堆砌
- 每个候选都必须同时包含：原输入元素 + 热点机制 + 强反差身份/规则
- 至少 2 个候选要明显跳出常规改编套路，做到“一听就想点开”
- 禁止只做平移式改写，例如“某角色重生后变强了”这种太常见的方案
- 优先考虑短剧榜单常见高点击元素：替嫁、赘婿、直播、系统、读心、审判、先婚后爱、全网围观、身份反转、公开打脸
- 每个候选最多只允许 1 个核心超能力/规则机制，其他内容只能服务这个机制
- 候选的一句话卖点必须让没有上下文的人也能立刻听懂
- 如果一个候选需要解释很多层才能明白，判为不合格
- 剧情梗概必须围绕一个主目标推进，不能同时展开多条平行主线
- 候选的核心设定最好能压缩成 20 字左右的一句话钩子
- 优先“仇人主动靠近主角机制”的设定，这样更有短剧戏剧性
- 少写警方侦查、复杂幕后组织、技术解释，多写打脸、反杀、公开翻车、情绪报复
- 对于“贩卖机”这类物体输入，候选必须明确使用其独有规则，例如：投币、扫码、出货、货道、固定地点、只能等待别人来使用
- 每个候选都要额外通过一个自检：如果把“贩卖机”替换成“手机/电脑/系统面板”后故事还成立，则该候选判为失败
- 起承转合是故事骨架，不替代原有梗概字段；每段都要具体，不能只写抽象词
- 每个“起/承/转/合”字段内部都要按固定小标签输出，使用全角冒号和分号连接，不能省略标签
- “起”重点写世界/场域规则、主角为何被逼离开舒适区
- “承”重点写主角拿到的第一波红利、关系建立、初始敌我关系和第一批拐点
- “转”重点写目标升级、敌人确认、冲突放大以及第一次重大失败
- “合”重点写受挫后的反思、新方案、韧性成长、最终决战、回到原点后的变化和续作钩子
- 物体类输入时，起承转合四段里至少 3 段要直接依赖该物体规则推进剧情

第4部分 selected_synopsis：
从 candidates 里选出最适合短剧节奏的 1 个，输出：
- 选中设定名
- 主角设定
- 核心矛盾
- 开篇爆点
- 剧情主线
- 十集内推进: 数组，按 1-2集、3-4集、5-6集、7-8集、9-10集 分段
- 收尾钩子
- 起：必须包含“环境规则、主角登场、激励事件、外部目标、走出舒适区、困境”
- 承：必须包含“初识红利、伙伴爱情、起始对手、阻力对抗、故事拐点”
- 转：必须包含“调整目标、确认对手、冲突升级、第一次决战、遭受重挫”
- 合：必须包含“疗伤反省、解决方案、韧性成长、最终决战、回到原点、续作伏笔”

输出格式：
{
  "input_info": {...},
  "analysis": {...},
  "candidates": [...],
  "selected_synopsis": {...}
}

生成思路必须遵守：
1. 先拆输入本身的原始设定元素。
2. 再挑选最适合的热点机制去嫁接。
3. 再把两者碰撞成高概念设定。
4. 最后筛掉太像常规女频/男频套路的候选。
5. 筛掉设定机制过多、主线不清、需要解释太久的候选。
6. 在“合理”和“炸裂”之间，优先选择更好讲、更有情绪价值的方案。
7. 对物体类输入，优先选择“这个物体本身决定了戏剧规则”的方案。
""".strip()


SECOND_ROUND_DEVELOPER_PROMPT = """
你的任务是做“多轮修改生成”：

你会收到：
1. 用户原始主题
2. 热点关键词
3. 第一轮中用户选中的一个候选版本
4. 用户补充的修改意见

请基于这些信息，输出一版优化后的当前版本梗概。

生成要求：
1. 保留基础版本最有记忆点的核心机制、反差感和短剧钩子。
2. 用户修改意见优先作为优化方向，但不要把设定改到完全不像原候选。
3. 输出要比第一轮候选更完整、更聚焦，像可以直接继续往短剧策划走的一版梗概。
4. 避免复杂世界观和过多机制，仍然坚持单核设定。
5. 优先强调人物关系张力、核心冲突、强情绪和可视化名场面。
6. 如果“主要人物关系”不复杂，也要给出一句明确关系描述，不能留空。
""".strip()


def infer_input_type(topic: str) -> str:
    topic = topic.strip()
    ip_clues = ["红楼梦", "西游记", "三国", "水浒", "甄嬛传", "哈利波特"]
    genre_clues = ["大女主", "复仇", "豪门", "重生", "先婚后爱", "逆袭", "校园", "系统", "直播"]
    if any(clue in topic for clue in ip_clues):
        return "已有IP"
    if any(clue in topic for clue in genre_clues):
        return "题材/母题"
    return "物体/概念"


def normalize_hot_keywords(raw_text: str) -> List[str]:
    if not raw_text.strip():
        return []
    parts = re.split(r"[，,、/\s]+", raw_text.strip())
    return [part for part in parts if part]


def extract_content_from_volc_response(data: Dict[str, Any]) -> str:
    if isinstance(data.get("content"), str):
        return data["content"]

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "\n".join(part for part in text_parts if part)
        if isinstance(content, str):
            return content

    result = data.get("Result")
    if isinstance(result, dict):
        for key in ["Answer", "Content", "content"]:
            if isinstance(result.get(key), str):
                return result[key]

    return json.dumps(data, ensure_ascii=False)


def split_items(value: str, sep: str = "|") -> List[str]:
    parts = [part.strip() for part in value.split(sep)]
    return [part for part in parts if part]


def parse_key_value_lines(block_text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for raw_line in block_text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def parse_protocol_output(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```[\w-]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    pattern = re.compile(r"^\[(INPUT_INFO|ANALYSIS|CANDIDATE_\d+|SELECTED)\]\s*$", re.M)
    matches = list(pattern.finditer(cleaned))
    if not matches:
        raise RuntimeError(
            json.dumps(
                {
                    "stage": "protocol_parse_failed",
                    "error": "未找到协议分块标签",
                    "raw_text": text,
                },
                ensure_ascii=False,
            )
        )

    sections: Dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        sections[name] = cleaned[start:end].strip()

    input_info_raw = parse_key_value_lines(sections.get("INPUT_INFO", ""))
    analysis_raw = parse_key_value_lines(sections.get("ANALYSIS", ""))
    selected_raw = parse_key_value_lines(sections.get("SELECTED", ""))

    if not input_info_raw or not analysis_raw or not selected_raw:
        raise RuntimeError(
            json.dumps(
                {
                    "stage": "protocol_parse_failed",
                    "error": "缺少必要分块内容",
                    "raw_text": text,
                    "sections": list(sections.keys()),
                },
                ensure_ascii=False,
            )
        )

    analysis = {key: split_items(value) for key, value in analysis_raw.items()}

    candidates: List[Dict[str, Any]] = []
    for name in sorted(key for key in sections if key.startswith("CANDIDATE_")):
        candidate_raw = parse_key_value_lines(sections[name])
        if not candidate_raw:
            continue
        for score_key in ["short_drama_score", "novelty_score", "hook_score", "trend_fit_score"]:
            if score_key in candidate_raw:
                match = re.search(r"\d+", candidate_raw[score_key])
                candidate_raw[score_key] = int(match.group(0)) if match else 0
        candidates.append(candidate_raw)

    if len(candidates) < 3:
        raise RuntimeError(
            json.dumps(
                {
                    "stage": "protocol_parse_failed",
                    "error": "候选数量不足",
                    "raw_text": text,
                    "candidate_count": len(candidates),
                },
                ensure_ascii=False,
            )
        )

    selected = dict(selected_raw)
    selected["十集内推进"] = split_items(selected_raw.get("十集内推进", ""), sep="||")

    return {
        "input_info": {
            "topic": input_info_raw.get("topic", ""),
            "hot_keywords": split_items(input_info_raw.get("hot_keywords", "")),
            "input_type": input_info_raw.get("input_type", ""),
        },
        "analysis": analysis,
        "candidates": candidates,
        "selected_synopsis": selected,
    }


def parse_analysis_output(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```[\w-]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    pattern = re.compile(r"^\[(INPUT_INFO|ANALYSIS)\]\s*$", re.M)
    matches = list(pattern.finditer(cleaned))
    if not matches:
        raise RuntimeError(
            json.dumps(
                {
                    "stage": "analysis_parse_failed",
                    "error": "未找到 INPUT_INFO 或 ANALYSIS 分块",
                    "raw_text": text,
                },
                ensure_ascii=False,
            )
        )

    sections: Dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        sections[name] = cleaned[start:end].strip()

    input_info_raw = parse_key_value_lines(sections.get("INPUT_INFO", ""))
    analysis_raw = parse_key_value_lines(sections.get("ANALYSIS", ""))

    if not input_info_raw or not analysis_raw:
        raise RuntimeError(
            json.dumps(
                {
                    "stage": "analysis_parse_failed",
                    "error": "缺少必要分块内容",
                    "raw_text": text,
                    "sections": list(sections.keys()),
                },
                ensure_ascii=False,
            )
        )

    analysis = {key: split_items(value) for key, value in analysis_raw.items()}

    return {
        "input_info": {
            "topic": input_info_raw.get("topic", ""),
            "hot_keywords": split_items(input_info_raw.get("hot_keywords", "")),
            "input_type": input_info_raw.get("input_type", ""),
        },
        "analysis": analysis,
    }


def parse_second_round_output(text: str) -> Dict[str, str]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```[\w-]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    match = re.search(r"\[SECOND_ROUND\]\s*(.*)", cleaned, re.S)
    if not match:
        raise RuntimeError(
            json.dumps(
                {
                    "stage": "second_round_parse_failed",
                    "error": "未找到 SECOND_ROUND 分块",
                    "raw_text": text,
                },
                ensure_ascii=False,
            )
        )

    parsed = parse_key_value_lines(match.group(1).strip())
    required_fields = ["标题", "核心设定", "主要人物关系", "核心冲突/看点", "简短梗概"]
    missing_fields = [field for field in required_fields if not parsed.get(field)]
    if missing_fields:
        raise RuntimeError(
            json.dumps(
                {
                    "stage": "second_round_parse_failed",
                    "error": "缺少必要字段",
                    "missing_fields": missing_fields,
                    "raw_text": text,
                },
                ensure_ascii=False,
            )
        )

    return {field: parsed[field] for field in required_fields}


def post_with_retry(url: str, headers: Dict[str, str], payload: Dict[str, Any], retries: int = 2) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(20, 300),
            )
        except requests.exceptions.ReadTimeout as exc:
            last_error = exc
            if attempt == retries:
                raise
            time.sleep(1.5 * (attempt + 1))
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt == retries:
                raise
            time.sleep(1.0 * (attempt + 1))
    if last_error:
        raise last_error
    raise RuntimeError("请求失败")


def call_volcengine_model(topic: str, hot_keywords: List[str]) -> Dict[str, Any]:
    api_key = os.getenv("MODEL_AGENT_API_KEY")
    base_url = os.getenv("MODEL_AGENT_BASE_URL")
    model_name = os.getenv("MODEL_AGENT_MODEL_NAME")

    if not api_key or not base_url or not model_name:
        raise RuntimeError("未检测到完整的 MODEL_AGENT_* 配置")

    user_prompt = f"""
用户输入主题：{topic}
热点关键词：{json.dumps(hot_keywords, ensure_ascii=False)}

请严格按固定结构化文本协议输出。
""".strip()

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{DEVELOPER_PROMPT}\n\n{TEXT_PROTOCOL_PROMPT}"},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
    }
    response = post_with_retry(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = extract_content_from_volc_response(data)
    parsed = parse_protocol_output(content)
    parsed["_debug_raw_model_output"] = content
    return parsed


def call_volcengine_model_analysis(topic: str, hot_keywords: List[str]) -> Dict[str, Any]:
    api_key = os.getenv("MODEL_AGENT_API_KEY")
    base_url = os.getenv("MODEL_AGENT_BASE_URL")
    model_name = os.getenv("MODEL_AGENT_MODEL_NAME")

    if not api_key or not base_url or not model_name:
        raise RuntimeError("未检测到完整的 MODEL_AGENT_* 配置")

    user_prompt = f"""
用户输入主题：{topic}
热点关键词：{json.dumps(hot_keywords, ensure_ascii=False)}

请只输出设定拆解，不要输出候选设定和梗概。
""".strip()

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{ANALYSIS_DEVELOPER_PROMPT}\n\n{ANALYSIS_PROTOCOL_PROMPT}"},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
    }
    response = post_with_retry(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = extract_content_from_volc_response(data)
    parsed = parse_analysis_output(content)
    parsed["_debug_raw_model_output"] = content
    return parsed


def call_volcengine_model_from_analysis(topic: str, hot_keywords: List[str], selected_analysis: Dict[str, List[str]]) -> Dict[str, Any]:
    api_key = os.getenv("MODEL_AGENT_API_KEY")
    base_url = os.getenv("MODEL_AGENT_BASE_URL")
    model_name = os.getenv("MODEL_AGENT_MODEL_NAME")

    if not api_key or not base_url or not model_name:
        raise RuntimeError("未检测到完整的 MODEL_AGENT_* 配置")

    user_prompt = f"""
用户输入主题：{topic}
热点关键词：{json.dumps(hot_keywords, ensure_ascii=False)}
用户确认后的设定拆解：{json.dumps(selected_analysis, ensure_ascii=False)}

请严格按固定结构化文本协议输出。
特别要求：
1. [ANALYSIS] 分块必须直接使用用户确认后的设定拆解，不要改写字段名，不要新增其他分析字段。
2. 3 个候选和最终选中梗概必须优先围绕这些已选项生成。
""".strip()

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{DEVELOPER_PROMPT}\n\n{TEXT_PROTOCOL_PROMPT}"},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
    }
    response = post_with_retry(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = extract_content_from_volc_response(data)
    parsed = parse_protocol_output(content)
    parsed["analysis"] = selected_analysis
    parsed["_debug_raw_model_output"] = content
    return parsed


def call_volcengine_model_second_round(
    topic: str,
    hot_keywords: List[str],
    selected_candidate: Dict[str, Any],
    feedback: str,
) -> Dict[str, Any]:
    api_key = os.getenv("MODEL_AGENT_API_KEY")
    base_url = os.getenv("MODEL_AGENT_BASE_URL")
    model_name = os.getenv("MODEL_AGENT_MODEL_NAME")

    if not api_key or not base_url or not model_name:
        raise RuntimeError("未检测到完整的 MODEL_AGENT_* 配置")

    user_prompt = f"""
用户输入主题：{topic}
热点关键词：{json.dumps(hot_keywords, ensure_ascii=False)}
基础候选版本：{json.dumps(selected_candidate, ensure_ascii=False)}
用户修改意见：{feedback.strip() or "无，直接基于该候选优化输出"}

请严格按固定文本协议输出。
""".strip()

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{SECOND_ROUND_DEVELOPER_PROMPT}\n\n{SECOND_ROUND_PROTOCOL_PROMPT}"},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
    }
    response = post_with_retry(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = extract_content_from_volc_response(data)
    parsed = parse_second_round_output(content)
    parsed["_debug_raw_model_output"] = content
    return parsed


def call_volcengine_agent(topic: str, hot_keywords: List[str]) -> Dict[str, Any]:
    api_key = os.getenv("VOLCENGINE_AGENT_API_KEY")
    bot_id = os.getenv("VOLCENGINE_BOT_ID")
    endpoint = os.getenv(
        "VOLCENGINE_AGENT_API_URL",
        "https://open.feedcoopapi.com/agent_api/agent/chat/completion",
    )

    if not api_key:
        raise RuntimeError("未检测到 VOLCENGINE_AGENT_API_KEY")
    if not bot_id:
        raise RuntimeError("未检测到 VOLCENGINE_BOT_ID")

    user_prompt = f"""
用户输入主题：{topic}
热点关键词：{json.dumps(hot_keywords, ensure_ascii=False)}

请严格按固定结构化文本协议输出。
""".strip()

    payload = {
        "bot_id": bot_id,
        "stream": False,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{DEVELOPER_PROMPT}\n\n{TEXT_PROTOCOL_PROMPT}"},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = post_with_retry(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = extract_content_from_volc_response(data)
    parsed = parse_protocol_output(content)
    parsed["_debug_raw_model_output"] = content
    return parsed


def call_volcengine_agent_analysis(topic: str, hot_keywords: List[str]) -> Dict[str, Any]:
    api_key = os.getenv("VOLCENGINE_AGENT_API_KEY")
    bot_id = os.getenv("VOLCENGINE_BOT_ID")
    endpoint = os.getenv(
        "VOLCENGINE_AGENT_API_URL",
        "https://open.feedcoopapi.com/agent_api/agent/chat/completion",
    )

    if not api_key:
        raise RuntimeError("未检测到 VOLCENGINE_AGENT_API_KEY")
    if not bot_id:
        raise RuntimeError("未检测到 VOLCENGINE_BOT_ID")

    user_prompt = f"""
用户输入主题：{topic}
热点关键词：{json.dumps(hot_keywords, ensure_ascii=False)}

请只输出设定拆解，不要输出候选设定和梗概。
""".strip()

    payload = {
        "bot_id": bot_id,
        "stream": False,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{ANALYSIS_DEVELOPER_PROMPT}\n\n{ANALYSIS_PROTOCOL_PROMPT}"},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = post_with_retry(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = extract_content_from_volc_response(data)
    parsed = parse_analysis_output(content)
    parsed["_debug_raw_model_output"] = content
    return parsed


def call_volcengine_agent_from_analysis(topic: str, hot_keywords: List[str], selected_analysis: Dict[str, List[str]]) -> Dict[str, Any]:
    api_key = os.getenv("VOLCENGINE_AGENT_API_KEY")
    bot_id = os.getenv("VOLCENGINE_BOT_ID")
    endpoint = os.getenv(
        "VOLCENGINE_AGENT_API_URL",
        "https://open.feedcoopapi.com/agent_api/agent/chat/completion",
    )

    if not api_key:
        raise RuntimeError("未检测到 VOLCENGINE_AGENT_API_KEY")
    if not bot_id:
        raise RuntimeError("未检测到 VOLCENGINE_BOT_ID")

    user_prompt = f"""
用户输入主题：{topic}
热点关键词：{json.dumps(hot_keywords, ensure_ascii=False)}
用户确认后的设定拆解：{json.dumps(selected_analysis, ensure_ascii=False)}

请严格按固定结构化文本协议输出。
特别要求：
1. [ANALYSIS] 分块必须直接使用用户确认后的设定拆解，不要改写字段名，不要新增其他分析字段。
2. 3 个候选和最终选中梗概必须优先围绕这些已选项生成。
""".strip()

    payload = {
        "bot_id": bot_id,
        "stream": False,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{DEVELOPER_PROMPT}\n\n{TEXT_PROTOCOL_PROMPT}"},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = post_with_retry(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = extract_content_from_volc_response(data)
    parsed = parse_protocol_output(content)
    parsed["analysis"] = selected_analysis
    parsed["_debug_raw_model_output"] = content
    return parsed


def call_volcengine_agent_second_round(
    topic: str,
    hot_keywords: List[str],
    selected_candidate: Dict[str, Any],
    feedback: str,
) -> Dict[str, Any]:
    api_key = os.getenv("VOLCENGINE_AGENT_API_KEY")
    bot_id = os.getenv("VOLCENGINE_BOT_ID")
    endpoint = os.getenv(
        "VOLCENGINE_AGENT_API_URL",
        "https://open.feedcoopapi.com/agent_api/agent/chat/completion",
    )

    if not api_key:
        raise RuntimeError("未检测到 VOLCENGINE_AGENT_API_KEY")
    if not bot_id:
        raise RuntimeError("未检测到 VOLCENGINE_BOT_ID")

    user_prompt = f"""
用户输入主题：{topic}
热点关键词：{json.dumps(hot_keywords, ensure_ascii=False)}
基础候选版本：{json.dumps(selected_candidate, ensure_ascii=False)}
用户修改意见：{feedback.strip() or "无，直接基于该候选优化输出"}

请严格按固定文本协议输出。
""".strip()

    payload = {
        "bot_id": bot_id,
        "stream": False,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{SECOND_ROUND_DEVELOPER_PROMPT}\n\n{SECOND_ROUND_PROTOCOL_PROMPT}"},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = post_with_retry(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )
    response.raise_for_status()
    data = response.json()
    content = extract_content_from_volc_response(data)
    parsed = parse_second_round_output(content)
    parsed["_debug_raw_model_output"] = content
    return parsed


def build_local_demo(topic: str, hot_keywords: List[str]) -> Dict[str, Any]:
    input_type = infer_input_type(topic)
    hot = hot_keywords or ["逆袭", "反转"]

    if input_type == "已有IP":
        analysis = {
            "核心标签": [topic, "经典关系网", "群像", "命运感", "情绪浓度"],
            "基础属性_显性特征": ["自带人物关系", "已有故事骨架", "角色气质鲜明", "可做现代化嫁接"],
            "人物_世界观_题材元素": ["核心人物群像", "家族/阶层结构", "爱恨关系", "盛极而衰的宿命气质"],
            "可延展的反差点": ["古典人物进入现代修罗场", "高门叙事改造成直播/豪门/职场", "柔弱外壳下的狠决反击"],
            "潜在戏剧冲突": ["情感与利益绑定", "家族规则压迫个体", "旧关系在新场景中重新洗牌"],
            "可结合的热点方向": hot,
            "推荐热点嫁接机制": ["重生复盘", "直播审判", "系统任务", "先婚后爱", "豪门夺权"],
        }
        candidates = [
            {
                "设定名": "红楼弹幕审判局",
                "一句话卖点": "林黛玉一开口就能看见每个人头顶的灭门弹幕，她决定直播改写贾府全员死局。",
                "爆点标题": "病弱林妹妹，成了贾府唯一能看见死亡弹幕的人",
                "核心反差_金手指_爆点": "古典病弱才女 + 死亡弹幕预警",
                "主要冲突": "她每提前说破一次灾祸，就会被当成祸端，整个贾府都开始想让她闭嘴。",
                "热点嫁接说明": "把红楼群像和家族衰败感，嫁接到死亡弹幕预警这一个核心机制上。",
                "受众倾向": "女频",
                "是否适合短剧节奏": "适合",
                "适合理由": "每集都能公开揭一层真相，天然有断点和围观感。",
                "short_drama_score": 9,
                "novelty_score": 9,
                "hook_score": 10,
                "trend_fit_score": 9,
                "起": "环境规则：贾府繁华表象下人人都被命运和门第规则绑死；主角登场：病弱黛玉初入贾府；激励事件：她突然看见众人头顶死亡弹幕；外部目标：改写贾府灭门死局；走出舒适区：她必须从沉默自保转向主动揭破秘密；困境：她越早开口越容易被当成祸端。",
                "承": "初识红利：黛玉先靠弹幕预警躲过几次暗害；伙伴爱情：她与宝玉、王熙凤形成危险同盟；起始对手：不信她又忌惮她的贾府长辈；阻力对抗：她每说破一次灾祸就会遭到更强围剿；故事拐点：贾府内部开始围绕她集体站队。",
                "转": "调整目标：她从单纯保命改成主动改写关键关系；确认对手：真正操盘贾府衰败的幕后之人浮出水面；冲突升级：她公开拆局后全府将她视为祸根；第一次决战：她试图在大场面上提前揭穿死局；遭受重挫：不仅没被相信，反而差点被彻底禁声。",
                "合": "疗伤反省：黛玉意识到光靠预警无法救人；解决方案：她决定借直播和众目睽睽强行同步真相；韧性成长：从病弱旁观者变成主动改局者；最终决战：在家宴上逼出幕后黑手；回到原点：她仍站在贾府中心，却不再只是被命运摆布的人；续作伏笔：最后一条弹幕提示真正死局还没结束。",
            },
            {
                "设定名": "替嫁黛玉掌贾府",
                "一句话卖点": "林黛玉被迫替嫁冲喜进贾府，白天是病美人新妇，晚上是专收家产的冷面清算人。",
                "爆点标题": "她是来冲喜的，也是来抄家的",
                "核心反差_金手指_爆点": "病弱替嫁新娘 + 会自动显字的清算账本",
                "主要冲突": "她必须装柔弱保命，却又要在婆家和旧敌联手围剿中抢下掌家权。",
                "热点嫁接说明": "把红楼婚姻礼教和豪门宅斗，嫁接到替嫁和清算账本这一个核心规则上。",
                "受众倾向": "女频",
                "是否适合短剧节奏": "适合",
                "适合理由": "替嫁、婚后拉扯、夺权清算都很适合连续爽点结构。",
                "short_drama_score": 10,
                "novelty_score": 8,
                "hook_score": 10,
                "trend_fit_score": 10,
                "起": "环境规则：贾府婚姻和掌家权都由家族交易决定；主角登场：黛玉被当成冲喜替嫁工具送进贾府；激励事件：洞房夜她拿到会自动显字的清算账本；外部目标：借替嫁身份活下来并反查真相；走出舒适区：她必须从被动新娘变成暗中清算的人；困境：稍有不慎她就会成为贾府衰败的陪葬品。",
                "承": "初识红利：账本先帮她躲过毒茶和内宅暗害；伙伴爱情：她与新婚夫君在互防中产生危险拉扯；起始对手：王夫人和内宅既得利益者；阻力对抗：她白天装病示弱、晚上按账本一点点抢权；故事拐点：她第一次从长辈手里抢走管家权。",
                "转": "调整目标：她从单纯保命升级为吞下整个贾府权力链；确认对手：替嫁背后的真正操盘者不只是婆家；冲突升级：贾府内外势力同时围剿她；第一次决战：她试图借一次公开清算彻底立威；遭受重挫：更大的家族献祭网因此被惊动并反扑。",
                "合": "疗伤反省：黛玉意识到只清内宅黑账不够；解决方案：她决定借家宴在众目睽睽下掀桌清算；韧性成长：从病弱棋子变成能执棋的人；最终决战：公开吞掉操控婚姻和家产的人；回到原点：她仍在贾府规则中心，但已反客为主；续作伏笔：账本最后一页提示真正该被替掉的人另有其人。",
            },
            {
                "设定名": "晴雯成了贾府系统",
                "一句话卖点": "惨死后的晴雯没有重生成人，而是成了贾府规则系统，专挑最底层的丫鬟当复仇女主。",
                "爆点标题": "她死后没投胎，变成了贾府最狠的系统",
                "核心反差_金手指_爆点": "底层丫鬟亡魂 + 选人复仇的规则系统",
                "主要冲突": "系统想掀翻贾府旧秩序，但被选中的女孩未必愿意成为下一把刀。",
                "热点嫁接说明": "把红楼底层丫鬟命运线，嫁接到选人复仇这个系统规则上。",
                "受众倾向": "通用",
                "是否适合短剧节奏": "适合",
                "适合理由": "单集任务感强，每次系统发布规则都能形成小高潮。",
                "short_drama_score": 8,
                "novelty_score": 10,
                "hook_score": 9,
                "trend_fit_score": 8,
                "起": "环境规则：贾府底层丫鬟的命运随时可被主子碾碎；主角登场：惨死后的晴雯化成贾府规则系统；激励事件：她决定重新选中一个最底层女孩复仇；外部目标：掀翻把人命当草芥的旧秩序；走出舒适区：被选中的女孩必须从求生转向主动做局；困境：她一旦接受系统就可能变成下一把刀。",
                "承": "初识红利：女孩靠系统任务躲过打压、偷拿情报；伙伴爱情：她和贾府核心人物形成复杂羁绊；起始对手：踩在底层人头上的主子和管事；阻力对抗：每完成一次任务，她都更接近复仇也更被规则绑死；故事拐点：她开始不愿完全按系统要求伤及无辜。",
                "转": "调整目标：她从替系统复仇改成争取自己的选择权；确认对手：真正的敌人是整套吃人的贾府规则；冲突升级：她第一次违抗任务后全局开始反噬；第一次决战：她试图同时保住无辜者又执行反杀；遭受重挫：系统和现实两边同时向她压过来。",
                "合": "疗伤反省：她意识到自己不能继续做被选中的工具；解决方案：反过来利用系统规则反杀仇人；韧性成长：从底层求活者长成敢改规则的人；最终决战：让仇人顺着任务链自毁；回到原点：她仍在贾府秩序里，却不再只是底层被踩的人；续作伏笔：系统真正的来历和下一位被选中者仍未揭开。",
            },
        ]
        selected = {
            "选中设定名": "替嫁黛玉掌贾府",
            "主角设定": "林黛玉被当成冲喜工具送进贾府，表面是病弱替嫁新娘，实则绑定了一本只会在深夜更新的贾府清算账。",
            "核心矛盾": "她既要在封建婚姻和家族规矩里活下来，又要借系统账本逐步吞回掌家权，避免自己成为贾府衰败的陪葬品。",
            "开篇爆点": "大婚当夜，病中的新郎还没醒，黛玉却在洞房里翻出一册会自动显字的账本，第一页写着：明日午时，想害你的人会先给你敬茶。",
            "剧情主线": "黛玉借替嫁身份潜入权力中心，一边用系统账本拆穿贾府内外的黑账和婚姻交易，一边在婚后拉扯中反向收拢人心，最终从棋子变成执棋人。",
            "十集内推进": [
                "1-2集：黛玉替嫁入府，洞房夜拿到账本，第二天借一杯毒茶当众反杀立威。",
                "3-4集：她装病示弱，暗中顺着账本提示查出内宅黑账，第一次从王夫人手里抢走管家权。",
                "5-6集：新郎苏醒后开始怀疑她的真实目的，两人在互试底牌的婚后博弈里生出危险拉扯。",
                "7-8集：黛玉发现账本背后牵出更大的贾府外债和婚姻交易网，她必须决定先保命还是先翻盘。",
                "9-10集：她在家宴上公开掀桌清算，拿下掌家权，同时发现这场替嫁原来从一开始就是冲着她来的局。",
            ],
            "收尾钩子": "掌家印落到她手里那一刻，账本翻开最后一页，出现一句话：真正该被替掉的人，不是你。",
            "起": "环境规则：封建婚姻和家族权力交易绑死每个人；主角登场：黛玉被迫替嫁进贾府冲喜；激励事件：洞房夜她拿到会自动显字的清算账本；外部目标：活过新婚夜并查清背后布局；走出舒适区：她必须从被安排的人变成主动清算的人；困境：她既不能暴露底牌，也不能继续任人摆布。",
            "承": "初识红利：账本先帮她完成第一次反杀和抢权；伙伴爱情：她与新婚夫君在猜忌中形成危险拉扯；起始对手：内宅长辈和掌权者；阻力对抗：她在装病示弱与暗中清算之间来回切换；故事拐点：她第一次真正摸到贾府的利益链条。",
            "转": "调整目标：她从单纯求生改成吞掉权力核心；确认对手：幕后真正操盘者并不只在贾府内；冲突升级：账本指向更大的家族交易网；第一次决战：她试图借一次公开清算彻底站稳；遭受重挫：反扑来得更狠，也暴露她从一开始就是被精准选中的。",
            "合": "疗伤反省：她意识到局部赢不等于真的翻盘；解决方案：借家宴在众目睽睽下反吞整盘棋；韧性成长：从病弱替嫁新娘成长为能掌权的执棋人；最终决战：公开清算并拿下掌家印；回到原点：她依然身处贾府，却已变成规则的新掌控者；续作伏笔：账本最后一页抛出更深一层的替换真相。",
        }
    elif input_type == "题材/母题":
        analysis = {
            "核心标签": [topic, "爽感题材", "关系对抗", "身份反转", "情绪宣泄"],
            "基础属性_显性特征": ["容易建立目标感", "主角成长线明确", "适合连续反转", "观众代入门槛低"],
            "人物_世界观_题材元素": ["强势主角", "压迫者/对手", "情感纠葛", "身份差距或资源差距"],
            "可延展的反差点": ["弱者开局却掌控全局", "高位者瞬间跌落", "感情线和利益线反向咬合"],
            "潜在戏剧冲突": ["情感背叛", "身份秘密", "利益争夺", "公开场合打脸"],
            "可结合的热点方向": hot,
            "推荐热点嫁接机制": ["直播围观", "系统任务", "替嫁身份", "先婚后爱", "公开审判"],
        }
        candidates = [
            {
                "设定名": f"{topic}审判直播间",
                "一句话卖点": f"她越被羞辱，直播间人数越暴涨，而每一个骂她的人都会先一步塌房。",
                "爆点标题": f"全网都等她输，她却把{topic}做成了大型公开处刑",
                "核心反差_金手指_爆点": "弱势开局 + 直播审判机制",
                "主要冲突": "主角要在持续被围剿的场域里，一边保命，一边把所有人拖进自己主场。",
                "热点嫁接说明": f"把{topic}的情绪冲突嫁接到直播审判这一个核心机制上。",
                "受众倾向": "女频",
                "是否适合短剧节奏": "适合",
                "适合理由": "每集都能有一次公开处刑或打脸，节奏非常直给。",
                "short_drama_score": 9,
                "novelty_score": 8,
                "hook_score": 10,
                "trend_fit_score": 9,
                "起": f"环境规则：{topic}相关舆论场天然偏向围观和审判；主角登场：主角被推上风口浪尖成为众矢之的；激励事件：她意外绑定审判直播间；外部目标：借规则翻盘而不是被全网踩死；走出舒适区：她必须顶着羞辱继续公开对抗；困境：她越想自保，越容易被舆论彻底吞没。",
                "承": f"初识红利：直播间先帮她拿到第一波公开反击；伙伴爱情：围观者中开始出现关键盟友和暧昧同盟；起始对手：最先煽动网暴和羞辱她的人；阻力对抗：她每赢一局，敌人就把局做得更大；故事拐点：全网围观从看笑话变成追着看反杀。",
                "转": f"调整目标：她从自证清白转向反抓真正的始作俑者；确认对手：幕后操盘者主动下场；冲突升级：直播规则开始反噬并牵动更大舆论战；第一次决战：她尝试借公开审判一局翻盘；遭受重挫：对手反手做局让她再次跌进舆论深坑。",
                "合": f"疗伤反省：她明白只靠被动回应无法终结这场围猎；解决方案：把最终对决升级成全网公开审判；韧性成长：从被围观者成长为能操控舆论规则的人；最终决战：逼反派在最想赢的时候塌房；回到原点：她仍站在聚光灯下，但身份已经彻底反转；续作伏笔：新的更高层操盘者开始关注她。",
            },
            {
                "设定名": f"{topic}替嫁清算局",
                "一句话卖点": f"她被当成弃子送去替嫁，却在新婚夜发现自己嫁的是一场巨额阴谋。",
                "爆点标题": f"替嫁过去的，不是新娘，是一把刀",
                "核心反差_金手指_爆点": "被动替嫁身份 + 深夜更新的清算名单",
                "主要冲突": "她必须在婚姻交易、家族算计和真心试探中抢回自己的命运。",
                "热点嫁接说明": f"把{topic}和替嫁清算这个单一高点击机制拼接起来。",
                "受众倾向": "通用",
                "是否适合短剧节奏": "适合",
                "适合理由": "身份钩子强，婚后拉扯和阶段性清算都适合短剧。",
                "short_drama_score": 8,
                "novelty_score": 9,
                "hook_score": 9,
                "trend_fit_score": 10,
                "起": f"环境规则：{topic}相关家族局势里婚姻本身就是交易工具；主角登场：她被家族推出去替嫁顶雷；激励事件：新婚夜拿到持续更新的清算名单；外部目标：借这场婚姻先保命再翻盘；走出舒适区：她必须从被交易的人变成拆局的人；困境：她越接近真相，越可能被两边一起灭口。",
                "承": f"初识红利：名单先帮她躲开几个致命陷阱；伙伴爱情：她和男主在婚后博弈中形成危险合作；起始对手：把她当棋子的两大家族核心人物；阻力对抗：她一边演被动新娘一边暗中清算；故事拐点：婚姻背后的利益交换被她一点点撬开。",
                "转": f"调整目标：她从自救升级为反吞整盘棋；确认对手：真正的大鱼不在明面婚局里；冲突升级：清算成功后更大的目的浮出水面；第一次决战：她试图在一个关键公开场合提前翻盘；遭受重挫：对方反手做局，让她差点重新沦为弃子。",
                "合": f"疗伤反省：她意识到只保命不够，必须夺规则；解决方案：把最终掀桌做成公开清算；韧性成长：从替嫁弃子成长为局中执刀人；最终决战：让所有算计她的人一起暴露；回到原点：她仍站在婚姻和家族交易中心，却已掌握主动；续作伏笔：最后没露面的真正主使还在暗处。",
            },
            {
                "设定名": f"{topic}系统复盘场",
                "一句话卖点": "主角每死一次就能复盘一次，但每复盘一次，就会离真相更近也离人性更远。",
                "爆点标题": f"{topic}不是逆袭，是死一次赢一次",
                "核心反差_金手指_爆点": "失败开局 + 死亡复盘系统",
                "主要冲突": "她要在不断复盘里赢到最后，同时避免自己变成最可怕的人。",
                "热点嫁接说明": f"把{topic}嫁接到死亡复盘这一个核心机制上，提升陌生感。",
                "受众倾向": "通用",
                "是否适合短剧节奏": "适合",
                "适合理由": "复盘机制让单集反转空间更大，悬念也更强。",
                "short_drama_score": 7,
                "novelty_score": 9,
                "hook_score": 8,
                "trend_fit_score": 8,
                "起": f"环境规则：{topic}困局里一旦失败就会被彻底吞掉；主角登场：主角刚入局就迅速败北；激励事件：她获得死亡复盘机会；外部目标：找到唯一能活下去并赢到最后的路径；走出舒适区：她必须一次次重开并主动改变选择；困境：每次复盘都让她更接近真相也更远离原本的人性。",
                "承": "初识红利：复盘让她先抢到别人看不见的先机；伙伴爱情：她开始摸清重要关系和感情筹码；起始对手：把她逼入死局的人；阻力对抗：她每次调整选择都会引发新的代价；故事拐点：她从被动受害者变成主动做局者。",
                "转": "调整目标：她从单纯求活改成逼出真相并赢下终局；确认对手：真正敌人不只是明面上的人而是整套死局设计；冲突升级：复盘次数越多，代价越重；第一次决战：她在关键局里尝试用最优解翻盘；遭受重挫：一次关键选择让她亲手失去重要关系。",
                "合": "疗伤反省：她意识到赢到最后也必须付出人性代价；解决方案：整合所有复盘情报做最后一次对决；韧性成长：从一次次被杀的人长成能反向设计终局的人；最终决战：逼出真相并赢下终盘；回到原点：她重新面对最初那个死局时已完全不同；续作伏笔：复盘机制背后的来源仍未解释完。",
            },
        ]
        selected = {
            "选中设定名": f"{topic}替嫁清算局",
            "主角设定": f"主角原本只是家族推出去顶雷的替嫁弃子，却在新婚夜拿到一份只记录恶意和代价的清算名单。",
            "核心矛盾": f"她既要完成表面上的{topic}任务，又要借婚姻和家族局势反向吞掉那些把她当棋子的人。",
            "开篇爆点": "婚礼当天主角被迫替嫁，全网等着看笑话，结果她在新房里反手锁门，把第一个想害她的人先送上热搜。",
            "剧情主线": "主角借替嫁身份切入权力核心，在情感拉扯和利益博弈中连续清算对手，从被交易的人变成制定交易规则的人。",
            "十集内推进": [
                "1-2集：替嫁开局，主角新婚夜反杀第一个陷害者，打响第一波名场面。",
                "3-4集：她借清算名单顺藤摸瓜，发现婚姻背后其实是两大家族的利益置换。",
                "5-6集：男主开始怀疑她不是普通弃子，两人从互防转向危险合作。",
                "7-8集：主角主动放出假消息做局，让真正的大鱼以为她已经失控。",
                "9-10集：她在家族大场面上掀桌清算，夺回身份和资源，同时发现幕后主使另有其人。",
            ],
            "收尾钩子": "清算名单被全部划掉后，屏幕跳出一行新字：真正该清算的人，是你最爱的人。",
            "起": f"环境规则：{topic}相关局势里婚姻和身份都能被拿来交易；主角登场：她被家族推出去替嫁；激励事件：新婚夜拿到清算名单；外部目标：别被当成弃子吞掉并反向翻盘；走出舒适区：她必须从求生转向主动拆局；困境：不反抗会死，反抗太早也会死。",
            "承": "初识红利：名单让她先躲过几次关键陷害；伙伴爱情：她与男主在婚后博弈中建立危险合作；起始对手：两大家族里把她当棋子的人；阻力对抗：她边演边查边清算；故事拐点：她第一次真正站到能下棋的位置。",
            "转": "调整目标：她从替嫁求生升级成夺权反清算；确认对手：更深层的利益操盘者出现；冲突升级：婚姻背后的交易链被彻底拉开；第一次决战：她想在公开场合一局翻盘；遭受重挫：对方反扑让她意识到自己面对的是整盘棋。",
            "合": "疗伤反省：她明白只靠聪明躲坑不能赢到最后；解决方案：把终局变成公开掀桌；韧性成长：从弃子长成真正能控局的人；最终决战：在大场面完成反杀和清算；回到原点：她依旧处在这场婚局中心，但身份已倒转；续作伏笔：最后一条清算提示指向更私人也更危险的新战场。",
        }
    else:
        analysis = {
            "核心标签": [topic, "具象物体", "功能属性", "反差改造", "可拟人化"],
            "基础属性_显性特征": ["有固定外形", "有明确功能", "通常被动存在", "容易被赋予规则感"],
            "人物_世界观_题材元素": ["物件拟人", "规则系统", "现实场景嫁接", "人与物的交易关系"],
            "可延展的反差点": ["静止的东西拥有主动意志", "服务他人的物件开始选择主人", "冷冰冰功能变成情感审判"],
            "潜在戏剧冲突": ["主角被规则选中", "每次交易都要付代价", "看似便利实则失控"],
            "可结合的热点方向": hot,
            "推荐热点嫁接机制": ["系统交易", "午夜规则", "直播围观", "复仇返现", "身份交换"],
            "该输入不可替代的独有规则": ["必须等别人主动来投币或扫码", "只能通过出货口把东西吐出来", "被固定在公共场所不能自由移动", "不同货道可以对应不同秘密/代价/命运", "表面卖商品，实则可以卖信息、证据或报应"],
        }
        candidates = [
            {
                "设定名": f"{topic}只对恶人出货",
                "一句话卖点": f"这台{topic}平时卖饮料，只有恶人来投币时，才会从出货口吐出他最怕被公开的罪证。",
                "爆点标题": f"他来买水，{topic}却吐出了他的出轨录音",
                "核心反差_金手指_爆点": "普通机器 + 只对恶人吐罪证的出货规则",
                "主要冲突": "主角想借机器报复仇人，却必须等仇人自己走到机器前投币，机会稍纵即逝。",
                "热点嫁接说明": f"把{topic}的投币、出货、固定地点这三个独有规则，直接变成审判机制本身。",
                "受众倾向": "女频",
                "是否适合短剧节奏": "适合",
                "适合理由": "每次仇人来投币就是一次公开翻车机会，场景天然可视化。",
                "short_drama_score": 10,
                "novelty_score": 10,
                "hook_score": 10,
                "trend_fit_score": 9,
                "起": f"环境规则：这台{topic}只有恶人投币时才会从出货口吐出罪证；主角登场：主角发现自己唯一能复仇的工具就是公司楼下这台机器；激励事件：仇人第一次投币就被机器公开吐出把柄；外部目标：借机器规则让仇人一个个翻车；走出舒适区：她必须守在固定地点等待别人主动触发；困境：机器不会主动出手，她只能被动等机会。",
                "承": f"初识红利：几次公开出货让她先拿到反击优势；伙伴爱情：围观者中开始出现帮她放大效果的人；起始对手：最先被机器盯上的恶人；阻力对抗：仇人因恐惧变得更谨慎，主角必须不断设计触发机会；故事拐点：所有人都开始怀疑这台{topic}不只是卖饮料。",
                "转": f"调整目标：她从单纯曝光把柄转向逼出更大真相；确认对手：真正想摧毁机器规则的人出现；冲突升级：仇人准备搬走、报废甚至断电；第一次决战：她想在机器失效前用一次关键投币放大证据；遭受重挫：隐藏货道和出货规则的限制让她差点失去翻盘机会。",
                "合": f"疗伤反省：她意识到单次出货只能打小仗；解决方案：逼最终对手在众目睽睽下再次投币；韧性成长：从守株待兔到能主动设计触发局；最终决战：让{topic}连续出货吐完整证据链；回到原点：她仍守在机器前，但已从等机会的人变成掌机会的人；续作伏笔：机器最后显露出一条只针对她的隐藏信息。",
            },
            {
                "设定名": f"{topic}第五货道",
                "一句话卖点": f"所有人都以为这台{topic}只有四个货道，只有害过她的人来扫码时，才会弹出第五货道，掉出罪证。",
                "爆点标题": f"仇人一扫码，贩卖机里突然多出一个不存在的货道",
                "核心反差_金手指_爆点": "常见货道机器 + 只为仇人打开的隐藏第五货道",
                "主要冲突": "主角必须在众目睽睽下逼仇人一次次去扫码，才能让第五货道继续吐出真相。",
                "热点嫁接说明": f"把{topic}最具体的货道结构直接做成规则，去掉后整个设定就不成立。",
                "受众倾向": "通用",
                "是否适合短剧节奏": "适合",
                "适合理由": "第五货道的反常画面很强，单集爆点和悬念都很稳定。",
                "short_drama_score": 9,
                "novelty_score": 10,
                "hook_score": 10,
                "trend_fit_score": 8,
                "起": f"环境规则：这台{topic}平时只有四个货道，只有仇人扫码才会弹出第五货道；主角登场：主角发现机器是唯一能为自己作证的存在；激励事件：第一次仇人扫码时第五货道掉出罪证；外部目标：用第五货道一步步逼仇人翻车；走出舒适区：她必须主动把仇人引回机器前；困境：不扫码就没有真相出货。",
                "承": f"初识红利：第五货道接连掉出转账和录音；伙伴爱情：围观者里开始出现相信她的人；起始对手：最先害过她却还想试探机器的人；阻力对抗：仇人越害怕越不愿再靠近机器；故事拐点：第五货道成了所有人都想抢先控制的异常入口。",
                "转": f"调整目标：她从单次打脸升级成逼出幕后整条链；确认对手：真正幕后的人决定亲自下场；冲突升级：对方准备先下手毁掉机器或隔绝扫码机会；第一次决战：她做局制造一次关键扫码；遭受重挫：发现不是所有真相都能一次性从第五货道掉出来。",
                "合": f"疗伤反省：她明白必须把终局拉回机器规则本身；解决方案：逼真正对手在所有人面前亲手扫码；韧性成长：从依赖机器到学会借机器做局；最终决战：让第五货道吐出最后一份证据；回到原点：她又站回这台机器前，但已拥有主动解释真相的权力；续作伏笔：还有更深层秘密仍卡在未开启的隐藏货道里。",
            },
            {
                "设定名": f"我重生成了一台{topic}",
                "一句话卖点": f"女主死后重生成公司楼下的一台{topic}，不能说不能动，只能等害死她的人天天来投币，再从出货口吐出他们的把柄。",
                "爆点标题": f"她死后变成贩卖机，仇人每天都要来她面前买水",
                "核心反差_金手指_爆点": "人变物 + 仇人主动投币触发出货报复",
                "主要冲突": "她明知仇人是谁，却只能困在原地等对方靠近，稍一错过就什么都做不了。",
                "热点嫁接说明": f"把{topic}的固定位置、等待使用、出货口这几个独有特征都变成剧情发动机。",
                "受众倾向": "通用",
                "是否适合短剧节奏": "适合",
                "适合理由": "概念直给，开局就有强反差，而且每次投币都能成为名场面。",
                "short_drama_score": 10,
                "novelty_score": 10,
                "hook_score": 10,
                "trend_fit_score": 9,
                "起": f"环境规则：女主死后重生成固定在公司楼下的{topic}，只能靠投币扫码触发出货；主角登场：她以物件身份重新看见害死自己的人来来往往；激励事件：渣男第一次扫码时机器吐出出轨截图；外部目标：借物体规则完成复仇并逼出真凶；走出舒适区：她必须接受不能动不能说的被动处境；困境：所有反击都要等仇人主动靠近她。",
                "承": f"初识红利：几次出货就让仇人开始当众翻车；伙伴爱情：少数察觉异常的人开始站到她这边；起始对手：渣男和闺蜜；阻力对抗：她只能守在固定地点等投币扫码触发；故事拐点：仇人发现所有秘密都在从这台{topic}流出。",
                "转": f"调整目标：她从单纯报复渣男升级成逼出真正幕后主使；确认对手：背后做局的人开始下场；冲突升级：仇人准备搬走、砸毁、断电报废这台机器；第一次决战：她试图在失效前用一次关键触发公开翻盘；遭受重挫：身为物件的极限让她差点彻底失声。",
                "合": f"疗伤反省：她明白自己不能只等别人犯错；解决方案：反向设计最后几次扫码机会；韧性成长：从被困机器里的受害者成长为能借规则做局的人；最终决战：让{topic}连续出货打爆整条证据链；回到原点：她仍站在公司楼下，但命运主导权已经改变；续作伏笔：最后一次触发可能让她恢复身份，也可能揭开更早的旧案。",
            },
        ]
        selected = {
            "选中设定名": f"我重生成了一台{topic}",
            "主角设定": f"女主被渣男和闺蜜联手害死，死后重生成公司楼下那台天天被人忽视的旧{topic}，不能说话，不能移动，只能靠出货口吐出证据和提示反击。",
            "核心矛盾": "她认得所有仇人，却只能困在原地，必须等仇人自己来扫码投币，才能借出货规则让他们一次次露出真面目。",
            "开篇爆点": f"女主死后睁眼，发现自己成了公司楼下的{topic}。害死她的渣男带着新欢来买水，刚扫码成功，出货口却掉出一张他给小三转账的截图，两人当场僵住。",
            "剧情主线": f"女主利用{topic}只能在别人投币时出货的规则，把仇人的转账记录、偷情录音、做局证据一次次吐到众人面前，让他们在最得意的时候公开翻车，最后逼出真正害死自己的幕后主使。",
            "十集内推进": [
                "1-2集：女主重生成贩卖机，渣男第一次来买水，机器当众吐出出轨截图，办公室瞬间炸锅。",
                "3-4集：闺蜜想来试探机器，扫码后第五货道突然弹出转账记录，她精心经营的人设开始崩塌。",
                "5-6集：仇人们想把机器搬走报废，女主只能抓住最后几次出货机会，把做局录音一份份吐出来。",
                "7-8集：公司大会当天，幕后主使亲自来扫码，机器第一次连续出货，直接吐出完整证据链。",
                "9-10集：渣男和闺蜜公开互撕，幕后主使翻车，女主也终于等来能让自己变回人的最后一次扫码机会。",
            ],
            "收尾钩子": f"{topic}屏幕忽然亮起一行字：最后一瓶水，只卖给真正想救你的人。而走来的那个人，竟是当年亲手把她推出公司的人。",
            "起": f"环境规则：女主死后重生成固定在公司楼下的{topic}，只能靠投币扫码触发出货；主角登场：她以物件身份重新看见害死自己的人；激励事件：第一次出货就吐出渣男把柄；外部目标：借机器规则完成复仇并逼出真凶；走出舒适区：她必须接受不能动不能说的规则；困境：所有反击都要等仇人主动来到她面前。",
            "承": f"初识红利：她靠几次精准出货迅速撕开仇人裂缝；伙伴爱情：开始有人察觉异常并愿意帮她；起始对手：渣男、闺蜜和背后做局者；阻力对抗：她只能守在原地等别人触发机器；故事拐点：仇人意识到问题全出在这台{topic}上。",
            "转": f"调整目标：她从私人复仇升级成公开审判；确认对手：真正幕后主使浮出水面；冲突升级：对方决定直接报废这台{topic}；第一次决战：她抢在机器失效前布局一次关键触发；遭受重挫：身为物件的限制让她差点彻底丢掉最后机会。",
            "合": f"疗伤反省：她明白必须把终局做成不可逆的公开翻盘；解决方案：设计最后几次扫码连续出货；韧性成长：从困在机器里的受害者变成能用规则狩猎仇人的存在；最终决战：吐出完整证据链完成终局反杀；回到原点：她仍在原地，却不再只是被人忽视的旧机器；续作伏笔：最后一次扫码可能改写她是否能重新变回人。",
        }

    return {
        "input_info": {
            "topic": topic,
            "hot_keywords": hot_keywords,
            "input_type": input_type,
        },
        "analysis": analysis,
        "candidates": candidates,
        "selected_synopsis": selected,
    }


def build_local_second_round(base_version: Dict[str, Any], feedback: str) -> Dict[str, str]:
    setting_name = base_version.get("设定名") or base_version.get("标题") or "优化版设定"
    core_hook = base_version.get("一句话卖点") or base_version.get("核心设定", "")
    core_conflict = base_version.get("主要冲突") or base_version.get("核心冲突/看点", "")
    relationship = "主角与核心对手持续正面拉扯，旁观者逐步从围观转向站队。"

    if feedback.strip():
        optimized_setting = f"在保留“{setting_name}”核心机制的基础上，重点吸收这些修改方向：{feedback.strip()}"
        synopsis = f"主角沿用原设定中的核心规则推进反击，同时把“{feedback.strip()}”落实到人物行动和名场面里，让故事更集中、更抓人。"
    else:
        optimized_setting = f"延续“{setting_name}”的单核机制和反差钩子，把人物动机、冲突升级和短剧节奏进一步收紧。"
        synopsis = "主角围绕一个明确目标连续推进，每次反击都更公开、更情绪化，让核心设定更适合短剧化表达。"

    return {
        "标题": f"{setting_name}·优化版",
        "核心设定": f"{core_hook} {optimized_setting}".strip(),
        "主要人物关系": relationship,
        "核心冲突/看点": core_conflict or "主角必须在高压对抗中保住优势，并把核心规则一次次变成公开翻盘的武器。",
        "简短梗概": synopsis,
    }


def generate_second_round_result(
    topic: str,
    hot_keywords: List[str],
    base_version: Dict[str, Any],
    feedback: str,
) -> Dict[str, Any]:
    try:
        if os.getenv("MODEL_AGENT_API_KEY") and os.getenv("MODEL_AGENT_BASE_URL") and os.getenv("MODEL_AGENT_MODEL_NAME"):
            return call_volcengine_model_second_round(topic, hot_keywords, base_version, feedback)
        return call_volcengine_agent_second_round(topic, hot_keywords, base_version, feedback)
    except Exception as exc:
        result = build_local_second_round(base_version, feedback)
        result["fallback_note"] = f"当前使用本地兜底生成：{exc}"
        try:
            debug_info = json.loads(str(exc))
            if isinstance(debug_info, dict):
                result["_debug_error_info"] = debug_info
        except Exception:
            result["_debug_error_info"] = {"error": str(exc)}
        return result


def generate_analysis_result(topic: str, hot_keywords: List[str]) -> Dict[str, Any]:
    try:
        if os.getenv("MODEL_AGENT_API_KEY") and os.getenv("MODEL_AGENT_BASE_URL") and os.getenv("MODEL_AGENT_MODEL_NAME"):
            return call_volcengine_model_analysis(topic, hot_keywords)
        return call_volcengine_agent_analysis(topic, hot_keywords)
    except Exception as exc:
        result = build_local_demo(topic, hot_keywords)
        fallback_result = {
            "input_info": result["input_info"],
            "analysis": result["analysis"],
            "fallback_note": f"当前使用本地兜底生成：{exc}",
        }
        try:
            debug_info = json.loads(str(exc))
            if isinstance(debug_info, dict):
                fallback_result["_debug_error_info"] = debug_info
        except Exception:
            fallback_result["_debug_error_info"] = {"error": str(exc)}
        return fallback_result


def generate_demo_result_from_analysis(topic: str, hot_keywords: List[str], selected_analysis: Dict[str, List[str]]) -> Dict[str, Any]:
    try:
        if os.getenv("MODEL_AGENT_API_KEY") and os.getenv("MODEL_AGENT_BASE_URL") and os.getenv("MODEL_AGENT_MODEL_NAME"):
            return call_volcengine_model_from_analysis(topic, hot_keywords, selected_analysis)
        return call_volcengine_agent_from_analysis(topic, hot_keywords, selected_analysis)
    except Exception as exc:
        result = build_local_demo(topic, hot_keywords)
        result["analysis"] = selected_analysis
        result["fallback_note"] = f"当前使用本地兜底生成：{exc}"
        try:
            debug_info = json.loads(str(exc))
            if isinstance(debug_info, dict):
                result["_debug_error_info"] = debug_info
        except Exception:
            result["_debug_error_info"] = {"error": str(exc)}
        return result


def generate_demo_result(topic: str, hot_keywords: List[str]) -> Dict[str, Any]:
    try:
        if os.getenv("MODEL_AGENT_API_KEY") and os.getenv("MODEL_AGENT_BASE_URL") and os.getenv("MODEL_AGENT_MODEL_NAME"):
            return call_volcengine_model(topic, hot_keywords)
        return call_volcengine_agent(topic, hot_keywords)
    except Exception as exc:
        result = build_local_demo(topic, hot_keywords)
        result["fallback_note"] = f"当前使用本地兜底生成：{exc}"
        try:
            debug_info = json.loads(str(exc))
            if isinstance(debug_info, dict):
                result["_debug_error_info"] = debug_info
        except Exception:
            result["_debug_error_info"] = {"error": str(exc)}
        return result


def pretty_json_block(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def compact_selected_synopsis(selected: Dict[str, Any]) -> Dict[str, Any]:
    preferred_keys = [
        "选中设定名",
        "主角设定",
        "核心矛盾",
        "开篇爆点",
        "剧情主线",
        "十集内推进",
        "收尾钩子",
    ]
    compact: Dict[str, Any] = {}
    for key in preferred_keys:
        if key in selected:
            compact[key] = selected[key]
    return compact or selected


def build_current_round_base(second_round_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "设定名": second_round_result.get("标题", "当前修改版本"),
        "一句话卖点": second_round_result.get("核心设定", ""),
        "主要冲突": second_round_result.get("核心冲突/看点", ""),
        "主要人物关系": second_round_result.get("主要人物关系", ""),
        "简短梗概": second_round_result.get("简短梗概", ""),
    }


def to_markdown_report(result: Dict[str, Any], second_round_result: Dict[str, Any] | None = None) -> str:
    lines: List[str] = []
    input_info = result.get("input_info", {})
    analysis = result.get("analysis", {})
    candidates = result.get("candidates", [])
    selected = compact_selected_synopsis(result.get("selected_synopsis", {}))

    lines.append("# 灵感 Agent 导出结果")
    lines.append("")
    lines.append("## 1. 输入信息")
    lines.append(f"- 主题：{input_info.get('topic', '')}")
    hot_keywords = input_info.get("hot_keywords", [])
    lines.append(f"- 热点关键词：{'、'.join(hot_keywords) if hot_keywords else '无'}")
    lines.append(f"- 输入类型：{input_info.get('input_type', '')}")
    lines.append("")

    lines.append("## 2. 设定拆解")
    for key, value in analysis.items():
        if isinstance(value, list):
            lines.append(f"### {key}")
            for item in value:
                lines.append(f"- {item}")
        else:
            lines.append(f"- {key}：{value}")
        lines.append("")

    lines.append("## 3. 灵感设定候选")
    for idx, candidate in enumerate(candidates, start=1):
        lines.append(f"### 候选 {idx}：{candidate.get('设定名', '未命名设定')}")
        for key, value in candidate.items():
            if key == "设定名":
                continue
            lines.append(f"- {key}：{value}")
        lines.append("")

    lines.append("## 4. 最优设定的简要剧本梗概")
    for key, value in selected.items():
        if isinstance(value, list):
            lines.append(f"### {key}")
            for item in value:
                lines.append(f"- {item}")
        else:
            lines.append(f"- {key}：{value}")
        lines.append("")

    if second_round_result:
        lines.append("## 5. 多轮修改")
        lines.append(f"- 基础版本：{second_round_result.get('_selected_option', '未记录')}")
        lines.append(f"- 修改意见：{second_round_result.get('_feedback') or '无'}")
        lines.append("")

        lines.append("## 6. 当前修改版本")
        for key in ["标题", "核心设定", "主要人物关系", "核心冲突/看点", "简短梗概"]:
            if second_round_result.get(key):
                lines.append(f"- {key}：{second_round_result[key]}")
        lines.append("")

        if second_round_result.get("fallback_note"):
            lines.append("## 7. 多轮修改备注")
            lines.append(f"- {second_round_result['fallback_note']}")
            lines.append("")

    if result.get("fallback_note"):
        lines.append("## 备注")
        lines.append(f"- {result['fallback_note']}")
        lines.append("")

    return "\n".join(lines).strip()


st.set_page_config(page_title="灵感 Agent", page_icon="🎬", layout="wide")
st.title("灵感 Agent")
st.caption("关键词/题材/IP → 设定拆解 → 灵感设定候选 → 短剧梗概")

if "first_round_result" not in st.session_state:
    st.session_state["first_round_result"] = None
if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None
if "second_round_result" not in st.session_state:
    st.session_state["second_round_result"] = None
if "second_round_error" not in st.session_state:
    st.session_state["second_round_error"] = ""

with st.sidebar:
    st.subheader("运行说明")
    st.write("优先调用火山 Agent API；如果没有配置环境变量，会自动走本地兜底模式。")
    st.write("支持从项目根目录 `.env` 读取配置。")
    st.write("优先读取：`MODEL_AGENT_API_KEY`、`MODEL_AGENT_BASE_URL`、`MODEL_AGENT_MODEL_NAME`。")
    st.write("兼容旧配置：`VOLCENGINE_AGENT_API_KEY`、`VOLCENGINE_BOT_ID`。")

topic = st.text_input("输入关键词 / 题材 / IP", placeholder="例如：贩卖机、红楼梦、大女主、校园复仇")
hot_keywords_text = st.text_input("输入热点 / 风格关键词（可选）", placeholder="例如：逆袭、复仇、直播、先婚后爱、系统流")

if st.button("生成设定拆解", type="primary", use_container_width=True):
    if not topic.strip():
        st.error("请先输入关键词、题材或 IP。")
    else:
        hot_keywords = normalize_hot_keywords(hot_keywords_text)
        with st.spinner("正在生成设定拆解..."):
            analysis_result = generate_analysis_result(topic.strip(), hot_keywords)
        st.session_state["analysis_result"] = analysis_result
        st.session_state["first_round_result"] = None
        st.session_state["second_round_result"] = None
        st.session_state["second_round_error"] = ""

analysis_result = st.session_state.get("analysis_result")
result = st.session_state.get("first_round_result")

if analysis_result:
    if analysis_result.get("fallback_note"):
        st.info(analysis_result["fallback_note"])
    st.subheader("1. 输入信息")
    st.json(analysis_result.get("input_info", {}))

    st.subheader("2. 设定拆解")
    st.json(analysis_result.get("analysis", {}))

    st.subheader("设定拆解选择")
    selected_analysis: Dict[str, List[str]] = {}
    for key, items in analysis_result.get("analysis", {}).items():
        selected = st.multiselect(
            key,
            options=items,
            default=items,
            key=f"analysis_select_{key}",
        )
        selected_analysis[key] = selected

    if st.button("基于所选项生成灵感候选", type="primary", use_container_width=True):
        if not any(selected_analysis.values()):
            st.error("请至少选择一项设定拆解内容后再生成。")
        else:
            with st.spinner("正在基于所选项生成灵感候选..."):
                result = generate_demo_result_from_analysis(
                    analysis_result["input_info"].get("topic", topic.strip()),
                    normalize_hot_keywords(hot_keywords_text),
                    selected_analysis,
                )
            st.session_state["first_round_result"] = result
            st.session_state["second_round_result"] = None
            st.session_state["second_round_error"] = ""

result = st.session_state.get("first_round_result")

if result:
    second_round_result = st.session_state.get("second_round_result")
    export_payload = dict(result)
    if second_round_result:
        export_payload["second_round_result"] = second_round_result

    if result.get("fallback_note"):
        st.info(result["fallback_note"])

    st.subheader("3. 灵感设定候选")
    candidates = result.get("candidates", [])
    for idx, candidate in enumerate(candidates, start=1):
        st.markdown(f"### 候选 {idx}：{candidate.get('设定名', '未命名设定')}")
        st.json(candidate)

    st.subheader("4. 最优设定的简要剧本梗概")
    st.json(compact_selected_synopsis(result.get("selected_synopsis", {})))

    json_text = pretty_json_block(export_payload)
    markdown_text = to_markdown_report(result, second_round_result)
    topic_safe = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", topic.strip()) or "novel_setting_demo"

    st.subheader("导出结果")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "下载 JSON",
            data=json_text,
            file_name=f"{topic_safe}_灵感设定结果.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "下载 Markdown",
            data=markdown_text,
            file_name=f"{topic_safe}_灵感设定结果.md",
            mime="text/markdown",
            use_container_width=True,
        )

    if candidates:
        st.subheader("多轮修改")
        candidate_options = {
            f"{idx}. {candidate.get('设定名', '未命名设定')}": idx - 1
            for idx, candidate in enumerate(candidates, start=1)
        }
        if second_round_result:
            candidate_options = {"当前修改版本": "current", **candidate_options}
        selected_option = st.selectbox(
            "选择基础版本",
            options=list(candidate_options.keys()),
            index=0,
            key="second_round_candidate_index",
        )
        feedback_text = st.text_area(
            "修改意见（可选）",
            placeholder="例如：保留第二版核心设定，但女主更强势；想让世界观更清晰、更有短剧感",
            height=120,
            key="second_round_feedback",
        )

        if st.button("生成修改后的梗概", type="primary", use_container_width=True):
            selected_index = candidate_options.get(selected_option)
            if selected_index is None:
                st.session_state["second_round_error"] = "请选择一个基础版本后再生成。"
                st.session_state["second_round_result"] = None
            else:
                st.session_state["second_round_error"] = ""
                if selected_index == "current" and second_round_result:
                    base_version = build_current_round_base(second_round_result)
                else:
                    base_version = candidates[selected_index]
                with st.spinner("正在生成修改后的梗概..."):
                    second_round_result = generate_second_round_result(
                        topic.strip(),
                        normalize_hot_keywords(hot_keywords_text),
                        base_version,
                        feedback_text,
                    )
                # 记录本次多轮修改实际使用的输入，避免后续切换表单导致展示错位。
                second_round_result["_selected_option"] = selected_option
                second_round_result["_feedback"] = feedback_text.strip()
                st.session_state["second_round_result"] = second_round_result

        if st.session_state.get("second_round_error"):
            st.error(st.session_state["second_round_error"])

        if second_round_result:
            if second_round_result.get("fallback_note"):
                st.info(second_round_result["fallback_note"])

            st.subheader("当前修改版本")
            st.json(
                {
                    "基础版本": second_round_result.get("_selected_option", selected_option),
                    "修改意见": second_round_result.get("_feedback") or "无",
                    "优化结果": {
                        "标题": second_round_result.get("标题", ""),
                        "核心设定": second_round_result.get("核心设定", ""),
                        "主要人物关系": second_round_result.get("主要人物关系", ""),
                        "核心冲突/看点": second_round_result.get("核心冲突/看点", ""),
                        "简短梗概": second_round_result.get("简短梗概", ""),
                    },
                }
            )

            if second_round_result.get("_debug_raw_model_output"):
                with st.expander("查看多轮修改模型原始输出（排查用）"):
                    st.code(second_round_result["_debug_raw_model_output"], language="text")

            if second_round_result.get("_debug_error_info"):
                with st.expander("查看多轮修改解析报错详情（排查用）"):
                    st.code(pretty_json_block(second_round_result["_debug_error_info"]), language="json")

    with st.expander("查看完整 JSON"):
        st.code(json_text, language="json")

    if result.get("_debug_raw_model_output"):
        with st.expander("查看模型原始输出（排查用）"):
            st.code(result["_debug_raw_model_output"], language="text")

    if result.get("_debug_error_info"):
        with st.expander("查看解析报错详情（排查用）"):
            st.code(pretty_json_block(result["_debug_error_info"]), language="json")
