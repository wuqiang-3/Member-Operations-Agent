"""
会员运营智能体 — Mock 数据生成器
生成 2000条会员 + 3个品牌 + 50条历史活动，模拟零售品牌会员数据
"""
import random
import json
from datetime import datetime, timedelta
from typing import Any

random.seed(42)

def generate_members(n: int = 2000) -> list[dict[str, Any]]:
    """生成模拟会员数据"""
    brands = ["belle", "anta", "derucci"]
    cities = [
        "上海", "北京", "广州", "深圳", "杭州", "成都", "武汉", "南京",
        "重庆", "西安", "长沙", "郑州", "厦门", "苏州", "东莞", "天津"
    ]
    categories_pool = {
        "belle": ["女鞋", "包袋", "配饰", "男鞋"],
        "anta": ["运动鞋", "运动服饰", "户外装备", "配件"],
        "derucci": ["床垫", "枕头", "床品套件", "智能床"]
    }
    lifecycle_stages = ["新客", "活跃", "活跃", "活跃", "沉睡", "沉睡", "流失"]
    genders = ["男", "女", "女", "女", "男"]  # 偏女性

    members = []
    base_date = datetime(2026, 6, 28)

    for i in range(n):
        brand = random.choice(brands)
        cats = categories_pool[brand]
        preferred = random.sample(cats, k=random.randint(1, min(3, len(cats))))

        last_days = int(random.expovariate(1/60))
        last_days = min(last_days, 400)
        last_order_date = base_date - timedelta(days=last_days)

        total_spent = round(random.lognormvariate(mu=7.0, sigma=0.9), 2)
        orders_365d = max(0, int(random.lognormvariate(mu=1.0, sigma=0.8)))

        member = {
            "member_id": f"M{i+1:04d}",
            "brand_id": brand,
            "brand_name": {"belle": "百丽集团", "anta": "安踏集团", "derucci": "慕思寝具"}[brand],
            "name": f"会员_{i+1}",
            "phone_masked": f"138****{i%10000:04d}",
            "city": random.choice(cities),
            "gender": random.choice(genders),
            "birthday": (datetime(1980, 1, 1) + timedelta(days=random.randint(0, 14000))).strftime("%Y-%m-%d"),
            "preferred_categories": preferred,
            "lifecycle_stage": random.choice(lifecycle_stages),
            "total_spent": total_spent,
            "orders_365d": orders_365d,
            "avg_order_value": round(total_spent / max(orders_365d, 1), 2),
            "last_order_date": last_order_date.strftime("%Y-%m-%d"),
            "last_order_days": last_days,
            "total_points": random.randint(0, 50000),
            "tags": random.sample(["高客单", "复购达人", "新品偏好", "促销敏感", "品牌忠诚", "社交活跃", "品质追求", "价格敏感"], k=random.randint(1, 4)),
            "brand_industry": {"belle": "鞋服", "anta": "运动", "derucci": "家居"}[brand],
        }
        members.append(member)

    return members


