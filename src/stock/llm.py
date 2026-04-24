"""统一 LLM 客户端

支持多种大模型 provider:
- claude: Anthropic Claude (需要 anthropic 包)
- qwen: 通义千问 (阿里，OpenAI 兼容)
- deepseek: DeepSeek (OpenAI 兼容)
- zhipu: 智谱 GLM (清华，OpenAI 兼容)
- openai: OpenAI GPT (OpenAI 原生)

通义千问/DeepSeek/智谱/OpenAI 都走 OpenAI SDK 的兼容接口，
只需要配置不同的 base_url 和 model。
"""

from loguru import logger

from stock.config import settings

# 各 provider 的默认配置
_PROVIDER_DEFAULTS = {
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
}


def chat(prompt: str, system: str = "") -> str:
    """统一的 LLM 调用接口

    Args:
        prompt: 用户消息
        system: 系统提示词（可选）

    Returns:
        模型回复文本
    """
    provider = settings.llm_provider.lower()

    if provider == "claude":
        return _call_claude(prompt, system)
    else:
        return _call_openai_compatible(prompt, system, provider)


def _call_claude(prompt: str, system: str) -> str:
    """调用 Claude API"""
    if not settings.anthropic_api_key:
        return "未配置 ANTHROPIC_API_KEY"

    try:
        import anthropic
    except ImportError:
        return "请安装 anthropic 包: pip install anthropic"

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        kwargs = {
            "model": settings.anthropic_model,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        message = client.messages.create(**kwargs)
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API 调用失败: {e}")
        return f"调用失败: {e}"


def _call_openai_compatible(prompt: str, system: str, provider: str) -> str:
    """调用 OpenAI 兼容接口（通义千问/DeepSeek/智谱/OpenAI）"""
    if not settings.openai_api_key:
        return f"未配置 OPENAI_API_KEY（当前 provider: {provider}）"

    try:
        from openai import OpenAI
    except ImportError:
        return "请安装 openai 包: pip install openai"

    defaults = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["openai"])
    base_url = settings.openai_base_url or defaults["base_url"]
    model = settings.openai_model or defaults["model"]

    try:
        client = OpenAI(api_key=settings.openai_api_key, base_url=base_url)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"{provider} API 调用失败: {e}")
        return f"调用失败: {e}"


def is_configured() -> bool:
    """检查 LLM 是否已配置"""
    provider = settings.llm_provider.lower()
    if provider == "claude":
        return bool(settings.anthropic_api_key)
    return bool(settings.openai_api_key)


def get_provider_name() -> str:
    """获取当前 provider 的显示名称"""
    names = {
        "claude": "Claude",
        "qwen": "通义千问",
        "deepseek": "DeepSeek",
        "zhipu": "智谱 GLM",
        "openai": "OpenAI",
    }
    return names.get(settings.llm_provider.lower(), settings.llm_provider)
