# Agentless MCP: Using Model Context Protocol Without AI Agents

> Demonstrating how to use the **Model Context Protocol (MCP)** directly from standard application code (**Python** and **Rust**) without an LLM or AI agent (like Claude, ChatGPT, Cursor, Windsurf, etc.).

---

## Table of Contents

- [The Big Misconception](#the-big-misconception)
- [What is "Agentless MCP"?](#what-is-agentless-mcp)
- [Why Use MCP Without an Agent?](#why-use-mcp-without-an-agent)
- [Agent-Driven vs. Agentless MCP](#agent-driven-vs-agentless-mcp)
- [Architecture & Flow](#architecture--flow)
- [Repository Structure](#repository-structure)
- [Python Implementation (`main.py`)](#python-implementation-mainpy)
- [Rust Implementation (`src/main.rs`)](#rust-implementation-srcmainrs)
- [Quickstart & Running](#quickstart--running)
- [How to Plug In Other MCP Servers](#how-to-plug-in-other-mcp-servers)

---

## The Big Misconception

When developers hear about the **Model Context Protocol (MCP)**, they usually imagine:

> *A human talks to Claude Desktop or an AI coding agent; the agent reads a prompt, chooses an MCP tool, generates JSON arguments, calls the tool, and summarizes the result.*

Because Anthropic introduced MCP in the context of AI assistants, many assume:
- MCP *requires* an LLM.
- You *must* have an AI model in the loop to use MCP servers.
- MCP is purely an AI prompt-orchestration layer.

**This is a myth.**

---

## What is "Agentless MCP"?

At its core, **MCP is simply an open, standardized client-server protocol based on JSON-RPC 2.0**. It defines standard interfaces for:
1. **Handshake & Capabilities** (`initialize`)
2. **Tool Discovery** (`tools/list`)
3. **Tool Execution** (`tools/call`)
4. **Resources & Prompts** (`resources/list`, `resources/read`, etc.)

An **MCP Client** does **not** have to be an AI agent or LLM. It can be:
- A backend REST/GraphQL microservice.
- A scheduled cron job or ETL pipeline.
- A CLI application or automation script.
- A compiled binary (like Rust, Go, or C++) controlling external subsystems.

In **Agentless MCP**, your application code takes the place of the agent. Your code deterministically spawns or connects to the server, inspects capabilities, selects tools, passes structured arguments, and handles responses.

---

## Why Use MCP Without an Agent?

Why would you use an MCP server instead of installing a normal native library or SDK?

### 1. Universal Plugin & Tool Interface
Instead of writing 20 different integration layers for 20 tools (PostgreSQL, SQLite, GitHub, Jira, Slack, Docker, filesystem, Puppeteer), MCP gives you **one uniform protocol**. If a tool has an MCP server, any language can invoke it identically via JSON-RPC.

### 2. 100% Deterministic & Safe
- **Zero Hallucinations**: Code directly passes validated arguments. No LLM guessing field names or types.
- **Zero Prompt Injection Risk**: Tool inputs are programmatic parameters, not parsed from natural language.
- **Predictable Control Flow**: Standard `if/else`, loops, and error-handling semantics govern when and how tools run.

### 3. Zero AI Cost & Zero Latency Overhead
- **0 Tokens**: Completely free of LLM API billing.
- **Sub-millisecond Overhead**: Tool execution happens at native process/RPC speeds, without waiting for 1,000ms+ of LLM inference or streaming.

### 4. Process Sandboxing & Language Agnosticism
- MCP servers run as isolated child processes (over `stdio`) or over HTTP/SSE.
- **Polyglot without FFI**: A Rust binary can run and control a Node.js or Python tool without writing C bindings, PyO3, or complex IPC wrappers.
- If an MCP server crashes or leaks memory, the client application remains isolated and stable.

### 5. Hybrid Architectures
You can write deterministic business workflows that use MCP tools directly, and only invoke an LLM when fuzzy reasoning or natural language synthesis is genuinely needed.

---

## Agent-Driven vs. Agentless MCP

| Feature | Agent-Driven MCP (Claude, Cursor, etc.) | Agentless MCP (This Repository) |
|---|---|---|
| **Client** | LLM / AI Assistant Runtime | Regular Python / Rust code |
| **Tool Selection** | Heuristic / LLM decides dynamically | Programmatic / Deterministic code |
| **Argument Generation** | LLM predicts arguments from prompt | Validated directly in code |
| **Execution Speed** | Latency of LLM inference + tool run | Instant local/RPC execution |
| **Cost** | API token cost per tool call | **$0.00** (Free, no LLMs) |
| **Reliability** | Probabilistic (can hallucinate or fail schema) | Deterministic (strict code execution) |
| **Protocol** | Standard JSON-RPC 2.0 | Standard JSON-RPC 2.0 |

---

## Architecture & Flow

```
+-------------------------------------------------------------+
|                     Agentless Client                        |
|       (Python Script / Rust Binary / Backend Service)       |
+-------------------------------------------------------------+
                              │
             1. Spawns process / Handshake
             2. JSON-RPC: initialize
             3. JSON-RPC: tools/list
             4. JSON-RPC: tools/call { "name": ..., "args": ... }
                              │  (Standard I/O stdin/stdout)
                              ▼
+-------------------------------------------------------------+
|                        MCP Server                           |
|       (mcp-server-sqlite, @modelcontextprotocol/..., etc.)  |
+-------------------------------------------------------------+
                              │
                 Executes tool operation
            (Database queries, FS actions, API calls)
```

---

## Repository Structure

```
agentless-mcp-eg/
├── main.py              # Agentless MCP client in Python (using official mcp SDK)
├── Cargo.toml           # Rust package configuration
├── src/
│   └── main.rs          # Agentless MCP client in Rust (using mcp_client_rs)
├── pyproject.toml       # Python package configuration (uv / pip)
├── test.db              # SQLite database created/managed by mcp-server-sqlite
└── README.md            # Comprehensive documentation & guide
```

---

## Python Implementation (`main.py`)

The Python implementation uses the official [`mcp`](https://github.com/modelcontextprotocol/python-sdk) SDK to directly control an isolated SQLite database server (`mcp-server-sqlite`) without an agent.

### Code Highlights

```python
import asyncio
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DB_PATH = Path(__file__).resolve().parent / "test.db"

# 1. Define server parameters (uvx spawns mcp-server-sqlite in an isolated environment)
server_params = StdioServerParameters(
    command="uvx",
    args=[
        "--from", "mcp-server-sqlite",
        "--with", "mcp[cli]<2",  # Pin SDK 1.x for compatibility with mcp-server-sqlite
        "mcp-server-sqlite",
        "--db-path", str(DB_PATH),
    ],
)

async def main():
    # 2. Establish stdio transport directly with the subprocess
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 3. Protocol handshake
            await session.initialize()

            # 4. Discover server capabilities programmatically
            tools = await session.list_tools()

            # 5. Deterministically call tools (create table, insert, select)
            await session.call_tool("write_query", arguments={"query": "CREATE TABLE IF NOT EXISTS notes ..."})
            await session.call_tool("write_query", arguments={"query": "INSERT INTO notes ..."})
            res = await session.call_tool("read_query", arguments={"query": "SELECT * FROM notes ..."})
            print(res.content)
```

### Server SDK Compatibility Note
`mcp-server-sqlite` (version 2025.4.25) relies on internal server APIs from MCP Python SDK `<2.0.0`. When running with `uvx`, passing `--with "mcp[cli]<2"` isolates the server's runtime from the client's modern MCP 2.x SDK.

---

## Rust Implementation (`src/main.rs`)

The Rust implementation demonstrates that a native, compiled language can easily consume existing Node.js or Python MCP servers without needing any language-specific bindings or AI runtime.

### Code Highlights

```rust
use mcp_client_rs::client::ClientBuilder;
use serde_json::json;

// On Windows, npx is a .cmd script
#[cfg(windows)]
const NPX: &str = "npx.cmd";
#[cfg(not(windows))]
const NPX: &str = "npx";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Spawn @modelcontextprotocol/server-everything via npx and perform handshake
    let client = ClientBuilder::new(NPX)
        .args(["-y", "@modelcontextprotocol/server-everything"])
        .implementation("agentless-mcp-eg", env!("CARGO_PKG_VERSION"))
        .spawn_and_initialize()
        .await?;

    // 2. Discover available tools
    let tools = client.list_tools().await?;

    // 3. Directly invoke tool via standard JSON-RPC
    let res = client
        .request(
            "tools/call",
            Some(json!({
                "name": "echo",
                "arguments": { "message": "Hello from agentless Rust MCP client!" }
            })),
        )
        .await?;

    println!("Tool response: {}", res);

    // 4. Clean shutdown
    client.shutdown().await?;
    Ok(())
}
```

### Windows Shim Note
On Windows, `npx` is installed as `npx.cmd`. Because Rust's `std::process::Command` searches `PATH` with `.exe` by default, using `npx.cmd` on Windows ensures reliable cross-platform execution.

---

## Quickstart & Running

### Prerequisites

- **Python**: 3.10+ (with [`uv`](https://docs.astral.sh/uv/) installed)
- **Node.js / npm**: For `npx` (used by the Rust example)
- **Rust toolchain**: `cargo` / `rustc` (optional, for the Rust example)

### 1. Running the Python Example

Using `uv`:
```bash
uv run python main.py
```

Expected output:
```text
--- [Agentless MCP] Python Client Starting ---
[OK] Connected & initialized MCP session via stdio.
[OK] Available tools discovered: ['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight']

Executing 'write_query' to create table...
Result: [TextContent(type='text', text="[{'affected_rows': -1}]", annotations=None, meta=None)]

Executing 'write_query' to insert a record...
Result: [TextContent(type='text', text="[{'affected_rows': 1}]", annotations=None, meta=None)]

Executing 'read_query' to fetch records...
Result: [TextContent(type='text', text="[{'id': 1, 'content': 'Agentless MCP works without any LLM!', 'created_at': '...'}]", annotations=None, meta=None)]

--- [Agentless MCP] Session cleanly closed ---
```

### 2. Running the Rust Example

```bash
cargo run
```

Expected output:
```text
--- [Agentless MCP] Rust Client Starting ---
[1/4] Spawning server process and performing handshake...
[OK] Connected & initialized MCP session via stdio.

[2/4] Querying available tools...
[OK] Discovered 13 tools: ["echo", "get-annotated-message", "get-env", ...]

[3/4] Calling tool 'echo' with deterministic input...
[OK] Tool response: {"content":[{"text":"Echo: Hello from agentless Rust MCP client!","type":"text"}]}

[4/4] Shutting down MCP client session...
--- [Agentless MCP] Session cleanly closed ---
```

---

## How to Plug In Other MCP Servers

Because MCP is a standard protocol, swapping or adding any community MCP server requires only changing the command and arguments.

### PostgreSQL
```python
server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost/mydb"],
)
```

### Git
```python
server_params = StdioServerParameters(
    command="uvx",
    args=["mcp-server-git", "--repository", "/path/to/repo"],
)
```

### Filesystem
```python
server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/allowed/directory"],
)
```

Your client code can then list tools, inspect the generated JSON Schema for input requirements, and invoke operations deterministically—no LLM or AI agent required.
