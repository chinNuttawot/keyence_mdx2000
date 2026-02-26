"""
Configuration settings for Keyence MD-X2000 Laser Marker Communication.

Update these settings according to your environment.
"""

# Keyence MD-X2000 Connection Settings
KEYENCE_HOST = "192.168.1.9"  # IP address of the laser marker controller
KEYENCE_PORT = 50002           # Default TCP port for MD-X2000
CONNECTION_TIMEOUT = 10        # Connection timeout in seconds
READ_TIMEOUT = 5               # Read timeout in seconds

# API Configuration
API_ENDPOINT = "http://your-api-endpoint.com/api/marking-data"  # Legacy/Default
PRODUCTION_ORDERS_API = "http://192.168.1.100:3000/api/production-orders/"
INJECTION_SCAN_API = "http://192.168.1.100:3000/api/injection/scan"
API_KEY = ""                   # Optional: API key for authentication
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEsImVtYWlsIjoiYWRtaW4iLCJpYXQiOjE3NzIxMDA4MjZ9.VNLNRe2PJlMnGqi4A_6spKMvHi7Q4trEcWM1rFnKZ3s"                # Device JWT token (generated from BE scripts/generate-device-token.ts)
API_TIMEOUT = 30               # API request timeout in seconds

# Device Configuration (for API Payloads)
DEVICE_NAME = "injection_1"
STATION_NAME = "injection"
DEVICE_ID = 4
USER_ID = 1                    # Default user ID for createdBy field

# Polling Configuration
POLL_INTERVAL = 1.0            # Polling interval in seconds
AUTO_RECONNECT = True          # Auto-reconnect on connection loss
MAX_RECONNECT_ATTEMPTS = 5000     # Maximum reconnection attempts

# Command Configuration
TARGET_NUMBER = 0              # Target specifier for commands (0 = first target)

# Block Reading Configuration
# Specify which blocks to read from the laser marker
# Examples:
#   BLOCKS_TO_READ = [1, 2, 3]       # Read specific blocks 1, 2, and 3
#   BLOCKS_TO_READ = [1]             # Read only block 1
#   BLOCKS_TO_READ = []              # Read ALL blocks (auto-detect)
#   BLOCKS_TO_READ = list(range(1, 6))  # Read blocks 1 to 5
BLOCKS_TO_READ = [1, 2]                # Empty list = read all available blocks
MAX_READ_RETRIES = 10            # Max retries when laser is busy (S009)
RETRY_DELAY = 0.5               # Delay in seconds between retries

# Logging Configuration

LOG_LEVEL = "INFO"             # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "keyence_mdx2000.log"





