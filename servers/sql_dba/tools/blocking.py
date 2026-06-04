# servers/sql_dba/tools/blocking.py
from ..pool import get_pool

async def active_chains(instance: str) -> dict:
    async with get_pool(instance) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT 
                    r.session_id,
                    r.blocking_session_id,
                    r.wait_type,
                    r.wait_time,
                    r.last_wait_type,
                    r.command,
                    r.status,
                    s.program_name,
                    s.host_name
                FROM sys.dm_exec_requests r
                LEFT JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
                WHERE r.blocking_session_id > 0
            """)
            columns = [col[0] for col in cur.description]
            rows = [dict(zip(columns, row)) for row in await cur.fetchall()]
    return {"instance": instance, "blocking_chains": rows}

async def deadlock_history(instance: str, minutes: int = 60) -> dict:
    async with get_pool(instance) as conn:
        async with conn.cursor() as cur:
            # Use a parameter placeholder (%s or ?) depending on driver
            await cur.execute("""
                SELECT TOP 10
                    XEventData.XEvent.value('@timestamp', 'datetime') AS event_time,
                    XEventData.XEvent.query('.') AS deadlock_xml
                FROM (SELECT CAST(target_data AS xml) AS TargetData
                      FROM sys.dm_xe_session_targets st
                      JOIN sys.dm_xe_sessions s ON s.address = st.event_session_address
                      WHERE s.name = 'system_health'
                        AND st.target_name = 'ring_buffer') AS Data
                CROSS APPLY TargetData.nodes('RingBufferTarget/event[@name="xml_deadlock_report"]') AS XEventData(XEvent)
                WHERE XEventData.XEvent.value('@timestamp', 'datetime') > DATEADD(MINUTE, -?, GETUTCDATE())
                ORDER BY event_time DESC
            """, (minutes,))
            # Fetch and convert
            rows = await cur.fetchall()
            # Since XML may be large, return a summary
            result = []
            for row in rows:
                result.append({
                    "event_time": row[0],
                    "deadlock_xml_preview": str(row[1])[:500]  # truncate for readability
                })
    return {"instance": instance, "deadlocks": result}