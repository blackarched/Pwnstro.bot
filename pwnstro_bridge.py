import logging
import os
import json
from collections import deque
from pwnagotchi.plugins import BasePlugin
from pwnagotchi.ui import view

class PwnstroBridge(BasePlugin):
    __author__ = 'pwnstrobot'
    __version__ = '2.0.0'
    __license__ = 'GPL3'
    __description__ = 'A bridge plugin for the Pwnstro.bot C&C dashboard to enable manual attacks and AI insight.'

    # File-based communication paths
    DEAUTH_TARGET_FILE = "/tmp/pwn_deauth_target.txt"
    ASSOC_TARGET_FILE = "/tmp/pwn_assoc_target.txt"
    AI_PARAMS_FILE = "/tmp/pwn_ai_params.json"
    EPOCH_LOG_FILE = "/tmp/pwn_epoch_history.log"
    MAX_EPOCH_LOG_LINES = 20

    def __init__(self):
        super(PwnstroBridge, self).__init__()
        self.epoch_history = deque(maxlen=self.MAX_EPOCH_LOG_LINES)
        logging.info("[PwnstroBridge] Plugin loaded.")
        # Load existing history if any
        self._load_history()

    def _load_history(self):
        if os.path.exists(self.EPOCH_LOG_FILE):
            with open(self.EPOCH_LOG_FILE, 'r') as f:
                for line in f:
                    self.epoch_history.append(line.strip())

    def _save_history(self):
        with open(self.EPOCH_LOG_FILE, 'w') as f:
            for entry in self.epoch_history:
                f.write(f"{entry}\n")

    def on_ai_epoch_step(self, agent, epoch, reward):
        """
        Called after the AI has completed a training epoch.
        """
        logging.info(f"[PwnstroBridge] AI epoch {epoch} complete. Reward: {reward}")
        
        # Get the current AI parameters
        params = agent.config()['ai']['params']
        
        epoch_data = {
            "epoch": epoch,
            "reward": round(reward, 4),
            "params": {
                "recon_hop_time": params.get('recon_hop_time'),
                "assoc_timeout": params.get('assoc_timeout'),
                "recon_time": params.get('recon_time')
            }
        }
        
        # Append to our history and save
        self.epoch_history.append(json.dumps(epoch_data))
        self._save_history()

    def on_ui_update(self, ui: view.View):
        """
        Called every time the UI is updated.
        We'll check for command files here.
        """
        # --- Check for Manual Attacks ---
        if os.path.exists(self.DEAUTH_TARGET_FILE):
            with open(self.DEAUTH_TARGET_FILE, 'r') as f:
                bssid = f.read().strip()
            logging.info(f"[PwnstroBridge] Received manual deauth command for {bssid}")
            ui.set('status', f'Deauthing {bssid}...')
            ui.agent.deauth(bssid)
            os.remove(self.DEAUTH_TARGET_FILE)
            ui.update(force=True)

        if os.path.exists(self.ASSOC_TARGET_FILE):
            with open(self.ASSOC_TARGET_FILE, 'r') as f:
                bssid = f.read().strip()
            target_ap = next((ap for ap in ui.get('aps') if ap['bssid'] == bssid), None)
            if target_ap:
                logging.info(f"[PwnstroBridge] Received manual association command for {target_ap['hostname']} ({bssid})")
                ui.set('status', f'Associating with {target_ap["hostname"]}...')
                ui.agent.associate(target_ap)
            else:
                logging.warning(f"[PwnstroBridge] Could not find AP with BSSID {bssid} to associate.")
            os.remove(self.ASSOC_TARGET_FILE)
            ui.update(force=True)

        # --- Check for AI Parameter Overrides ---
        if os.path.exists(self.AI_PARAMS_FILE):
            try:
                with open(self.AI_PARAMS_FILE, 'r') as f:
                    new_params = json.load(f)
                
                # Update the agent's running config
                agent = ui.agent
                agent.config()['ai']['params'].update(new_params)
                
                logging.info(f"[PwnstroBridge] Applied manual AI parameter overrides: {new_params}")
                ui.set('status', 'AI params updated!')
                os.remove(self.AI_PARAMS_FILE)
                ui.update(force=True)
            except Exception as e:
                logging.error(f"[PwnstroBridge] Error processing AI params file: {e}")
                os.remove(self.AI_PARAMS_FILE)

    def on_unload(self):
        logging.info("[PwnstroBridge] Plugin unloaded.")

