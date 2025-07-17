import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any

import httpx

# --- Configuration ---
PWNAGOTCHI_API_URL = "http://127.0.0.1:8666/api/v1"

logger = logging.getLogger(__name__)

async def get_pwnagotchi_data() -> Dict[str, Any]:
    """Fetches data from the Pwnagotchi's local API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PWNAGOTCHI_API_URL}/data")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error fetching data from Pwnagotchi API: {e}")
        return {"error": "Could not connect to Pwnagotchi API"}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from Pwnagotchi API: {e}")
        return {"error": "Invalid JSON response from Pwnagotchi API"}

async def get_handshakes() -> Dict[str, Any]:
    """Fetches the list of handshakes from the Pwnagotchi's handshake directory."""
    try:
        handshake_dir = Path("/root/handshakes/")
        handshakes = []
        for handshake_file in handshake_dir.glob("*.pcap"):
            handshakes.append({
                "name": handshake_file.name,
                "timestamp": handshake_file.stat().st_mtime,
                "size_kb": round(handshake_file.stat().st_size / 1024, 2)
            })
        return handshakes
    except Exception as e:
        logger.error(f"Error fetching handshakes: {e}")
        return {"error": "Could not fetch handshakes"}

async def get_peers() -> Dict[str, Any]:
    """Fetches the list of peers from the Pwnagotchi's local API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PWNAGOTCHI_API_URL}/mesh/peers")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error fetching peers from Pwnagotchi API: {e}")
        return {"error": "Could not connect to Pwnagotchi API"}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from Pwnagotchi API: {e}")
        return {"error": "Invalid JSON response from Pwnagotchi API"}
