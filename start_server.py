"""Entry point for running the MCP server directly (no -m flag needed)."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from server import main

main()
