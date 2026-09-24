//! # Agentless MCP Example (Rust)
//!
//! This example demonstrates using the Model Context Protocol (MCP) in Rust
//! **without** an AI agent or Large Language Model (such as Claude, ChatGPT, Cursor, etc.).
//!
//! ## What is "Agentless MCP"?
//! While MCP was created to connect LLMs to tools, the underlying protocol is simply
//! a bidirectional JSON-RPC 2.0 specification running over standard I/O (stdio) or HTTP/SSE.
//!
//! An MCP Client does NOT need to be an LLM:
//! - A native Rust binary can act as the MCP Client directly.
//! - The Rust application connects directly to pre-built MCP servers written in Node.js,
//!   Python, or Go, gaining instant access to databases, web scraping, git, or filesystem tools.
//! - Tool invocations are 100% deterministic, type-checked, instant (no LLM latency),
//!   and cost nothing in AI tokens.

use mcp_client_rs::client::ClientBuilder;
use serde_json::json;

// On Windows `npx` is a `.cmd` shim, which std::process::Command cannot find by
// bare name (it only appends `.exe` when resolving through PATH).
#[cfg(windows)]
const NPX: &str = "npx.cmd";
#[cfg(not(windows))]
const NPX: &str = "npx";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("--- [Agentless MCP] Rust Client Starting ---");

    // Step 1: Configure & Spawn the MCP server as a subprocess.
    // Here we launch the official reference `@modelcontextprotocol/server-everything` via npx.
    // Communication happens over standard I/O (stdin/stdout) via JSON-RPC.
    println!("[1/4] Spawning server process and performing handshake...");
    let client = ClientBuilder::new(NPX)
        .args(["-y", "@modelcontextprotocol/server-everything"])
        .implementation("agentless-mcp-eg", env!("CARGO_PKG_VERSION"))
        .spawn_and_initialize()
        .await?;
    println!("[OK] Connected & initialized MCP session via stdio.");

    // Step 2: Discover available tools from the server.
    // Inspect the tools and schemas exposed by the server dynamically.
    println!("\n[2/4] Querying available tools...");
    let tools = client.list_tools().await?;
    let tool_names: Vec<&str> = tools.tools.iter().map(|t| t.name.as_str()).collect();
    println!("[OK] Discovered {} tools: {:?}", tool_names.len(), tool_names);

    // Step 3: Deterministic Tool Invocation (No LLM in the loop).
    // The Rust client directly selects the 'echo' tool and sends structured parameters.
    //
    // Note on client.call_tool vs raw request:
    // Some versions of `mcp_client_rs::call_tool` deserialize `isError` as a required bool,
    // whereas spec-compliant MCP servers omit `isError` on success.
    // Using `client.request("tools/call", ...)` sends the raw standard JSON-RPC 2.0 call safely.
    println!("\n[3/4] Calling tool 'echo' with deterministic input...");
    let res = client
        .request(
            "tools/call",
            Some(json!({
                "name": "echo",
                "arguments": {
                    "message": "Hello from agentless Rust MCP client!"
                }
            })),
        )
        .await?;
    println!("[OK] Tool response: {}", res);

    // Step 4: Clean shutdown.
    // Terminate the MCP session and allow the server child process to exit.
    println!("\n[4/4] Shutting down MCP client session...");
    client.shutdown().await?;
    println!("--- [Agentless MCP] Session cleanly closed ---");

    Ok(())
}

