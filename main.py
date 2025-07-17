import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any

import toml
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pwnagotchi_api import get_pwnagotchi_data, get_peers, get_handshakes

# --- Configuration ---
LOG_LEVEL = logging.INFO
HOST = "0.0.0.0"
PORT = 8080
HANDSHAKE_DIR = Path("/root/handshakes/")
CONFIG_PATH = Path("/etc/pwnagotchi/config.toml")
PLUGIN_DIRS = [
    Path("/usr/local/share/pwnagotchi/custom-plugins/"),
    Path("/usr/share/pwnagotchi/plugins/")
]
BSSID_REGEX = re.compile(r'^([0-9a-fA-F]{2}[:]){5}([0-9a-fA-F]{2})$')
EPOCH_LOG_FILE = "/tmp/pwn_epoch_history.log"
AI_PARAMS_FILE = "/tmp/pwn_ai_params.json"


logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = FastAPI(title="Pwnagotchi C&C API", version="5.0.0")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

class AttackRequest(BaseModel):
    bssid: str

class AiParamsRequest(BaseModel):
    params: Dict[str, Any]

# --- Helper Functions ---
def restart_pwnagotchi_service():
    try:
        subprocess.run(["sudo", "systemctl", "restart", "pwnagotchi"], check=True, capture_output=True, text=True)
        logger.info("Pwnagotchi service restarted successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to restart pwnagotchi service: {e}")
        return False

# --- API Endpoints (in logical order) ---

# Core Data
@app.get("/api/data")
async def get_data(): return await get_pwnagotchi_data()

# Handshakes
@app.get("/api/handshakes/{filename:path}")
async def download_handshake(filename: str):
    try:
        file_path = (HANDSHAKE_DIR / filename).resolve()
        if not file_path.is_file() or not str(file_path).startswith(str(HANDSHAKE_DIR.resolve())):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(file_path, media_type='application/vnd.tcpdump.pcap', filename=filename)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# Configuration
@app.get("/api/config")
async def get_config_file():
    if not CONFIG_PATH.is_file(): raise HTTPException(status_code=404, detail="config.toml not found")
    return FileResponse(CONFIG_PATH, media_type='text/plain')

@app.post("/api/config")
async def update_config_file(request: Request):
    try:
        new_config_content = await request.body()
        toml.loads(new_config_content.decode())
        with open(CONFIG_PATH, "wb") as f: f.write(new_config_content)
        if restart_pwnagotchi_service(): return {"message": "Config saved. Pwnagotchi is restarting."}
        else: raise HTTPException(status_code=500, detail="Config saved, but service restart failed.")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# Plugins
@app.get("/api/plugins")
async def get_plugins():
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
    config = toml.load(CONFIG_PATH)
    plugins_config = config.setdefault("main", {}).setdefault("plugins", {})
    plugin_entry = plugins_config.setdefault(plugin_name, {})
    current_status = plugin_entry.get("enabled", False)
    plugin_entry["enabled"] = not current_status
    with open(CONFIG_PATH, "w") as f: toml.dump(config, f)
    if restart_pwnagotchi_service(): return {"message": f"Plugin '{plugin_name}' toggled. Pwnagotchi is restarting."}
    else: raise HTTPException(status_code=500, detail="Config saved, but service restart failed.")

# PwnGRID
@app.get("/api/grid")
async def get_grid_status():
    config = toml.load(CONFIG_PATH)
    grid_config = config.get("main", {}).get("plugins", {}).get("grid", {})
    key_path = Path(grid_config.get("key_path", "/etc/pwnagotchi/pwnagotchi.rsa"))
    return {
        "enabled": grid_config.get("enabled", False), "report_mode": grid_config.get("report", False),
        "keys_generated": key_path.exists() and key_path.with_suffix(".pub").exists()
    }

# AI Insights
@app.get("/api/ai/epochs")
async def get_epoch_history():
    if not os.path.exists(EPOCH_LOG_FILE): return []
    try:
        with open(EPOCH_LOG_FILE, "r") as f:
            return [json.loads(line) for line in f]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/params")
async def set_ai_params(req: AiParamsRequest):
    try:
        # Basic validation
        valid_params = {k: float(v) for k, v in req.params.items() if v}
        if not valid_params: raise HTTPException(status_code=400, detail="No valid parameters provided.")
        with open(AI_PARAMS_FILE, "w") as f:
            json.dump(valid_params, f)
        logger.info(f"Manual AI parameters queued for update: {valid_params}")
        return {"message": "AI parameters queued for next update cycle."}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))


# Attacks
@app.post("/api/attack/{type}")
async def trigger_attack(type: str, req: AttackRequest):
    if type not in ["deauth", "assoc"]: raise HTTPException(status_code=400, detail="Invalid attack type.")
    if not BSSID_REGEX.match(req.bssid): raise HTTPException(status_code=400, detail="Invalid BSSID format.")
    target_file = f"/tmp/pwn_{type}_target.txt"
    with open(target_file, "w") as f: f.write(req.bssid)
    logger.info(f"Manual {type} command queued for BSSID: {req.bssid}")
    return {"message": f"{type.capitalize()} attack queued for {req.bssid}."}

# System Control
@app.post("/api/control/toggle_ai")
async def toggle_ai():
    config = toml.load(CONFIG_PATH)
    ai_config = config.setdefault("main", {}).setdefault("ai", {})
    ai_config["enabled"] = not ai_config.get("enabled", False)
    with open(CONFIG_PATH, "w") as f: toml.dump(config, f)
    if restart_pwnagotchi_service(): return {"message": "AI mode toggled. Pwnagotchi is restarting."}
    else: raise HTTPException(status_code=500, detail="Config saved, but service restart failed.")

@app.post("/api/control/restart")
async def restart_service():
    if restart_pwnagotchi_service(): return {"message": "Pwnagotchi service is restarting."}
    else: raise HTTPException(status_code=500, detail="Failed to issue restart command.")

@app.post("/api/control/shutdown")
async def shutdown_system():
    try:
        subprocess.run(["sudo", "shutdown", "now"], check=True)
        return {"message": "System shutdown command issued."}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- WebSocket and Static Files ---
async def broadcast_updates():
    while True:
        await asyncio.sleep(5)
        try:
            data = await get_pwnagotchi_data()
            if "error" not in data:
                data["peers"] = await get_peers(data)
                data["handshakes"] = await get_handshakes()
                await manager.broadcast(json.dumps(data))
        except Exception as e: logger.error(f"Error in broadcast loop: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        data = await get_pwnagotchi_data()
        if "error" not in data:
            data["peers"] = await get_peers(data)
            data["handshakes"] = await get_handshakes()
            await websocket.send_text(json.dumps(data))
        while True: await websocket.receive_text()
    except WebSocketDisconnect: logger.info("Client disconnected.")
    finally: manager.disconnect(websocket)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse("static/gemini_dash5.html")

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(broadcast_updates())

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
