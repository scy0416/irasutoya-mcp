"""서버를 실제로 띄워 Tool/Resource/Prompt를 호출해 보는 점검 스크립트."""
import json
import os
import sys

import anyio
from mcp import Client, StdioServerParameters


def _env() -> dict[str, str]:
    """사내/샌드박스 프록시 환경에서만 필요: 서버 자식 프로세스에 프록시·CA 설정을 넘긴다."""
    keys = ("HTTPS_PROXY", "https_proxy", "NO_PROXY", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE")
    return {k: os.environ[k] for k in keys if k in os.environ}


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=["server.py"], env=_env())
    async with Client(params) as c:
        r = await c.call_tool("search_irasutoya", {"keyword": "ドア", "max_results": 3})
        data = json.loads(r.content[0].text)
        print("search:", "has_more=", data["has_more"], "/", [(x["title"], x["image_url"][-40:]) for x in data["results"]])
        first = data["results"][0]
        p2 = json.loads((await c.call_tool("search_irasutoya", {"keyword": "ドア", "max_results": 3, "page": 2})).content[0].text)
        print("page2:", [x["title"] for x in p2["results"]])
        none = json.loads((await c.call_tool("search_irasutoya", {"keyword": "zzzzqqqq"})).content[0].text)
        print("empty:", none["results"], none["hint"][:20])
        img = await c.call_tool("view_irasutoya_image", {"image_url": first["image_url"], "size": 200})
        print("image:", [(x.type, getattr(x, "mime_type", None), len(getattr(x, "data", "") or "")) for x in img.content])
        bad = await c.call_tool("view_irasutoya_image", {"image_url": "https://example.com/a.png"})
        print("bad:", bad.is_error, [getattr(x, "text", "") for x in bad.content])
        res = await c.read_resource("irasutoya://latest")
        print("resource:", res.contents[0].text[:200])
        p = await c.get_prompt("find_illustration", {"topic": "문"})
        print("prompt:", p.messages[0].content.text[:80])


anyio.run(main)
