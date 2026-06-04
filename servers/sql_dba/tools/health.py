# servers/sql_dba/tools/health.py
from ..pool import get_pool

#async def cpu_pressure(instance: str) -> dict:
#    async with get_pool(instance) as conn:
#        async with conn.cursor() as cur:
#            await cur.execute("""
#                SELECT 
#                    scheduler_id,
#                    runnable_tasks_count,
#                    active_workers_count,
#                    current_tasks_count
#                FROM sys.dm_os_schedulers
#                WHERE scheduler_id < 255  -- exclude DAC
#            """)
#            rows = await cur.fetchall()
#    return {"instance": instance, "schedulers": [dict(r) for r in rows]}

async def cpu_pressure(instance: str) -> dict:
    async with get_pool(instance) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT scheduler_id, runnable_tasks_count, active_workers_count
                FROM sys.dm_os_schedulers
                WHERE scheduler_id < 255
            """)
            columns = [col[0] for col in cur.description]
            rows = [dict(zip(columns, row)) for row in await cur.fetchall()]
    return {"instance": instance, "schedulers": rows}

async def memory_grants(instance: str) -> dict:
    async with get_pool(instance) as conn:
        async with conn.cursor() as cur:
            # Removed 'is_next_runner' – not available in older SQL Server versions
            await cur.execute("""
                SELECT 
                    request_id,
                    grant_time,
                    requested_memory_kb,
                    granted_memory_kb,
                    required_memory_kb,
                    wait_time_ms
                FROM sys.dm_exec_query_memory_grants
            """)
            columns = [col[0] for col in cur.description]
            rows = [dict(zip(columns, row)) for row in await cur.fetchall()]
    return {"instance": instance, "memory_grants": rows}