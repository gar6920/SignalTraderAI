import os
from pathlib import Path

# Logging configuration for use in main.py
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# Docker image and container settings for Signal CLI REST API
DOCKER_IMAGE = "bbernhard/signal-cli-rest-api:latest"  # Use the latest image to avoid known issues
CONTAINER_NAME = "signal-cli-rest-api"                # Container name

# Signal CLI REST API connectivity settings
API_PORT = os.getenv("SIGNAL_SERVICE_PORT", "8080")
API_HOST = os.getenv("SIGNAL_SERVICE_HOST", "localhost")
API_HOST_FALLBACK = "127.0.0.1"  # Fallback if 'localhost' fails

# Directory for persisting Signal CLI configuration data
CONFIG_VOLUME = os.getenv("SIGNAL_CLI_CONFIG_DIR", str(Path.home() / ".local" / "share" / "signal-api"))

# Device name for linking (appears in your Signal app's linked devices)
DEVICE_NAME = os.getenv("DEVICE_NAME", "local")

# (Optional) Phone number for your Signal account (in international format)
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "+18122433247")  # Set your number here
