# SQL MCP Server

[![LinkedIn](https://img.shields.io/badge/Follow%20me%20on-LinkedIn-blue?logo=linkedin&style=social)](https://www.linkedin.com/in/jegazhu/)

**Stop guessing. Wire AI agents directly into SQL Server DMVs — 28 purpose‑built tools for estate‑wide diagnostics, compliance checks, and natural‑language database access.**

This project implements a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes a rich set of SQL Server diagnostic tools via a simple HTTP API. It connects to one or more SQL Server instances using Windows authentication or SQL logins, and it is designed to be used by AI assistants like Claude Desktop, Cursor, or Continue.

# Repository Structure
```
sql-mcp-server/
├── .gitignore
├── README.md
├── LICENSE (choose MIT or Apache-2.0)
├── pyproject.toml
├── .env.example
├── docker-compose.yml (optional)
├── config/
│   ├── instances.json
│   └── compliance.json
├── servers/
│   ├── __init__.py
│   ├── sql_dba/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── pool.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       ├── blocking.py
│   │       ├── indexes.py
│   │       └── backup.py
│   └── products_db/
│       ├── __init__.py
│       └── server.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_health.py
│   └── test_dab_proxy.py
└── scripts/
    └── run_server.ps1 (optional helper)
```

## Features

- **Health checks** – wait stats, CPU pressure, memory grants
- **Blocking analysis** – active blocking chains, deadlock history
- **Index management** – missing, unused, fragmented indexes
- **Backup monitoring** – last backup times, custom compliance rules
- **Ad‑hoc SQL queries** – safe, read‑only `SELECT` statements
- **Multi‑instance support** – manage many servers from one MCP endpoint
- **StreamableHTTP transport** – works with Claude Desktop via `mcp-proxy`

## Quick Start

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) package manager
- SQL Server instance with Windows authentication (or SQL login)
- ODBC Driver for SQL Server (e.g., `SQL Server Native Client 11.0` or `ODBC Driver 17`)

# Install dependencies
```
uv sync
```

# Configure SQL Server instances
```
{
  "default": {
    "server": "YOUR_SERVER",
    "database": "master",
    "trusted_connection": true,
    "driver": "SQL Server Native Client 11.0"
  }
}
```
- trusted_connection: true uses Windows authentication (your current user).
- For SQL authentication, add username and password.

# (Optional) Create compliance rules
```
{
  "max_backup_age_hours": 24,
  "require_full_recovery": true
}
```

# Run the server
```
uv run python -m servers.sql_dba.server
```
You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:3001
```

# Connect to Claude Desktop
```
uv tool install mcp-proxy
```

# Add to:
```
%APPDATA%\Claude\claude_desktop_config.json

{
  "mcpServers": {
    "sql-dba": {
      "command": "C:\\Users\\YOUR_USER\\.local\\bin\\mcp-proxy.exe",
      "args": [
        "http://127.0.0.1:3001/mcp",
        "--transport",
        "streamablehttp"
      ]
    }
  }
}
```
Restart Claude Desktop. Then ask: "What MCP servers are connected?" → sql-dba should appear.
# Finally, Smoke test a tool:

Ask Claude: *"Using the sql-dba server, show me the top 5 wait stats on my SQL Server."*
Claude will call the wait_stats tool and return real DMV data.

## Tools Reference

| Tool Name           | Description                                                              |
|---------------------|--------------------------------------------------------------------------|
| `wait_stats`        | Top 10 wait types by cumulative wait time                                |
| `cpu_pressure`      | Scheduler runnable tasks and active workers                              |
| `memory_grants`     | Pending and granted memory grants                                        |
| `active_chains`     | Active blocking chains with lead blocker                                 |
| `deadlock_history`  | Last deadlock events (system_health session)                             |
| `missing_indexes`   | Suggested indexes with impact score                                      |
| `unused_indexes`    | Indexes with zero reads                                                  |
| `fragmentation`     | Index fragmentation > threshold                                          |
| `backup_status_all` | Last full/diff/log backups per database                                  |
| `compliance_check`  | Validates instance against compliance.json                               |
| `run_sql_query`     | Execute read‑only SELECT statements (safe)                               |

# Development - Run tests
```
uv run pytest
```

# Add a new tool
1. Implement the SQL query in the appropriate ```tools/*.py``` file.
2. Add a ```@mcp.tool()``` decorated function in ```server.py```.
3. Restart the server – the tool will be automatically exposed.

Using with other MCP clients
Any client that supports StreamableHTTP (e.g., ```mcp-cli```, Continue, Cursor) can connect to ```http://localhost:3001/mcp```.

# Troubleshooting
## Server starts but no tools appear in Claude
- Ensure ```mcp-proxy``` is installed and the path is absolute in the config.
- Check Claude logs: ```%APPDATA%\Claude\logs\mcp.log```.
- Verify the server is running before launching Claude.

```run_sql_query``` returns empty
- The query may be targeting the wrong database. Prefix with ```DatabaseName.dbo.TableName```.
- Use ```SELECT TOP 10 * FROM sys.databases``` to test.

# ODBC driver errors
Confirm the driver name matches exactly what is in ODBC Administrator ```(odbcad32.exe)```.

For Windows authentication, use ```Trusted_Connection=yes```.

### 1. Clone the repository

```bash
git clone https://github.com/jegazhu/sql-mcp-server.git
cd sql-mcp-server
```

# Contributing
Issues and pull requests are welcome! Please ensure all tools are documented and tests pass.

# Acknowledgements [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) – simplified MCP server framework
- [aioodbc](https://github.com/aio-libs/aioodbc) – async ODBC pool
- [uv](https://docs.astral.sh/uv/) – fast Python package manager

# Happy diagnosing! 🚀
```

---

## 🐍 3. Final `pyproject.toml` (with scripts and build)

```toml
[project]
name = "sql-mcp-server"
version = "0.1.0"
description = "MCP server for SQL Server diagnostics – wait stats, indexes, blocking, backups, and ad-hoc queries."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "aioodbc>=0.5.0",
    "httpx>=0.28.1",
    "mcp[cli]>=1.27.1",
    "pydantic-settings>=2.14.1",
    "python-dotenv>=1.2.2",
    "structlog>=25.5.0",
    "uvicorn>=0.48.0",
]

[project.scripts]
sql-dba-server = "servers.sql_dba.server:main"
products-db-server = "servers.products_db.server:main"

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.4.0",
    "respx>=0.23.1",
    "testcontainers>=4.14.2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
package = true

[tool.hatch.build.targets.wheel]
packages = ["servers"]
```