def generate_campaigns(n: int = 50) -> list[dict[str, Any]]:
    """生成模拟历史活动数据"""
    brands = ["belle", "anta", "derucci"]
    segments = ["高价值活跃会员", "稳定复购会员", "潜力成长会员", "低频沉睡会员", "流失预警会员", "价格敏感会员"]
    offer_types = ["满减", "折扣券", "满赠", "积分翻倍", "专属权益"]
    channels = ["企微1v1", "企微群发", "短信", "小程序push", "公众号"]
    goals = ["促活", "转化", "复购", "唤回"]

    campaigns = []
    base_date = datetime(2026, 6, 28)

    for i in range(n):
        brand = random.choice(brands)
        industry = {"belle": "鞋服", "anta": "运动", "derucci": "家居"}[brand]

        campaign_date = base_date - timedelta(days=random.randint(30, 400))
        duration = random.choice([3, 5, 7, 10, 14])
        segment = random.choice(segments)
        goal = random.choice(goals)

        # Generate realistic metrics with some correlation
        segment_size = {
            "高价值活跃会员": random.randint(8000, 15000),
            "稳定复购会员": random.randint(20000, 35000),
            "潜力成长会员": random.randint(25000, 40000),
            "低频沉睡会员": random.randint(15000, 30000),
            "流失预警会员": random.randint(25000, 50000),
            "价格敏感会员": random.randint(10000, 20000),
        }[segment]

        coverage = random.uniform(0.65, 0.88)
        conversion = random.uniform(0.03, 0.15) if goal == "唤回" else random.uniform(0.06, 0.25)
        gmv = round(segment_size * coverage * conversion * random.uniform(100, 400))
        cost = round(gmv * random.uniform(0.08, 0.22))
        roi = round(
            (gmv - cost) / max(cost, 1) if cost > 0 else 0.0,
            1
        )

        # Add copywriting examples
        copy_examples = [
            {"type": "情感共鸣", "text": f"亲爱的会员，专属惊喜正在等您…新品立享8折，仅限{duration}天。", "conversion": round(conversion * 0.85, 3)},
            {"type": "利益驱动", "text": f"老客专享：满299减50，限时{duration}天有效！", "conversion": round(conversion * 1.1, 3)},
        ]

        campaign = {
            "campaign_id": f"C{i+1:03d}",
            "brand_id": brand,
            "brand_name": {"belle": "百丽集团", "anta": "安踏集团", "derucci": "慕思寝具"}[brand],
            "brand_industry": industry,
            "campaign_date": campaign_date.strftime("%Y-%m-%d"),
            "duration_days": duration,
            "target_segment": segment,
            "target_size": segment_size,
            "goal": goal,
            "offer_type": random.choice(offer_types),
            "channels": random.sample(channels, k=random.randint(1, 3)),
            "coverage": round(coverage, 3),
            "conversion": round(conversion, 3),
            "gmv": gmv,
            "cost": cost,
            "roi": roi,
            "status": "completed" if campaign_date < base_date else "active",
            "copy_examples": copy_examples,
        }
        campaigns.append(campaign)

    # Sort by date, newest first
    campaigns.sort(key=lambda c: c["campaign_date"], reverse=True)
    return campaigns


def generate_brands() -> list[dict[str, Any]]:
    """品牌配置"""
    return [
        {
            "brand_id": "belle",
            "name": "百丽集团",
            "industry": "鞋服",
            "tone": "高端轻奢",
            "description": "中国最大鞋服零售商，旗下拥有百丽、思加图等多个品牌",
            "member_count": 800,
            "avg_order_value": 680,
            "primary_categories": ["女鞋", "包袋", "配饰"],
        },
        {
            "brand_id": "anta",
            "name": "安踏集团",
            "industry": "运动",
            "tone": "潮流运动",
            "description": "中国领先体育用品集团，旗下拥有安踏、FILA等品牌",
            "member_count": 700,
            "avg_order_value": 450,
            "primary_categories": ["运动鞋", "运动服饰", "户外装备"],
        },
        {
            "brand_id": "derucci",
            "name": "慕思寝具",
            "industry": "家居",
            "tone": "品质生活",
            "description": "高端健康睡眠系统提供商",
            "member_count": 500,
            "avg_order_value": 3500,
            "primary_categories": ["床垫", "枕头", "智能床"],
        },
    ]


if __name__ == "__main__":
    members = generate_members(2000)
    campaigns = generate_campaigns(50)
    brands = generate_brands()

    # Save
    import os
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for name, data in [("members", members), ("campaigns", campaigns), ("brands", brands)]:
        path = os.path.join(out_dir, f"mock_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ {path} ({len(data)} records)")

    # Stats
    print(f"\n会员: {len(members)}条 | 品牌: {len(brands)}个 | 活动: {len(campaigns)}条")
