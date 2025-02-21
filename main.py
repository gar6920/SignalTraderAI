import sys
import logging
import time
import subprocess
import requests

import config

# Warn if running on Python 3.13 (which may be less stable)
if sys.version_info.major == 3 and sys.version_info.minor == 13:
    logging.warning("Detected Python 3.13, which may be unstable. Proceed with caution and consider using a stable Python release.")

# Configure logging
logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("SignalBotSetup")

# Prepare base URLs for Signal CLI REST API
base_url = f"http://{config.API_HOST}:{config.API_PORT}"
fallback_url = f"http://{config.API_HOST_FALLBACK}:{config.API_PORT}"

api_info = {}
connected = False

# Try connecting to the Signal CLI REST API (primary host)
try:
    logger.info(f"Attempting to contact Signal CLI REST API at {base_url}/v1/about")
    resp = requests.get(f"{base_url}/v1/about", timeout=5)
    if resp.ok:
        api_info = resp.json()
        connected = True
        logger.info(f"Connected to Signal CLI REST API at {base_url}")
    else:
        api_info = resp.json() if resp.headers.get('Content-Type','').startswith('application/json') else {}
except Exception as e:
    logger.warning(f"Could not reach Signal CLI REST API at {base_url} ({e}). Trying fallback {fallback_url}...")
    try:
        resp = requests.get(f"{fallback_url}/v1/about", timeout=5)
        if resp.ok:
            api_info = resp.json()
            base_url = fallback_url  # switch to fallback
            connected = True
            logger.info(f"Connected to Signal CLI REST API at {fallback_url}")
        else:
            api_info = resp.json() if resp.headers.get('Content-Type','').startswith('application/json') else {}
    except Exception as e2:
        logger.error(f"Failed to connect to Signal CLI REST API at both 'localhost' and '127.0.0.1'. Error: {e2}")
        logger.info("Attempting to start the Signal CLI REST API Docker container in normal mode...")
        try:
            subprocess.run(
                [
                    "docker", "run", "-d", "--name", config.CONTAINER_NAME, "--restart=always",
                    "-p", f"{config.API_PORT}:8080",
                    "-v", f"{config.CONFIG_VOLUME}:/home/.local/share/signal-cli",
                    "-e", "MODE=normal",
                    config.DOCKER_IMAGE
                ],
                check=True, capture_output=True
            )
            logger.info("Signal CLI REST API container started in 'normal' mode.")
        except subprocess.CalledProcessError as docker_err:
            logger.error(f"Failed to start container. Ensure Docker is running and you have proper permissions. Error: {docker_err.stderr.decode().strip()}")
            sys.exit(1)
        # Wait for the container to become available
        for attempt in range(1, 6):
            try:
                time.sleep(3)
                logger.info(f"Checking API availability (attempt {attempt})...")
                resp = requests.get(f"{base_url}/v1/about", timeout=5)
                if resp.ok:
                    api_info = resp.json()
                    connected = True
                    logger.info("Signal CLI REST API is now reachable after starting the container.")
                    break
            except Exception as e3:
                logger.debug(f"Attempt {attempt} failed: {e3}")
        if not connected:
            logger.error("Signal CLI REST API did not respond after starting the container. Exiting setup.")
            sys.exit(1)

# If connected, check API mode and version
if connected and api_info:
    mode = api_info.get("mode")
    if mode:
        logger.info(f"Signal CLI REST API mode: {mode}")
        if str(mode).lower() == "json-rpc":
            logger.error("API is running in 'json-rpc' mode. Please restart in normal mode for linking.")
            sys.exit(1)
    version = api_info.get("version")
    if version:
        logger.info(f"Signal CLI REST API version: {version}")
        try:
            ver_parts = version.split(".")
            ver_tuple = tuple(int(x) for x in ver_parts if x.isdigit())
        except Exception as parse_err:
            ver_tuple = ()
            logger.debug(f"Unable to parse API version '{version}': {parse_err}")
        if ver_tuple and ver_tuple < (0, 88):
            logger.warning(f"API version {version} may be outdated. Please upgrade to avoid potential QR code issues.")

# Request a linking QR code
link_url = f"{base_url}/v1/qrcodelink?device_name={config.DEVICE_NAME}"
logger.info(f"Requesting linking QR code from {link_url}")
try:
    resp = requests.get(link_url, timeout=10)
except Exception as e:
    logger.error(f"Error connecting to {link_url}: {e}")
    sys.exit(1)

if resp.status_code != 200:
    error_detail = ""
    try:
        error_json = resp.json()
        if isinstance(error_json, dict) and "error" in error_json:
            error_detail = error_json["error"]
    except ValueError:
        error_detail = resp.text
    if error_detail:
        logger.error(f"Failed to generate QR code: {error_detail}")
    else:
        logger.error(f"Failed to generate QR code. HTTP status: {resp.status_code}")
    sys.exit(1)

logger.info("Successfully obtained QR code for linking.")
logger.info(f"Open {link_url} in your browser to scan the QR code with your Signal app.")
print(f"Please open the following URL in your browser to link your Signal device:\n{link_url}\n")
print("After scanning the QR code with your phone, press Enter to continue...")
input()

logger.info("QR code scanned. The Signal bot should now be linked to your account.")
logger.info("Restarting container in 'json-rpc' mode for normal bot operation...")

# Automatically restart the container in JSON-RPC mode
try:
    subprocess.run(["docker", "rm", "-f", config.CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", config.CONTAINER_NAME, "-p", f"{config.API_PORT}:8080",
            "-v", f"{config.CONFIG_VOLUME}:/home/.local/share/signal-cli",
            "-e", "MODE=json-rpc",
            config.DOCKER_IMAGE
        ],
        check=True, capture_output=True
    )
    logger.info("Container restarted in 'json-rpc' mode.")
except subprocess.CalledProcessError as e:
    logger.error(f"Failed to restart container in json-rpc mode: {e.stderr.decode().strip()}")
    sys.exit(1)

# Wait for the container to be ready in json-rpc mode
for attempt in range(1, 6):
    try:
        time.sleep(3)
        logger.info(f"Checking API availability in json-rpc mode (attempt {attempt})...")
        resp = requests.get(f"{base_url}/v1/about", timeout=5)
        if resp.ok:
            api_info = resp.json()
            logger.info("Signal CLI REST API is now running in json-rpc mode.")
            break
    except Exception as e:
        logger.debug(f"Attempt {attempt} in json-rpc mode failed: {e}")

# Now start the SignalBot instance with a simple Ping→Pong command
from signalbot import SignalBot, Command, Context

# Build service address from API_HOST and API_PORT
service = f"{config.API_HOST}:{config.API_PORT}"
number = config.PHONE_NUMBER  # Your phone number from config
bot = SignalBot({
    "signal_service": service,
    "phone_number": number
})
logger.info("SignalBot instance created with service %s and phone %s", service, number)

class PingCommand(Command):
    async def handle(self, c: Context):
        if c.message.text == "Ping":
            await c.send("Pong")

bot.register(PingCommand())
logger.info("PingCommand registered. Starting SignalBot...")

# Start the bot (this call blocks)
bot.start()
logger.info("SignalBot is now running. Send a 'Ping' message to test responsiveness.")
