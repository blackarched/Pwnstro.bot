# In /usr/local/share/pwnagotchi/custom-plugins/WebUI_data.py
import logging
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
import pwnagotchi.plugins as plugins
import toml

class WebUI_data(plugins.Plugin):
    __author__ = 'Your Name'
    __version__ = '4.0.0'
    __license__ = 'GPL3'
    __description__ = 'A plugin to save all Pwnagotchi state to a JSON file for the C&C dashboard.'

    def __init__(self):
        self.ready = False
        self.agent = None
        self.output_path = Path('/tmp/pwnagotchi_data.json')
        self.handshake_dir = Path('/root/handshakes/')
        self.config_path = Path("/etc/pwnagotchi/config.toml")
        self.last_log_line = ""

    def on_loaded(self):
        logging.info("WebUI_data plugin loaded. Data will be saved to %s", self.output_path)
        if not self.handshake_dir.exists():
            self.handshake_dir.mkdir(parents=True)
        self.ready = True
        
    def on_agent(self, agent):
        self.agent = agent

    def get_config_data(self):
        """Safely reads AI and personality data from the config file."""
        config = {}
        if self.config_path.exists():
            try:
                config = toml.load(self.config_path)
            except Exception as e:
                logging.error(f"[webui_data] Error parsing config.toml: {e}")

        main_ai = config.get("main", {}).get("ai", {})
        personality = config.get("personality", {})
        
        return {
            "ai_enabled": main_ai.get("enabled", False),
            "epsilon": main_ai.get("epsilon_start", 0.0),
            "learning_rate": main_ai.get("learning_rate", 0.0),
            "excited_epochs": personality.get("excited_num_epochs", 0),
            "bored_epochs": personality.get("bored_num_epochs", 0),
            "sad_epochs": personality.get("sad_num_epochs", 0)
        }

    def get_ip_address(self):
        # ... (no changes)
        try:
            result = subprocess.check_output("ip -4 addr | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){3}' | grep -v '127.0.0.1'", shell=True).decode().strip()
            return result.split('\n')[0] if result else 'N/A'
        except Exception: return 'N/A'

    def get_handshakes(self):
        # ... (no changes)
        handshakes = []
        for pcap_file in self.handshake_dir.glob('*.pcap'):
            stats = pcap_file.stat()
            creation_time = datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            handshakes.append({"name": pcap_file.name, "size_kb": round(stats.st_size / 1024, 2), "timestamp": creation_time})
        handshakes.sort(key=lambda x: x['timestamp'], reverse=True)
        return handshakes
        
    def on_ui_update(self, ui):
        if not self.ready: return

        try:
            loaded_plugins = list(self.agent.plugins.keys()) if self.agent else []
            
            state_data = {
                "device_info": { "face": ui.get('face'), "status": ui.get('status'), "mode": ui.get('mode'), "epoch": ui.get('epoch'), "uptime": ui.get('uptime'), "cpu_load": ui.get('cpu'), "temperature": f"{ui.get('temperature') or 0:.1f}", "memory": ui.get('mem'), "channel": ui.get('channel_text'), "ip_address": self.get_ip_address(), "internet": str(ui.get('internet_connection')) },
                "session_stats": { "aps_total": ui.get('aps_total'), "aps_session": ui.get('aps_session'), "handshakes_total": ui.get('shakes_total'), "handshakes_session": ui.get('shakes_session'), "deauths": ui.get('deauth'), "associations": ui.get('assoc'), "pmkids": ui.get('pmkid') },
                "peers": ui.get('peers') or [],
                "plugins_loaded": loaded_plugins,
                "handshakes": self.get_handshakes(),
                "ai_stats": self.get_config_data(),
                "timestamp": datetime.now().isoformat()
            }

            with self.output_path.open('w') as f: json.dump(state_data, f, indent=4)

        except Exception as e: logging.error(f"WebUI_data plugin error: {e}", exc_info=True)