"""
LLM 安全调用工具
—— token 计数 + 输入截断 + 错误诊断
"""
import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger("agent.llm")


# ===== Token 估算 =====
# DeepSeek V3 中文约 1.5 字符/token，英文约 4 字符/token
# 使用简单混合估算：每个字符 0.4 token
CHARS_PER_TOKEN = 1 / 0.4  # 2.5 字符 = 1 token

# DeepSeek V3 上下文窗口 64K，保守使用 50K 输入上限
MAX_INPUT_TOKENS = 50_000
MAX_PROMPT_CHARS = int(MAX_INPUT_TOKENS * 2.0)  # ~100K 字符


def estimate_tokens(text: str) -> int:
    """估算文本 token 数（简单字符比例法，无需 tiktoken）"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 0.6 + other_chars * 0.25)


def safe_json_dumps(obj: Any, max_chars: int = 30_000) -> str:
    """
    安全序列化为 JSON，超出长度自动截断
    返回截断后的 JSON 字符串
    """
    json_str = json.dumps(obj, ensure_ascii=False, indent=2)
    if len(json_str) <= max_chars:
        return json_str

    # 截断策略：如果是列表，只保留前 N 条
    if isinstance(obj, list) and len(obj) > 0:
        # 二分查找合适数量
        items = obj
        for n in range(len(items), 0, -1):
            truncated = json.dumps(items[:n], ensure_ascii=False, indent=2)
            if len(truncated) <= max_chars:
                suffix = f"\n（共 {len(items)} 条，仅展示前 {n} 条）"
                # 确保加上后缀也不超
                if len(truncated) + len(suffix) <= max_chars + 500:
                    return truncated + suffix
                continue

    # 通用截断：暴力截断
    return json_str[:max_chars - 200] + f"\n（内容过长，已截断，原始长度 {len(json_str)} 字符）"


def check_prompt_size(prompt: str, label: str = "prompt") -> dict[str, Any]:
    """检查 prompt 大小，返回 {chars, tokens, warning}"""
    chars = len(prompt)
    tokens = estimate_tokens(prompt)

    result = {"chars": chars, "tokens": tokens, "warning": None}

    if tokens > MAX_INPUT_TOKENS:
        result["warning"] = (
            f"⚠️ {label} 输入过大：{tokens:,} tokens / {chars:,} 字符，"
            f"超过安全阈值 {MAX_INPUT_TOKENS:,} tokens"
        )
        logger.warning(result["warning"])
    elif tokens > MAX_INPUT_TOKENS * 0.7:
        result["warning"] = (
            f"⚠️ {label} 输入较大：{tokens:,} tokens，接近阈值"
        )
        logger.info(result["warning"])

    return result


def safe_invoke(llm, prompt: str, label: str = "LLM call") -> tuple[Any | None, str | None]:
    """
    安全调用 LLM：检查大小 → 调用 → 错误捕获
    返回 (response, error_message)
    """
    size_info = check_prompt_size(prompt, label)

    if size_info["tokens"] > MAX_INPUT_TOKENS:
        error = f"{label}: 输入过大（{size_info['tokens']:,} tokens），超过 {MAX_INPUT_TOKENS:,} 上限，已跳过 LLM 调用"
        logger.error(error)
        return None, error

    try:
        response = llm.invoke(prompt)
        return response, None
    except Exception as e:
        error_msg = str(e)
        error = f"{label}: LLM 调用失败 — {error_msg}"
        logger.error(error)

        # 诊断常见错误
        if "400" in error_msg and ("length" in error_msg.lower() or "too long" in error_msg.lower()):
            error += f" | 数据大小：{size_info['chars']:,} 字符 / {size_info['tokens']:,} tokens"
        elif "401" in error_msg or "403" in error_msg:
            error += " | 请检查 DEEPSEEK_API_KEY 是否正确"
        elif "429" in error_msg:
            error += " | API 频率限制，请稍后重试"

        return None, error


def parse_llm_json(response: Any, fallback: dict) -> dict:
    """
    解析 LLM 返回的 JSON
    自动处理 markdown 代码块包裹
    """
    if response is None:
        return fallback

    content = response.content.strip()

    # 去掉 markdown 代码块
    if content.startswith("```"):
        lines = content.split("\n")
        lines = lines[1:]  # 去掉 ```json 或 ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    # 尝试找 JSON 对象
    content = content.strip()
    if content.startswith("{") and content.endswith("}"):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

    # 尝试找数组
    if content.startswith("[") and content.endswith("]"):
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return {"items": result}
        except json.JSONDecodeError:
            pass

    logger.warning(f"LLM JSON 解析失败，使用 fallback。原始内容前 200 字符: {content[:200]}")
    return fallback
