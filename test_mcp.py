# test_mcp_client.py
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://localhost:3001/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List all tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Call wait_stats tool
            result = await session.call_tool("wait_stats", arguments={"instance": "default"})
            print("\nwait_stats result:")
            print(result.content)

if __name__ == "__main__":
    asyncio.run(main())