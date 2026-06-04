import asyncio
from servers.sql_dba.pool import get_pool, close_all_pools

async def test():
    async with get_pool("default") as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT @@VERSION")
            row = await cur.fetchone()
            print("Connected successfully! SQL Server version:")
            print(row[0])

async def main():
    await test()
    await close_all_pools()

if __name__ == "__main__":
    asyncio.run(main())