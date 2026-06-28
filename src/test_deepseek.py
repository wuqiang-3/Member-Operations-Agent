"""
DeepSeek API 连通性验证
用法：python src/test_deepseek.py
需要先配置 .env 文件中的 DEEPSEEK_API_KEY
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

if not api_key or api_key == "your-api-key-here":
    print("❌ 请先配置 .env 文件中的 DEEPSEEK_API_KEY")
    print("   cp .env.example .env")
    print("   编辑 .env 填入你的 API Key")
    sys.exit(1)

from openai import OpenAI

client = OpenAI(api_key=api_key, base_url=base_url)


def test_simple():
    """简单调用测试"""
    print(f"🔗 连接 {base_url}，模型 {model}...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个会员运营助手。"},
            {"role": "user", "content": "用一句话介绍会员分层模型"},
        ],
        max_tokens=100,
        temperature=0.7,
    )

    content = response.choices[0].message.content
    tokens = response.usage.total_tokens if response.usage else 0
    print(f"✅ 调用成功！响应：{content[:80]}...")
    print(f"   Token 用量：{tokens}")
    return True


def test_stream():
    """流式调用测试"""
    print(f"\n🔗 流式调用测试...")

    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "列举3个会员运营的核心指标"},
        ],
        max_tokens=150,
        stream=True,
    )

    chars = 0
    for chunk in stream:
        if chunk.choices[0].delta.content:
            chars += len(chunk.choices[0].delta.content)

    print(f"✅ 流式调用成功！接收 {chars} 字符")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("  DeepSeek API 连通性验证")
    print("=" * 50)

    try:
        test_simple()
        test_stream()
        print("\n🎉 全部测试通过！DeepSeek API 连通正常")
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        sys.exit(1)
