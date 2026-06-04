# servers/sql_dba/pool.py
import hashlib
import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

import aioodbc
import structlog
from aioodbc import Pool

logger = structlog.get_logger()
_pool_cache: Dict[str, Pool] = {}

def _get_config_path() -> Path:
    return Path(__file__).parent.parent.parent / "config" / "instances.json"

def _build_connection_string(instance_config: dict) -> str:
    server = instance_config["server"]
    port = instance_config.get("port")
    server_part = f"{server},{port}" if port else server
    database = instance_config.get("database", "master")
    trusted = instance_config.get("trusted_connection", False)
    if trusted:
        auth_part = "Trusted_Connection=yes"
    else:
        username = instance_config.get("username")
        password = instance_config.get("password")
        if not username or not password:
            raise ValueError("SQL auth requires username and password")
        auth_part = f"UID={username};PWD={password}"
    driver = instance_config.get("driver", "ODBC Driver 17 for SQL Server")
    conn_str = f"DRIVER={{{driver}}};SERVER={server_part};DATABASE={database};{auth_part};"
    extra = instance_config.get("extra_options", {})
    for key, value in extra.items():
        conn_str += f"{key}={value};"
    return conn_str

def _hash_connection_string(conn_str: str) -> str:
    return hashlib.sha256(conn_str.encode()).hexdigest()

async def _create_pool(conn_str: str) -> Pool:
    return await aioodbc.create_pool(dsn=conn_str, minsize=1, maxsize=10)

@asynccontextmanager
async def get_pool(instance_name: str) -> AsyncIterator[aioodbc.Connection]:
    # Load config
    config_path = _get_config_path()
    try:
        with open(config_path) as f:
            instances = json.load(f)
    except FileNotFoundError:
        logger.warning("Config file missing", path=str(config_path))
        raise
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON", error=str(e))
        raise

    instance_config = instances.get(instance_name)
    if not instance_config:
        raise KeyError(f"Instance '{instance_name}' not found")

    conn_str = _build_connection_string(instance_config)
    conn_hash = _hash_connection_string(conn_str)

    pool = _pool_cache.get(conn_hash)
    if pool is None:
        pool = await _create_pool(conn_str)
        _pool_cache[conn_hash] = pool
        logger.info("Created pool", instance=instance_name)

    # Acquire connection and yield
    async with pool.acquire() as conn:
        yield conn

async def close_all_pools():
    for pool in _pool_cache.values():
        pool.close()
        await pool.wait_closed()
    _pool_cache.clear()

async def close_all_pools() -> None:
    """Gracefully close all cached connection pools."""
    for conn_hash, pool in _pool_cache.items():
        pool.close()
        await pool.wait_closed()
        logger.info("Closed connection pool", hash=conn_hash[:8])
    _pool_cache.clear()