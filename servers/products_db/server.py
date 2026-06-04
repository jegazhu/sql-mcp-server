# servers/products_db/server.py
import httpx
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

load_dotenv()
logger = structlog.get_logger()

class Settings(BaseSettings):
    dab_base_url: str = "http://localhost:5000/api"
    dab_timeout: float = 30.0

    class Config:
        model_config = SettingsConfigDict(
            env_prefix = "DAB_",
            env_file = ".env",
            extra = "ignore"
        )

settings = Settings()
#PORT = int(os.getenv("SQL_DBA_PORT", "3001"))
mcp = FastMCP("products-db", port=5001)
client = httpx.AsyncClient(timeout=settings.dab_timeout)

@mcp.tool()
async def query_products(
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 100
) -> dict:
    """Query products with optional filters."""
    params = {"$top": limit}
    if category:
        params["$filter"] = f"category eq '{category}'"
    if min_price is not None:
        params["$filter"] = (params.get("$filter", "") + 
                            f" and price ge {min_price}" if "$filter" in params 
                            else f"price ge {min_price}")
    if max_price is not None:
        params["$filter"] = (params.get("$filter", "") + 
                            f" and price le {max_price}" if "$filter" in params 
                            else f"price le {max_price}")
    
    resp = await client.get(f"{settings.dab_base_url}/products", params=params)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
async def get_product(id: int) -> dict:
    """Fetch a single product by ID."""
    resp = await client.get(f"{settings.dab_base_url}/products({id})")
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
async def create_product(name: str, price: float, category: str) -> dict:
    """Insert a new product."""
    resp = await client.post(
        f"{settings.dab_base_url}/products",
        json={"name": name, "price": price, "category": category}
    )
    resp.raise_for_status()
    return resp.json()

def main():
    mcp.run()

if __name__ == "__main__":
    main()