import os

LOG_FORMAT = "{asctime} [{levelname}] {message}"
API_HOST = os.getenv("SIGNAL_SERVICE_HOST", "signal-cli")
API_PORT = os.getenv("SIGNAL_SERVICE_PORT", "8080")
DEVICE_NAME = os.getenv("DEVICE_NAME", "SignalBot")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "+18122433247")  # Replace with your number
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "signaltrader_db")
DB_USER = os.getenv("DB_USER", "signaltrader")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_secure_password")  # Replace with your password