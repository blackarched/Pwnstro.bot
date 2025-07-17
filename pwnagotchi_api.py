import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import httpx

# --- Configuration ---
PWNAGOTCHI_API_URL = "http://127.0.0.1:8666/api/v1/data"
HANDSHAKE_DIR = Path("/root/handshakes/")

logger = logging.getLogger(__name__)

async def get_pwnagotchi_data() -> Dict[str, Any]:
    """Fetches the main data blob from the Pwnagotchi's local API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(PWNAGOTCHI_API_URL)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error fetching data from Pwnagotchi API: {e}")
        return {"error": "Could not connect to Pwnagotchi API. Is it running and is the web UI plugin enabled?"}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from Pwnagotchi API: {e}")
        return {"error": "Invalid JSON response from Pwnagotchi API."}
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching Pwnagotchi data: {e}")
        return {"error": "An unknown error occurred."}

async def get_handshakes() -> List[Dict[str, Any]]:
    """Fetches the list of handshakes from the Pwnagotchi's handshake directory."""
    handshakes = []
    if not HANDSHAKE_DIR.is_dir():
        logger.warning(f"Handshake directory not found: {HANDSHAKE_DIR}")
        return []
    try:
        for handshake_file in sorted(HANDSHAKE_DIR.glob("*.pcap"), key=lambda f: f.stat().st_mtime, reverse=True):
            stat = handshake_file.stat()
            handshakes.append({
                "name": handshake_file.name,
                "timestamp": stat.st_mtime,
                "size_kb": round(stat.st_size / 1024, 2)
            })
        return handshakes
    except Exception as e:
        logger.error(f"Error fetching handshakes from {HANDSHAKE_DIR}: {e}")
        return [] # Return empty list on error

def get_peers(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts peer information from the main data payload."""
    # Modern Pwnagotchi APIs include peers in the main /data endpoint.
    # This avoids a separate call to a potentially non-existent /mesh/peers endpoint.
    return data.get("peers", [])