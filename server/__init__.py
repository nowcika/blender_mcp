import argparse
import os

from mcp.server.fastmcp import FastMCP

from .blender_client import BlenderClient
from .tools import register_tools


def create_server() -> FastMCP:
    # Design Ref: §3.5 — BlenderClient config from env vars; tools injected at startup
    host = os.environ.get("BLENDER_MCP_HOST", "localhost")
    port = int(os.environ.get("BLENDER_MCP_PORT", 9999))

    blender = BlenderClient(host=host, port=port)
    mcp = FastMCP("blender-mcp")
    register_tools(mcp, blender)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Blender MCP Server")
    # Plan SC: SC-03 — both stdio and HTTP/SSE transports must be available
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode: stdio (Claude Desktop) or http (SSE remote)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP server bind host")
    parser.add_argument("--port", type=int, default=8080, help="HTTP server port")
    args = parser.parse_args()

    mcp = create_server()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        # Design Ref: §3.5 — HTTP/SSE via FastMCP's built-in SSE transport
        mcp.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
