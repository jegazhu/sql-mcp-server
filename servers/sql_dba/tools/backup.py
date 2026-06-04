# servers/sql_dba/tools/backup.py
from ..pool import get_pool

async def status_all(instance: str = "default") -> dict:
    """
    Last backup times (full, diff, log) for all databases.
    """
    async with get_pool(instance) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT 
                    d.name AS database_name,
                    d.recovery_model_desc,
                    MAX(CASE WHEN bs.type = 'D' THEN bs.backup_finish_date END) AS last_full_backup,
                    MAX(CASE WHEN bs.type = 'I' THEN bs.backup_finish_date END) AS last_diff_backup,
                    MAX(CASE WHEN bs.type = 'L' THEN bs.backup_finish_date END) AS last_log_backup
                FROM sys.databases d
                LEFT JOIN msdb.dbo.backupset bs ON d.name = bs.database_name
                GROUP BY d.name, d.recovery_model_desc
                ORDER BY d.name
            """)
            columns = [col[0] for col in cur.description]
            rows = [dict(zip(columns, row)) for row in await cur.fetchall()]
    return {"instance": instance, "backup_status": rows}

async def compliance_check(instance: str = "default") -> dict:
    """
    Check instance against 'good looks like' rules from compliance.json.
    Reads config/compliance.json from the project root.
    """
    import json
    from pathlib import Path
    
    # Load compliance rules
    root = Path(__file__).parent.parent.parent.parent
    compliance_path = root / "config" / "compliance.json"
    try:
        with open(compliance_path, "r") as f:
            rules = json.load(f)
    except FileNotFoundError:
        return {"instance": instance, "error": "compliance.json not found", "checks": []}
    
    results = []
    
    async with get_pool(instance) as conn:
        async with conn.cursor() as cur:
            # Example rule: backup age (in hours)
            if "max_backup_age_hours" in rules:
                max_age = rules["max_backup_age_hours"]
                await cur.execute("""
                    SELECT d.name, MAX(bs.backup_finish_date) AS last_backup,
                           DATEDIFF(HOUR, MAX(bs.backup_finish_date), GETDATE()) AS hours_ago
                    FROM sys.databases d
                    LEFT JOIN msdb.dbo.backupset bs ON d.name = bs.database_name AND bs.type = 'D'
                    WHERE d.name NOT IN ('tempdb')
                    GROUP BY d.name
                    HAVING MAX(bs.backup_finish_date) IS NULL 
                           OR DATEDIFF(HOUR, MAX(bs.backup_finish_date), GETDATE()) > ?
                """, (max_age,))
                rows = await cur.fetchall()
                if rows:
                    results.append({
                        "rule": "backup_age",
                        "compliant": False,
                        "details": [{"database": r[0], "last_backup": r[1], "hours_ago": r[2]} for r in rows]
                    })
                else:
                    results.append({"rule": "backup_age", "compliant": True})
            
            # Example rule: recovery model (full for user databases)
            if "require_full_recovery" in rules and rules["require_full_recovery"]:
                await cur.execute("""
                    SELECT name, recovery_model_desc
                    FROM sys.databases
                    WHERE name NOT IN ('master', 'model', 'msdb', 'tempdb')
                      AND recovery_model_desc != 'FULL'
                """)
                rows = await cur.fetchall()
                if rows:
                    results.append({
                        "rule": "recovery_model",
                        "compliant": False,
                        "details": [{"database": r[0], "recovery_model": r[1]} for r in rows]
                    })
                else:
                    results.append({"rule": "recovery_model", "compliant": True})
            
            # You can add more rules from compliance.json here
            
    return {"instance": instance, "compliance": results}