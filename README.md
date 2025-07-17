# Pwnagotchi C&C Dashboard

A real-time, production-grade dashboard for monitoring and controlling your Pwnagotchi.

## Features

- **Live Data:** Real-time updates for status, peers, handshakes, and logs via WebSockets.
- **Remote Control:** Restart the Pwnagotchi service, toggle AI mode, and shut down the device from the web UI.
- **Plugin Management:** Enable and disable plugins on the fly.
- **Configuration Editor:** Edit your `config.toml` directly from the dashboard.
- **Handshake Management:** Download captured handshakes.

## Production-Readiness Checklist

| Category                     | Status | Notes                                                                                             |
| ---------------------------- | :----: | ------------------------------------------------------------------------------------------------- |
| **BACKEND: FastAPI**         |   ✅   | All endpoints are functional and return live data from the Pwnagotchi's local API.                |
|                              |   ✅   | Input validation and error handling are implemented for all routes.                               |
|                              |   ✅   | Endpoints match the real Pwnagotchi JSON schema.                                                  |
|                              |   ✅   | No commented-out, unfinished, or placeholder logic exists.                                        |
|                              |   ✅   | Live connection to the device via the local API.                                                  |
| **FRONTEND (HTML/CSS/JS)**   |   ✅   | Live data binding is implemented using WebSockets.                                                |
|                              |   ✅   | Real-time updates for peers, handshakes, and logs are displayed.                                  |
|                              |   ✅   | The dashboard dynamically displays the device status, mode, and configuration.                    |
|                              |   ✅   | Functional buttons for rebooting, switching modes, etc., are implemented.                         |
|                              |   ✅   | No hardcoded placeholder values or fake data are used.                                            |
| **WEBSOCKET + TELEMETRY**    |   ✅   | The backend emits correctly structured WebSocket messages from live data.                         |
|                              |   ✅   | The frontend listens and reacts to WebSocket messages in real time.                               |
|                              |   ✅   | Reconnection logic for dropped WebSocket connections is implemented.                              |
|                              |   ✅   | Message schemas are consistent with the actual device output.                                     |
| **INTEGRATION + DEPLOYMENT** |   ✅   | A `requirements.txt` file is provided.                                                            |
|                              |   ✅   | The `main.py` entry point serves both the API and the static frontend.                            |
|                              |   ✅   | Clear startup instructions are provided for direct Linux execution.                               |
|                              |   ✅   | An optional `systemd` unit file is provided for auto-starting the dashboard.                      |
| **SECURITY & PERFORMANCE**   |   ⚠️   | No rate limiting or abuse protection is implemented. This is a potential area for improvement.      |
|                              |   ⚠️   | No authentication is implemented. The dashboard should only be exposed to trusted networks.       |
|                              |   ✅   | Input is sanitized for the configuration editor.                                                  |
|                              |   ✅   | The application is lightweight and performant enough for a Raspberry Pi Zero.                     |

## Deployment Instructions

### Prerequisites

- A Pwnagotchi running on a Raspberry Pi or other Linux device.
- Python 3.7+

### 1. Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd pwnagotchi-cc-dashboard
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

### 2. Running the Dashboard

To run the dashboard, simply execute the `main.py` script:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

The dashboard will be available at `http://<your-pwnagotchi-ip>:8080`.

### 3. Auto-starting with `systemd` (Optional)

To automatically start the dashboard on boot, you can create a `systemd` service.

1.  **Create a service file:**
    ```bash
    sudo nano /etc/systemd/system/pwnagotchi-dashboard.service
    ```

2.  **Add the following content to the file, replacing `<path-to-your-project>` with the absolute path to the project directory:**

    ```ini
    [Unit]
    Description=Pwnagotchi C&C Dashboard
    After=network.target

    [Service]
    User=pi
    Group=pi
    WorkingDirectory=<path-to-your-project>
    ExecStart=<path-to-your-project>/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Enable and start the service:**
    ```bash
    sudo systemctl enable pwnagotchi-dashboard
    sudo systemctl start pwnagotchi-dashboard
    ```

You can check the status of the service with `sudo systemctl status pwnagotchi-dashboard`.
