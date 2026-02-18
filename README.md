# Keyence MD-X2000 Laser Marker Communication Script

Python script for communicating with Keyence MD-X2000 laser marking system via TCP/IP Ethernet.

## Features

1. **Read Ready Status** - Check if laser marker is ready for marking
2. **Read Marking Text** - Retrieve the text marked on parts
3. **Send to API** - Transmit marking data to external API endpoint

## Installation

```bash
# Navigate to the project directory
cd keyence_mdx2000

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to configure:

```python
# Keyence Connection
KEYENCE_HOST = "192.168.0.20"  # Your laser marker IP
KEYENCE_PORT = 50002           # Default TCP port

# API Settings
API_ENDPOINT = "http://your-api.com/api/marking-data"
API_KEY = "your-api-key"       # Optional
```

## Usage

### Single Read Mode
Read marking data once and send to API:
```bash
python main.py
```

### Continuous Polling Mode
Monitor laser marker continuously:
```bash
python main.py --continuous
# or with custom interval
python main.py -c -p 2.0  # Poll every 2 seconds
```

### Test Connection
Verify connectivity to laser marker and API:
```bash
python main.py --test-connection
```

### Command Line Options
```
-c, --continuous        Run in continuous polling mode
-t, --test-connection   Test connection only
-p, --poll-interval     Polling interval in seconds
-H, --host              Override Keyence host IP
-P, --port              Override Keyence port
```

## API Data Format

The script sends JSON data to your API endpoint:

```json
{
  "timestamp": "2025-12-19T06:48:26.000Z",
  "source": "keyence_mdx2000",
  "data": {
    "status": "READY",
    "marking_text": "PART-123456",
    "job_number": 1,
    "block_number": 0,
    "error_code": null
  }
}
```

## Keyence Protocol Reference

Commands used (per Keyence MD-X2000/2500 Communication Interface Manual):

| Command | Description |
|---------|-------------|
| `RX,RS` | Request READY status |
| `RX,MS` | Request final marking string |
| `RX,ES` | Request error status |
| `RX,JN` | Request current job number |

## Files

- `main.py` - Main entry point with CLI
- `keyence_client.py` - Keyence TCP/IP communication class
- `api_client.py` - API client for sending data
- `config.py` - Configuration settings
- `requirements.txt` - Python dependencies

## Troubleshooting

1. **Connection Timeout**: Verify IP address and ensure laser marker is on the same network
2. **No Response**: Check Marking Builder Plus Ethernet settings (delimiter should be CR)
3. **API Errors**: Verify API endpoint URL and authentication settings

## License

MIT License
