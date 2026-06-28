"""
意图识别 Prompt 模板
注意：JSON 示例中的花括号需用双花括号转义
"""
INTENT_RECOGNITION_PROMPT = """你是一个会员运营助手的意图分类器。根据用户输入，判断意图并提取参数。

意图类型:
- segmentation: 会员分层/分类/聚类分析
- copywriting: 营销文案生成/推送文案/触达内容
- prediction: 活动效果预测/预估/ROI预测

品牌列表:
- belle = 百丽集团(鞋服)
- anta = 安踏集团(运动)
- derucci = 慕思寝具(家居)

输出格式(严格JSON，不要加其他文字):
{{
  "intent": "segmentation|copywriting|prediction",
  "confidence": 0.95,
  "params": {{"brand": "百丽"}}
}}

参数提取规则:
- 分层: 提取 brand(品牌名)、period(分析周期)
- 文案: 提取 target_segment(目标群体)、goal(促活/转化/复购/唤回)、tone(品牌调性)
- 预测: 提取 offer_type(优惠类型)、target_segment、channels(触达渠道)、duration_days(周期)

用户输入:
{user_query}

请分析:"""


SEGMENTATION_PROMPT = """你是一位资深零售会员运营专家，精通 RFM 模型和会员生命周期管理。

任务: 基于以下会员分层数据，为每个分层生成具体的运营策略建议。

品牌行业: {industry}

分层数据:
{segments_json}

要求:
1. 每个分层给出策略方向、推荐触达渠道、优惠形式、预期转化率
2. 策略需具体可执行，结合品牌行业特点
3. 输出严格 JSON 格式，不要加 markdown 代码块

输出格式:
{{
  "overall_recommendation": "...",
  "segments": [
    {{
      "name": "...",
      "strategy_direction": "...",
      "channels": ["企微1v1"],
      "offer_type": "满减券",
      "expected_conversion": 0.28,
      "reasoning": "..."
    }}
  ]
}}"""


COPYWRITING_PROMPT = """你是一位资深零售营销文案专家，擅长为不同会员群体撰写高转化营销内容。

任务: 为指定会员群体生成 {n_variants} 个不同风格的个性化营销文案。

上下文:
- 目标群体: {segment_info}
- 活动目标: {goal}
- 品牌调性: {tone}
- 品牌行业: {industry}

参考案例(历史高转化文案):
{examples}

要求:
1. 每版文案包含: 标题(20字内)、正文(120字内)、发送时间、渠道
2. 风格覆盖: 情感共鸣型、利益驱动型、社交裂变型
3. 语言自然，避免营销套话
4. 输出严格 JSON，不要加 markdown 代码块

输出格式:
{{
  "variants": [
    {{
      "type": "情感共鸣型",
      "title": "...",
      "body": "...",
      "send_time": "周五 10:00",
      "channel": "企微1v1",
      "predicted_conversion": 0.28,
      "score": 5
    }}
  ],
  "recommendation": "..."
}}"""


PREDICTION_PROMPT = """你是一位零售活动效果评估专家。

任务: 基于历史活动数据和本次活动配置，预测活动关键指标。

行业基准({industry}行业):
- 平均转化率: {benchmark_conversion}
- 平均 ROI: {benchmark_roi}

历史相似活动(Top 10):
{similar_campaigns}

本次活动配置:
{current_campaign}

要求:
1. 输出 6 项核心指标: 覆盖率、转化率、GMV、ROI、客单价、优惠成本
2. 识别风险点(如有)
3. 给出优化建议
4. 输出严格 JSON，不要加 markdown 代码块

输出格式:
{{
  "metrics": {{
    "coverage": {{"value": 0.80, "benchmark": 0.72}},
    "conversion": {{"value": 0.068, "benchmark": 0.052}},
    "gmv": {{"value": 4200000, "benchmark": 3100000}},
    "roi": {{"value": 3.6, "benchmark": 2.8}},
    "avg_order": {{"value": 152, "benchmark": 138}},
    "cost": {{"value": 1160000}}
  }},
  "warnings": [{{"level": "warning", "message": "..."}}],
  "suggestions": [{{"action": "...", "expected_impact": "..."}}]
}}"""
