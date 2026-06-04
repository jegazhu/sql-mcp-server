# servers/sql_dba/server.py
import atexit
import asyncio
from servers.sql_dba.pool import close_all_pools
from mcp.server.fastmcp import FastMCP
from .pool import get_pool
from .tools import health, blocking, indexes, backup
import structlog
from importlib.metadata import version

print(version("mcp"))
logger = structlog.get_logger()
logger.info("Starting SQL DBA server on port 3001")

mcp = FastMCP("sql-dba", port=3001)

# ========== Health tools ==========
@mcp.tool()
async def wait_stats(instance: str = "default") -> dict:
    """Top 10 wait types by cumulative wait time on a SQL Server instance."""
    async with get_pool(instance) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT TOP 10 wait_type, wait_time_ms, waiting_tasks_count
                FROM sys.dm_os_wait_stats
                WHERE wait_type NOT IN (
                  'SLEEP_TASK','BROKER_TO_FLUSH','XE_TIMER_EVENT'
                )
                ORDER BY wait_time_ms DESC
            """)
            rows = await cur.fetchall()
            # Get column names from cursor description
            columns = [col[0] for col in cur.description]
            result = [dict(zip(columns, row)) for row in rows]
    return {"instance": instance, "waits": result}

@mcp.tool()
async def cpu_pressure(instance: str = "default") -> dict:
    """CPU pressure metrics – scheduler runnable tasks and cumulative CPU usage."""
    return await health.cpu_pressure(instance)

@mcp.tool()
async def memory_grants(instance: str = "default") -> dict:
    """Pending and granted memory grants – detect memory pressure."""
    return await health.memory_grants(instance)

# ========== Blocking tools ==========
@mcp.tool()
async def active_chains(instance: str = "default") -> dict:
    """Currently active blocking chains with lead blocker and waiters."""
    return await blocking.active_chains(instance)

@mcp.tool()
async def deadlock_history(instance: str = "default", minutes: int = 60) -> dict:
    """Deadlock events captured from the system_health session."""
    return await blocking.deadlock_history(instance, minutes)

# ========== Index tools ==========
@mcp.tool()
async def missing_indexes(instance: str = "default", top: int = 20) -> dict:
    """Suggested missing indexes with impact score."""
    return await indexes.missing_indexes(instance, top)

@mcp.tool()
async def unused_indexes(instance: str = "default") -> dict:
    """Indexes with zero reads – candidates for removal."""
    return await indexes.unused_indexes(instance)

@mcp.tool()
async def fragmentation(instance: str = "default", min_frag: int = 30) -> dict:
    """Index fragmentation > min_frag% with page count details."""
    return await indexes.fragmentation(instance, min_frag)

# ========== Backup tools ==========
@mcp.tool()
async def backup_status_all(instance: str = "default") -> dict:
    """Last backup times (full, diff, log) for all databases."""
    return await backup.status_all(instance)

@mcp.tool()
async def compliance_check(instance: str = "default") -> dict:
    """Check instance against 'good looks like' rules from compliance.json."""
    return await backup.compliance_check(instance)

# ========== Run Queries on Server ==========
@mcp.tool()
async def run_sql_query(
    instance: str = "default",
    query: str = "",
    max_rows: int = 100
) -> dict:
    """
    Execute a read‑only SQL query on the specified instance.
    Only SELECT statements are allowed. Results are limited to max_rows.
    """
    # Safety: only allow SELECT
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed for safety.")
    
    # Optional: block certain dangerous commands (e.g., UNION, INTO, etc.)
    for forbidden in ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "EXEC", "EXECUTE"]:
        if forbidden in query_upper:
            raise ValueError(f"Forbidden keyword '{forbidden}' detected. Only SELECT allowed.")
    
    async with get_pool(instance) as conn:
        async with conn.cursor() as cur:
            # Add TOP to limit rows if not already present
            if " TOP " not in query_upper:
                # Simple injection-safe way: prefix with SELECT TOP (max_rows)
                # But need to preserve original ordering? We'll just add a limit clause
                # For SQL Server, use "SELECT TOP (max_rows) ..."
                import re
                # Replace first SELECT with SELECT TOP (max_rows)
                modified_query = re.sub(
                    r'(?i)^\s*SELECT',
                    f'SELECT TOP ({max_rows})',
                    query,
                    count=1
                )
                query = modified_query
            await cur.execute(query)
            # Fetch results
            rows = await cur.fetchall()
            if not rows:
                return {"instance": instance, "query": query, "row_count": 0, "data": []}
            columns = [col[0] for col in cur.description]
            result = [dict(zip(columns, row)) for row in rows]
    return {
        "instance": instance,
        "query": query,
        "row_count": len(result),
        "data": result
    }

# ========== Run the server ==========
def main():
    mcp.run()

if __name__ == "__main__":
    #main()
    # Using 'streamable-http' instead of 'http'
    import uvicorn
    app = mcp.streamable_http_app
    uvicorn.run(app, host="0.0.0.0", port=3001)
    # mcp.run(transport="streamable-http", host="0.0.0.0", port=3001)

def _shutdown():
    asyncio.run(close_all_pools())
atexit.register(_shutdown)