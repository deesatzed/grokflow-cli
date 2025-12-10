# MCP Server Integration Guide for GrokFlow

**Date**: 2025-12-09
**Purpose**: How to integrate Model Context Protocol (MCP) servers and tools into GrokFlow CLI

---

## What is MCP?

Model Context Protocol (MCP) is an open protocol that enables AI applications to securely access external data sources and tools. It provides:

- **Standardized tool calling** - Consistent interface for AI to invoke tools
- **Context providers** - Access to files, databases, APIs, etc.
- **Security** - Sandboxed execution with permission controls
- **Composability** - Mix and match different MCP servers

**Official Spec**: https://spec.modelcontextprotocol.io/

---

## Current GrokFlow Architecture

GrokFlow currently has:
- ✅ Direct API integration with x.ai Grok models
- ✅ OpenAI-compatible client (via `OpenAI` class)
- ✅ Custom tools (git, test runners, file operations)
- ❌ **No MCP integration** (yet!)

**Opportunity**: Add MCP support to enable:
- Database queries (PostgreSQL, MongoDB, etc.)
- Web search (Google, Bing, DuckDuckGo)
- File system access (structured, permission-controlled)
- API integrations (GitHub, Slack, Jira, etc.)
- Custom business tools

---

## MCP Integration Options

### Option 1: Python MCP SDK (Recommended)

**Library**: `mcp` (official Python SDK)
**Install**: `pip install mcp`

**Architecture**:
```
GrokFlow CLI
    ↓
MCP Client (Python SDK)
    ↓
MCP Server (stdio or SSE)
    ↓
Tools/Resources (filesystem, database, API)
```

**Example Integration**:

```python
# grokflow/mcp_client.py
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class GrokFlowMCPClient:
    """MCP client for GrokFlow tool integration"""

    def __init__(self, server_config: dict):
        """
        Initialize MCP client with server configuration

        Args:
            server_config: {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/data"],
                "env": {...}
            }
        """
        self.server_config = server_config
        self.session = None
        self.available_tools = []

    async def connect(self):
        """Connect to MCP server"""
        server_params = StdioServerParameters(
            command=self.server_config["command"],
            args=self.server_config["args"],
            env=self.server_config.get("env")
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()

                # List available tools
                tools_result = await session.list_tools()
                self.available_tools = tools_result.tools

                return self.available_tools

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call an MCP tool"""
        if not self.session:
            raise RuntimeError("MCP session not initialized")

        result = await self.session.call_tool(tool_name, arguments)
        return result


# Usage in grokflow_v2.py
async def smart_fix_with_mcp(self, target: str):
    """Smart fix with MCP tool support"""

    # Initialize MCP client
    mcp = GrokFlowMCPClient({
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    })

    # Connect and list tools
    tools = await mcp.connect()
    console.print(f"[cyan]MCP tools available: {[t.name for t in tools]}[/cyan]")

    # Read file using MCP
    file_content = await mcp.call_tool("read_file", {"path": target})

    # Include MCP tools in Grok prompt
    tools_description = "\n".join([
        f"- {tool.name}: {tool.description}" for tool in tools
    ])

    prompt = f"""
    You have access to the following tools:
    {tools_description}

    File to fix: {target}
    Content: {file_content}

    Analyze and suggest fixes.
    """

    # ... rest of fix logic
```

**Available MCP Servers**:
- `@modelcontextprotocol/server-filesystem` - File operations
- `@modelcontextprotocol/server-postgres` - PostgreSQL queries
- `@modelcontextprotocol/server-github` - GitHub API
- `@modelcontextprotocol/server-brave-search` - Web search
- `@modelcontextprotocol/server-sqlite` - SQLite queries

---

### Option 2: HuggingFace MCPClient (Alternative)

**Library**: Built into `huggingface_hub>=0.28.0`
**Advantage**: Already have `sentence-transformers` which depends on it

