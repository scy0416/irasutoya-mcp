"""내 서버가 어떤 기능을 내놓는지 한눈에 확인하는 스크립트.

실행: uv run python list_features.py template/server.py
Inspector를 열지 않고도 Tool, Resource, Prompt 목록과 설명을 볼 수 있어
저장 직후 빠르게 점검할 때 편합니다.
"""

import sys

import anyio
from mcp import Client, StdioServerParameters


async def main(path: str) -> None:
    params = StdioServerParameters(command=sys.executable, args=[path])
    async with Client(params) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        prompts = await client.list_prompts()

        print(f"Tools ({len(tools.tools)})")
        for t in tools.tools:
            print(f"  - {t.name}: {t.description}")
        print(f"Resources ({len(resources.resources)}), Templates ({len(templates.resource_templates)})")
        for r in resources.resources:
            print(f"  - {r.uri}: {r.description}")
        for t in templates.resource_templates:
            print(f"  - {t.uri_template}: {t.description}")
        print(f"Prompts ({len(prompts.prompts)})")
        for p in prompts.prompts:
            print(f"  - {p.name}: {p.description}")


if len(sys.argv) != 2:
    sys.exit("사용법: uv run python list_features.py <서버 파일 경로>")
anyio.run(main, sys.argv[1])
