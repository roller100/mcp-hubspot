import argparse
import asyncio
import logging
from .server import Server

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('mcp_hubspot')

def main():
    logger.debug("Starting mcp-server-hubspot main()")
    parser = argparse.ArgumentParser(description='HubSpot MCP Server')
    parser.add_argument('--access-token', help='HubSpot access token')
    args = parser.parse_args()
    
    logger.debug(f"Access token from args: {args.access_token}")
    # Run the async main function
    logger.debug("About to run server")
    server = Server()
    asyncio.run(server.run())
    logger.debug("Server completed")

if __name__ == "__main__":
    main()

# Expose important items at package level
__all__ = ["main", "Server"]
