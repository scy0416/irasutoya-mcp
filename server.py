"""irasutoya(いらすとや) 이미지 검색 MCP 서버.

session-2 구조(MCPServer + Tool/Resource/Prompt)를 따릅니다.
irasutoya는 Blogger로 운영되므로, 검색 결과 HTML을 긁는 대신 공개 JSON 피드
(https://www.irasutoya.com/feeds/posts/default?q=...&alt=json)를 사용합니다.

실행(Inspector 열기): uv run mcp dev server.py
"""

import html
import re
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("Irasutoya Search")

FEED_URL = "https://www.irasutoya.com/feeds/posts/default"
IMAGE_HOST = "blogger.googleusercontent.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (irasutoya-mcp study project)"}

# 본문 HTML에서 원본 이미지 링크(<a href>)와 설명 문장을 뽑는 정규식
_IMG_LINK = re.compile(r'<a[^>]+href="(https://blogger\.googleusercontent\.com/[^"]+)"')
_TAGS = re.compile(r"<[^>]+>")


async def fetch_feed(params: dict[str, Any]) -> dict:
    """Blogger JSON 피드를 가져온다. 네트워크 실패는 ToolError로 바꿔 모델에게 알린다."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
            resp = await client.get(FEED_URL, params={**params, "alt": "json"})
            resp.raise_for_status()
            return resp.json()["feed"]
    except httpx.HTTPError as e:
        raise ToolError(f"irasutoya에 접속하지 못했습니다: {e}") from e


def parse_entry(entry: dict) -> dict:
    """피드 항목 하나를 모델이 읽기 좋은 dict로 정리한다."""
    content = entry.get("content", {}).get("$t", "")
    link = re.search(_IMG_LINK, content)
    page_url = next(
        (l["href"] for l in entry.get("link", []) if l.get("rel") == "alternate"), ""
    )
    # 이미지 링크 <div> 뒤에 오는 텍스트가 작품 설명
    description = html.unescape(_TAGS.sub("", re.sub(r"<a .*?</a>", "", content, flags=re.S))).strip()
    return {
        "title": entry["title"]["$t"],
        "description": description,
        "image_url": link.group(1) if link else None,
        "page_url": page_url,
        "labels": [c["term"] for c in entry.get("category", [])],
        "published": entry.get("published", {}).get("$t", ""),
    }


# ── Tools ──────────────────────────────────────────────────────────────────


@mcp.tool()
async def search_irasutoya(keyword: str, max_results: int = 10, page: int = 1) -> dict:
    """irasutoya(일본 무료 일러스트 사이트)에서 키워드로 일러스트를 검색해 제목, 설명, 이미지 URL을 돌려준다.

    사이트가 일본어라서 keyword는 일본어로 넣어야 결과가 잘 나온다(예: 문 → ドア, 고양이 → 猫).
    사용자가 한국어나 영어로 요청하면 일본어 단어로 바꿔서 검색할 것.
    결과가 더 필요하면 page를 올려서 다시 호출한다.
    """
    keyword = keyword.strip()
    if not keyword:
        raise ToolError("keyword를 입력해 주세요.")
    if not 1 <= max_results <= 30:
        raise ToolError("max_results는 1~30 사이여야 합니다.")
    if page < 1:
        raise ToolError("page는 1 이상이어야 합니다.")

    feed = await fetch_feed(
        {"q": keyword, "max-results": max_results, "start-index": (page - 1) * max_results + 1}
    )
    results = [parse_entry(e) for e in feed.get("entry", [])]
    if not results:
        return {
            "keyword": keyword,
            "page": page,
            "results": [],
            "hint": "결과가 없습니다. 더 짧거나 다른 일본어 단어(히라가나/가타카나 포함)로 다시 검색해 보세요.",
        }
    # 피드는 전체 건수를 알려 주지 않으므로, 요청한 개수를 꽉 채웠으면 다음 페이지가 있을 수 있다고 본다
    return {
        "keyword": keyword,
        "page": page,
        "has_more": len(results) == max_results,
        "results": results,
    }


@mcp.tool()
async def view_irasutoya_image(image_url: str, size: int = 400) -> Image:
    """검색 결과의 image_url을 받아 일러스트 미리보기 이미지를 직접 보여 준다.

    search_irasutoya가 돌려준 image_url만 사용할 수 있다. size는 가로 픽셀(100~800).
    """
    if not 100 <= size <= 800:
        raise ToolError("size는 100~800 사이여야 합니다.")
    parsed = httpx.URL(image_url)
    if parsed.scheme != "https" or parsed.host != IMAGE_HOST:
        raise ToolError(f"{IMAGE_HOST} 의 이미지 URL만 열 수 있습니다. search_irasutoya 결과의 image_url을 사용하세요.")

    # Blogger 이미지 URL 경로의 /s862/ 같은 구간이 크기 지정이라 원하는 크기로 바꾼다
    sized = re.sub(r"/s\d+(-[a-z]+)?/", f"/s{size}/", image_url, count=1)
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
            resp = await client.get(sized)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise ToolError(f"이미지를 가져오지 못했습니다: {e}") from e

    fmt = resp.headers.get("content-type", "image/png").split("/")[-1].split(";")[0]
    return Image(data=resp.content, format=fmt)


# ── Resource ───────────────────────────────────────────────────────────────


@mcp.resource("irasutoya://latest")
async def latest_illustrations() -> str:
    """irasutoya에 가장 최근 올라온 일러스트 10개를 보여 준다."""
    feed = await fetch_feed({"max-results": 10})
    lines = []
    for e in feed.get("entry", []):
        item = parse_entry(e)
        lines.append(f"- {item['title']} ({item['published'][:10]})\n  {item['page_url']}")
    return "\n".join(lines) or "불러온 일러스트가 없습니다."


# ── Prompt ─────────────────────────────────────────────────────────────────


@mcp.prompt()
def find_illustration(topic: str) -> str:
    """원하는 주제에 맞는 irasutoya 일러스트를 찾아 달라고 요청하는 프롬프트."""
    return (
        f"irasutoya에서 '{topic}'에 어울리는 일러스트를 찾아 주세요. "
        "먼저 일본어 검색어로 바꿔 search_irasutoya로 검색하고, "
        "가장 잘 맞는 3개를 view_irasutoya_image로 보여 준 뒤 제목과 페이지 링크를 알려 주세요."
    )


if __name__ == "__main__":
    mcp.run()