**Example**:
```python
from huggingface_hub import MCPClient

# Initialize MCP client
client = MCPClient(
    servers=[
        {
            "type": "stdio",
            "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
            }
        }
    ]
)

# Connect and list tools
await client.connect_servers()
tools = await client.list_tools()

# Call tool
result = await client.call_tool("read_file", {"path": "app.py"})
```

---

### Option 3: Custom HTTP/SSE Integration

**For web-based MCP servers**:

```python
import httpx

class SSEMCPClient:
    """MCP client for Server-Sent Events (SSE) servers"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def list_tools(self):
        """List available tools via HTTP"""
        response = await self.client.get(f"{self.base_url}/tools")
        return response.json()

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call tool via HTTP POST"""
        response = await self.client.post(
            f"{self.base_url}/tools/{tool_name}",
            json=arguments
        )
        return response.json()
```

---

## Implementation Plan

### Phase 1: Basic MCP Support (1-2 days)

1. **Add MCP dependency**:
   ```bash
   pip install mcp
   ```

2. **Create `grokflow/mcp_client.py`**:
   - Basic MCP client wrapper
   - Support stdio servers
   - Tool listing and calling

3. **Update `grokflow_v2.py`**:
   - Add `--mcp-server` flag
   - Load MCP configuration from `.env` or config file
   - Initialize MCP client in `__init__()`

4. **Test with filesystem server**:
   ```bash
   export GROKFLOW_MCP_SERVER="npx -y @modelcontextprotocol/server-filesystem ."
   python grokflow_v2.py fix app.py
   ```

### Phase 2: Multi-Server Support (2-3 days)

1. **Configuration file** (`.grokflow/mcp.json`):
   ```json
   {
     "servers": {
       "filesystem": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
       },
       "postgres": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-postgres"],
         "env": {
           "POSTGRES_CONNECTION_STRING": "postgresql://..."
         }
       },
       "github": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-github"],
         "env": {
           "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
         }
       }
     }
   }
   ```

2. **Tool discovery UI**:
   ```bash
   grokflow mcp list
   ```
   Output:
   ```
   Available MCP Servers:

   📁 filesystem (12 tools)
     - read_file: Read file contents
     - write_file: Write file contents
     - list_directory: List directory contents
     ...

   🗄️ postgres (5 tools)
     - query: Execute SQL query
     - describe_table: Get table schema
     ...

   🐙 github (20 tools)
     - create_issue: Create GitHub issue
     - create_pr: Create pull request
     ...
   ```

3. **Automatic tool selection**:
   - Grok model analyzes prompt
   - Determines which MCP tools to use
   - Calls tools automatically
   - Incorporates results into response

### Phase 3: Advanced Features (3-5 days)

1. **Tool composition**:
   - Chain multiple MCP tools together
   - Example: Read file → Analyze → Create GitHub issue

2. **Permission management**:
   - User approval for sensitive operations
   - Sandboxed execution

3. **Performance optimization**:
   - Cache tool results
   - Parallel tool execution
   - Connection pooling

---

## Example: MCP-Enhanced Fix Workflow

**User command**:
```bash
grokflow fix app.py --with-mcp
```

**Behind the scenes**:

1. **GrokFlow loads MCP servers**:
   - Filesystem server (read/write files)
   - GitHub server (create issues/PRs)
   - Postgres server (query database)

2. **Grok analyzes file**:
   ```
   System: You have access to these tools:
   - read_file(path): Read file contents
   - write_file(path, content): Write file
   - query_postgres(sql): Query database
   - create_github_issue(title, body): Create issue

   User: Fix app.py

   Grok: Let me analyze the file using read_file...
   ```

3. **Grok calls tools**:
   - `read_file("app.py")` → Gets content
   - `query_postgres("SELECT * FROM users LIMIT 1")` → Checks schema
   - Analyzes and generates fix

4. **Grok applies fix**:
   - `write_file("app.py", fixed_content)` → Writes fix
   - `create_github_issue("Bug: SQL injection", "Fixed in app.py")` → Documents

---

## Configuration Examples

