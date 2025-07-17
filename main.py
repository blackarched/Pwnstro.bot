import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any

import toml
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# --- Configuration ---
LOG_LEVEL = logging.INFO
HOST = "0.0.0.0"
PORT = 8080
PWNAGOTCHI_DATA_FILE = Path("/tmp/pwnagotchi_data.json")
HANDSHAKE_DIR = Path("/root/handshakes/")
CONFIG_PATH = Path("/etc/pwnagotchi/config.toml")
PLUGIN_DIRS = [ Path("/usr/local/share/pwnagotchi/custom-plugins/"), Path("/usr/share/pwnagotchi/plugins/") ]

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)
app = FastAPI(title="Pwnagotchi C&C API", version="4.0.0")

class ConnectionManager:
    # ... (no changes)
    def __init__(self): self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket): await websocket.accept(); self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket): self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections: await connection.send_text(message)
manager = ConnectionManager()

# --- Helper Functions ---
async def get_pwnagotchi_data() -> dict:
    if not PWNAGOTCHI_DATA_FILE.is_file(): return {"error": "Pwnagotchi data file not found."}
    try:
        with open(PWNAGOTCHI_DATA_FILE, 'r') as f: return json.load(f)
    except Exception as e: return {"error": str(e)}

def restart_pwnagotchi_service():
    try:
        subprocess.run(["sudo", "systemctl", "restart", "pwnagotchi"], check=True)
        logger.info("Pwnagotchi service restarted successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to restart pwnagotchi service: {e}")
        return False

# --- API Endpoints ---
@app.get("/api/data")
async def get_data(): return await get_pwnagotchi_data()

@app.get("/api/handshakes/{filename:path}")
async def download_handshake(filename: str):
    # ... (no changes)
    try:
        file_path = (HANDSHAKE_DIR / filename).resolve()
        if not file_path.is_file() or not str(file_path).startswith(str(HANDSHAKE_DIR.resolve())):
            raise HTTPException(status_code=404, detail="File not found.")
        return FileResponse(file_path, media_type='application/vnd.tcpdump.pcap', filename=filename)
    except Exception as e: raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/config")
async def get_config_file():
    if not CONFIG_PATH.is_file(): raise HTTPException(status_code=404, detail="config.toml not found.")
    return FileResponse(CONFIG_PATH, media_type='text/plain')

@app.post("/api/config")
async def update_config_file(request: Request):
    # ... (no changes)
    try:
        new_config_content = await request.body()
        toml.loads(new_config_content.decode())
        with open(CONFIG_PATH, "wb") as f: f.write(new_config_content)
        if restart_pwnagotchi_service(): return {"message": "Configuration saved. Pwnagotchi is restarting."}
        else: raise HTTPException(status_code=500, detail="Config saved, but service restart failed.")
    except Exception as e: raise HTTPException(status_code=500, detail=f"Failed to update config: {e}")

@app.get("/api/plugins")
async def get_plugins():
    # ... (no changes)
    if not CONFIG_PATH.is_file(): return JSONResponse(content={"error": "config.toml not found."}, status_code=404)
    config = toml.load(CONFIG_PATH)
    enabled_plugins = config.get("main", {}).get("plugins", {})
    available_plugins = {}
    for plugin_dir in PLUGIN_DIRS:
        if plugin_dir.is_dir():
            for f in plugin_dir.glob("*.py"):
                if f.stem != "__init__": available_plugins[f.stem] = {}
    result = [{"name": name, "enabled": enabled_plugins.get(name, {}).get("enabled", False)} for name in available_plugins]
    return sorted(result, key=lambda x: x['name'])

@app.post("/api/plugins/toggle/{plugin_name}")
async def toggle_plugin(plugin_name: str):
    # ... (no changes)
    if not CONFIG_PATH.is_file(): raise HTTPException(status_code=404, detail="config.toml not found.")
    try:
        config = toml.load(CONFIG_PATH)
        plugins_config = config.setdefault("main", {}).setdefault("plugins", {})
        plugin_entry = plugins_config.setdefault(plugin_name, {})
        plugin_entry["enabled"] = not plugin_entry.get("enabled", False)
        with open(CONFIG_PATH, "w") as f: toml.dump(config, f)
        if restart_pwnagotchi_service(): return {"message": f"Plugin '{plugin_name}' toggled. Pwnagotchi restarting."}
        else: raise HTTPException(status_code=500, detail="Config saved, but service restart failed.")
    except Exception as e: raise HTTPException(status_code=500, detail=f"Failed to toggle plugin: {e}")

# --- NEW: Final Control Endpoints ---
@app.post("/api/control/toggle_ai")
async def toggle_ai():
    """Toggles main.ai.enabled in config.toml and restarts."""
    if not CONFIG_PATH.is_file():
        raise HTTPException(status_code=404, detail="config.toml not found.")
    try:
        config = toml.load(CONFIG_PATH)
        ai_config = config.setdefault("main", {}).setdefault("ai", {})
        current_status = ai_config.get("enabled", False)
        ai_config["enabled"] = not current_status
        new_mode = "AUTO" if not current_status else "MANU"
        with open(CONFIG_PATH, "w") as f:
            toml.dump(config, f)
        if restart_pwnagotchi_service():
            return {"message": f"AI mode set to {new_mode}. Pwnagotchi is restarting."}
        else:
            raise HTTPException(status_code=500, detail="AI mode changed, but service restart failed.")
    except Exception as e:
        logger.error(f"Failed to toggle AI: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle AI: {e}")

@app.post("/api/control/shutdown")
async def shutdown_system():
    """Issues a safe shutdown command to the system."""
    try:
        subprocess.run(["sudo", "shutdown", "now"], check=True)
        return {"message": "System shutdown command issued."}
    except Exception as e:
        logger.error(f"Failed to shutdown system: {e}")
        raise HTTPException(status_code=500, detail="Failed to issue shutdown command.")

# --- Background Task, WebSocket, and Static Files (no changes) ---
async def broadcast_updates():
    # ...
    last_known_mtime = 0
    while True:
        await asyncio.sleep(2)
        try:
            if not PWNAGOTCHI_DATA_FILE.exists(): continue
            mtime = PWNAGOTCHI_DATA_FILE.stat().st_mtime
            if mtime > last_known_mtime:
                last_known_mtime = mtime
                data = await get_pwnagotchi_data()
                if "error" not in data: await manager.broadcast(json.dumps(data))
        except Exception as e: logger.error(f"Broadcast loop error: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # ...
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps(await get_pwnagotchi_data()))
        while True: await asyncio.sleep(1)
    except WebSocketDisconnect: pass
    finally: manager.disconnect(websocket)

app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("static/gemini_dash5.html", "r") as f: return HTMLResponse(content=f.read())
    except FileNotFoundError: return HTMLResponse("<h1>Dashboard HTML not found.</h1>", status_code=404)
@app.on_event("startup")
async def on_startup(): asyncio.create_task(broadcast_updates())

if __name__ == "__main__": uvicorn.run(app, host=HOST, port=PORT)