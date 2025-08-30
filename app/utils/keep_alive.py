import asyncio
import logging
import aiohttp
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
PING_INTERVAL = 600  # Default: 10 minutes (600 seconds)
SERVICE_URL = "https://api.azlok.com/health"

async def ping_service():
    """Send a ping request to the service to keep it alive."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SERVICE_URL) as response:
                if response.status == 200:
                    logger.info(f"Keep-alive ping successful at {datetime.now().isoformat()}")
                else:
                    logger.warning(f"Keep-alive ping failed with status {response.status}")
    except Exception as e:
        logger.error(f"Keep-alive ping error: {str(e)}")

async def start_keep_alive():
    """Start the keep-alive service."""
    logger.info(f"Starting keep-alive service, pinging every {PING_INTERVAL} seconds")
    while True:
        await ping_service()
        await asyncio.sleep(PING_INTERVAL)
