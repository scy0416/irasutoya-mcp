# irasutoya-mcp

irasutoya(いらすとや)에서 일러스트를 검색해 주는 MCP 서버. KANT 스터디 session-2 구조(MCPServer, SDK v2)를 따른다.

| 종류 | 이름 | 설명 |
|---|---|---|
| Tool | `search_irasutoya(keyword, max_results=10, page=1)` | 일본어 키워드로 검색 → 제목/설명/이미지 URL/페이지 URL/라벨 |
| Tool | `view_irasutoya_image(image_url, size=400)` | 검색 결과 이미지를 미리보기로 직접 반환 |
| Resource | `irasutoya://latest` | 최신 일러스트 10개 |
| Prompt | `find_illustration(topic)` | 주제에 맞는 일러스트 찾기 요청 틀 |

검색은 HTML 스크래핑 대신 Blogger 공개 JSON 피드(`/feeds/posts/default?q=...&alt=json`)를 쓴다.

## 실행

```
uv sync
uv run mcp dev server.py            # Inspector
uv run python list_features.py server.py
uv run python test_client.py        # 실제 호출 점검
```

## Claude Desktop 등록 (claude_desktop_config.json)

```json
{
  "mcpServers": {
    "irasutoya": {
      "command": "uv",
      "args": ["--directory", "/절대경로/irasutoya-mcp", "run", "python", "server.py"]
    }
  }
}
```

이미지는 irasutoya 저작권 규약(https://www.irasutoya.com/p/terms.html)을 확인하고 사용할 것.
