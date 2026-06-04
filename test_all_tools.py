# test_all_tools.py
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://localhost:3001/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            tools = ["wait_stats", "cpu_pressure", "memory_grants", "active_chains", 
                     "deadlock_history", "missing_indexes", "unused_indexes", 
                     "fragmentation", "backup_status_all", "compliance_check"]
            
            for tool_name in tools:
                print(f"\n--- Calling {tool_name} ---")
                result = await session.call_tool(tool_name, arguments={"instance": "default"})
                print(result.content)

if __name__ == "__main__":
    asyncio.run(main())