### Minimal Setup (.env)
```bash
GROKFLOW_MCP_FILESYSTEM=true
GROKFLOW_MCP_FILESYSTEM_PATH=/Users/yourname/projects
```

### Advanced Setup (.grokflow/mcp.json)
```json
{
  "servers": {
    "filesystem": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "permissions": {
        "read": ["**/*.{py,ts,js,md}"],
        "write": ["src/**/*.{py,ts,js}"]
      }
    },
    "github": {
      "enabled": true,
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "enabled": false,
      "command": "uvx",
      "args": ["mcp-server-postgres"],
      "env": {
        "DATABASE_URL": "${POSTGRES_URL}"
      }
    }
  }
}
```

---

## Security Considerations

1. **Permission controls**:
   - Whitelist allowed paths for filesystem access
   - Require user approval for destructive operations
   - Sandbox tool execution

2. **Credential management**:
   - Store tokens in `.env` (gitignored)
   - Use environment variable substitution
   - Never hardcode credentials

3. **Audit logging**:
   - Log all MCP tool calls
   - Track who called what when
   - Alert on suspicious activity

---

## Testing Strategy

```python
# tests/test_mcp_integration.py
import pytest
from grokflow.mcp_client import GrokFlowMCPClient

@pytest.mark.asyncio
async def test_mcp_filesystem_connection():
    """Test connecting to filesystem MCP server"""
    mcp = GrokFlowMCPClient({
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    })

    tools = await mcp.connect()
    assert len(tools) > 0
    assert any(t.name == "read_file" for t in tools)

@pytest.mark.asyncio
async def test_mcp_read_file():
    """Test reading file via MCP"""
    mcp = GrokFlowMCPClient({...})
    await mcp.connect()

    # Create test file
    test_file = "/tmp/test.txt"
    Path(test_file).write_text("Hello MCP!")

    # Read via MCP
    result = await mcp.call_tool("read_file", {"path": test_file})
    assert "Hello MCP!" in result.content[0].text
```

---

## Roadmap

### v1.5.0 - MCP Foundation (Next Release)
- ✅ Basic MCP client integration
- ✅ Filesystem server support
- ✅ Tool listing command
- ✅ Manual tool calling

### v1.6.0 - Multi-Server Support
- ✅ Multiple MCP servers simultaneously
- ✅ Configuration file support
- ✅ Automatic tool discovery
- ✅ GitHub integration

### v2.0.0 - Advanced MCP
- ✅ Automatic tool selection by Grok
- ✅ Tool composition (chaining)
- ✅ Permission management UI
- ✅ Custom MCP server creation

---

## Resources

**Official MCP**:
- Specification: https://spec.modelcontextprotocol.io/
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Servers: https://github.com/modelcontextprotocol/servers

**GrokFlow Docs**:
- Current: See CLI_USAGE_GUIDE.md
- MCP Guide: This document

**Community**:
- MCP Discord: https://discord.gg/modelcontextprotocol
- GrokFlow Issues: https://github.com/deesatzed/grokflow-cli/issues

---

## Quick Start (Manual Testing)

1. **Install MCP SDK**:
   ```bash
   pip install mcp
   ```

2. **Test filesystem server**:
   ```bash
   # In Python
   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client

   async def test():
       params = StdioServerParameters(
           command="npx",
           args=["-y", "@modelcontextprotocol/server-filesystem", "."]
       )
       async with stdio_client(params) as (read, write):
           async with ClientSession(read, write) as session:
               await session.initialize()
               tools = await session.list_tools()
               print([t.name for t in tools.tools])

   import asyncio
   asyncio.run(test())
   ```

3. **Expected output**:
   ```
   ['read_file', 'read_multiple_files', 'write_file', 'create_directory', ...]
   ```

---

**Status**: Not yet implemented in GrokFlow
**Priority**: High - Would enable powerful workflow automation
**Effort**: Medium - ~5-10 days for full implementation
**Risk**: Low - MCP is well-documented and stable

**Recommendation**: Start with Phase 1 (basic support) in v1.5.0 release.
