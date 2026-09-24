"""Agentless MCP Example (Python)
==============================
This example demonstrates how to use the Model Context Protocol (MCP) *without*
an AI agent or Large Language Model (such as Claude, ChatGPT, Cursor, etc.).

What is "Agentless MCP"?
-----------------------
MCP is often perceived as an LLM-only protocol, where an AI assistant acts as the
client that inspects available tools and decides what to call.

In reality, MCP is a lightweight, language-agnostic JSON-RPC 2.0 protocol over
transports like stdio or HTTP/SSE. An MCP client does NOT need an AI model:
- Any regular application, backend service, script, or worker can act as the client.
- The host code directly and deterministically connects to the MCP server,
  discovers tools, passes structured arguments, and handles responses.

Key Benefits of Agentless MCP:
------------------------------
1. Reusability: Access any community or private MCP server (databases, Git,
   Docker, Slack, cloud APIs, filesystems) without writing custom wrappers or SDKs.
2. Determinism & Safety: No LLM hallucinations, prompt injections, or stochastic
   tool-calling behavior. Your code controls the logic flow 100%.
3. Zero Inference Cost: No tokens consumed, no LLM latency, and no API keys required.
4. Process Isolation: MCP servers run as independent child processes communicating
   via standard I/O (stdio), providing safe sandboxing and clean lifecycle management.
"""

import asyncio
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Path to the SQLite database managed by the MCP server
DB_PATH = Path(__file__).resolve().parent / "test.db"

# Configure the MCP server subprocess.
# Note: mcp-server-sqlite 2025.4.25 requires "mcp[cli]>=1.6.0" without an upper bound,
# but calls Server.list_resources(), which was removed in MCP SDK 2.x.
# Pinning `--with mcp[cli]<2` ensures the isolated server environment starts properly.
server_params = StdioServerParameters(
    command="uvx",  # uvx runs the tool in an isolated, ephemeral environment
    args=[
        "--from", "mcp-server-sqlite",
        "--with", "mcp[cli]<2",
        "mcp-server-sqlite",
        "--db-path", str(DB_PATH),
    ],
)


async def main():
    print("--- [Agentless MCP] Python Client Starting ---")

    # Step 1: Spawn the MCP server as a subprocess and establish stdio communication.
    # No LLM or agent runtime is involved; this is a direct inter-process JSON-RPC transport.
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Step 2: Protocol Handshake.
            # Negotiate capabilities and protocol version with the server.
            await session.initialize()
            print("[OK] Connected & initialized MCP session via stdio.")

            # Step 3: Discover Server Capabilities.
            # Deterministically inspect what tools the server exposes and their input schemas.
            tool_listing = await session.list_tools()
            available_tool_names = [tool.name for tool in tool_listing.tools]
            print(f"[OK] Available tools discovered: {available_tool_names}")

            # Step 4: Deterministic Tool Invocation (No LLM in the loop).
            # Your code directly decides which tool to call and provides exact arguments.

            # Example 4a: Create a table using the 'write_query' tool
            print("\nExecuting 'write_query' to create table...")
            create_result = await session.call_tool(
                "write_query",
                arguments={
                    "query": (
                        "CREATE TABLE IF NOT EXISTS notes ("
                        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                        "content TEXT NOT NULL, "
                        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                        ");"
                    )
                },
            )
            print(f"Result: {create_result.content}")

            # Example 4b: Insert a record
            print("\nExecuting 'write_query' to insert a record...")
            insert_result = await session.call_tool(
                "write_query",
                arguments={
                    "query": "INSERT INTO notes (content) VALUES ('Agentless MCP works without any LLM!');"
                },
            )
            print(f"Result: {insert_result.content}")

            # Example 4c: Read back the records using the 'read_query' tool
            print("\nExecuting 'read_query' to fetch records...")
            read_result = await session.call_tool(
                "read_query",
                arguments={"query": "SELECT id, content, created_at FROM notes ORDER BY id DESC LIMIT 3;"},
            )
            print(f"Result: {read_result.content}")

    print("\n--- [Agentless MCP] Session cleanly closed ---")


if __name__ == "__main__":
    asyncio.run(main())