"""东方财富个股新闻数据获取

直接调用东财搜索 API，绕过 AKShare 的 pyarrow 正则兼容 bug。
"""

import json
import re
import time

import requests
from loguru import logger

_HEADERS = {
    "accept": "*/*",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "referer": "https://so.eastmoney.com/",
}

_CALLBACK = "jQuery35101792940631092459_1764599530165"

_TAG_RE = re.compile(r"</?em>")
_PAREN_TAG_RE = re.compile(r"\(</?em>\)")


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = _PAREN_TAG_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    text = text.replace("　", "").replace("\r\n", " ").strip()
    return text


def fetch_stock_news(code: str, count: int = 20, keywords: list[str] | None = None) -> list[dict]:
    """获取个股最新新闻

    Args:
        code: 股票代码，如 "600519"
        count: 获取条数，最多 100
        keywords: 额外搜索关键词（如关联公司名称），每个关键词单独搜索后合并去重

    Returns:
        [{"title": str, "content": str, "time": str, "source": str, "url": str}, ...]
    """
    all_keywords = [code]
    if keywords:
        all_keywords.extend(k.strip() for k in keywords if k.strip())

    seen_titles = set()
    all_news = []

    for kw in all_keywords:
        per_kw_count = count if len(all_keywords) == 1 else max(count // len(all_keywords), 10)
        items = _search_news(kw, min(per_kw_count, 100))
        for item in items:
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                all_news.append(item)

    all_news.sort(key=lambda x: x["time"], reverse=True)
    return all_news[:count]


def _search_news(keyword: str, count: int) -> list[dict]:
    """搜索单个关键词的新闻"""
    url = "https://search-api-web.eastmoney.com/search/jsonp"
    inner_param = {
        "uid": "",
        "keyword": keyword,
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": "default",
                "pageIndex": 1,
                "pageSize": count,
                "preTag": "<em>",
                "postTag": "</em>",
            }
        },
    }
    params = {
        "cb": _CALLBACK,
        "param": json.dumps(inner_param, ensure_ascii=False),
        "_": str(int(time.time() * 1000)),
    }

    for attempt in range(3):
        try:
            resp = requests.get(
                url, params=params, headers=_HEADERS, timeout=10
            )
            resp.raise_for_status()
            break
        except Exception as e:
            if attempt == 2:
                logger.error(f"获取 '{keyword}' 新闻失败: {e}")
                return []
            time.sleep(1)

    try:
        text = resp.text
        json_str = text[len(_CALLBACK) + 1 : -1]
        data = json.loads(json_str)
        items = data.get("result", {}).get("cmsArticleWebOld", [])
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"解析 '{keyword}' 新闻数据失败: {e}")
        return []

    news_list = []
    for item in items:
        article_code = item.get("code", "")
        news_list.append({
            "title": _clean_html(item.get("title", "")),
            "content": _clean_html(item.get("content", "")),
            "time": item.get("date", ""),
            "source": item.get("mediaName", ""),
            "url": f"http://finance.eastmoney.com/a/{article_code}.html"
            if article_code
            else "",
        })

    return news_list
