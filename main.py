"""
Keyence MD-X2000 Laser Marker Communication Script.

Main entry point for communicating with Keyence MD-X2000 laser marker,
reading marking data, and sending it to an external API.

Features:
1. Read ready status from laser marker
2. Read the text that laser marker marks on the part
3. Send the marking data to external API

Usage:
    python main.py                    # Run once
    python main.py --continuous       # Run in continuous polling mode
    python main.py --test-connection  # Test connection only
"""

import argparse
import logging
import sys
import time
import signal
from datetime import datetime
from typing import Optional

import config
from keyence_client import KeyenceMDX2000, KeyenceStatus, KeyenceError, MarkingData
from api_client import APIClient, APIClientError


# Global flag for graceful shutdown
running = True


def setup_logging() -> logging.Logger:
    """Setup logging configuration."""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger = logging.getLogger(__name__)
    logger.info("Shutdown signal received. Stopping...")
    running = False


def test_connection(keyence: KeyenceMDX2000, api: APIClient, logger: logging.Logger) -> bool:
    """
    Test connections to Keyence laser marker and API.
    
    Args:
        keyence: Keyence client instance
        api: API client instance
        logger: Logger instance
        
    Returns:
        True if all connections successful
    """
    logger.info("=" * 50)
    logger.info("Testing Connections")
    logger.info("=" * 50)
    
    # Test Keyence connection
    logger.info(f"\n[1] Testing Keyence MD-X2000 connection...")
    logger.info(f"    Host: {config.KEYENCE_HOST}:{config.KEYENCE_PORT}")
    
    try:
        keyence.connect()
        status = keyence.get_ready_status()
        logger.info(f"    [OK] Connected successfully!")
        logger.info(f"    [OK] Laser marker status: {status.value}")
        
        # Try to get error status
        error = keyence.get_error_status()
        if error:
            logger.warning(f"    [!] Error status: {error}")
        else:
            logger.info(f"    [OK] No errors detected")
        
        keyence.disconnect()
        keyence_ok = True
        
    except KeyenceError as e:
        logger.error(f"    [FAILED] Connection failed: {e}")
        keyence_ok = False
    
    # Test API connection
    logger.info(f"\n[2] Testing API connection...")
    logger.info(f"    Endpoint: {config.API_ENDPOINT}")
    
    if not config.API_ENDPOINT or config.API_ENDPOINT == "http://your-api-endpoint.com/api/marking-data":
        logger.warning("    [!] API endpoint not configured")
        api_ok = False
    else:
        api_ok = api.health_check()
        if api_ok:
            logger.info(f"    [OK] API is reachable")
        else:
            logger.warning(f"    [FAILED] API is not reachable")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Connection Test Results:")
    logger.info(f"  Keyence: {'OK' if keyence_ok else 'FAILED'}")
    logger.info(f"  API: {'OK' if api_ok else 'NOT CONFIGURED/FAILED'}")
    logger.info("=" * 50)
    
    return keyence_ok


def read_and_send_once(
    keyence: KeyenceMDX2000, 
    api: APIClient, 
    logger: logging.Logger
) -> Optional[MarkingData]:
    """
    Read marking data from Keyence and send to API once.
    
    Args:
        keyence: Keyence client instance
        api: API client instance
        logger: Logger instance
        
    Returns:
        MarkingData if successful, None otherwise
    """
    try:
        # Connect to Keyence
        if not keyence.is_connected:
            keyence.connect()
        
        # Read ready status
        logger.info("Reading laser marker status...")
        status = keyence.get_ready_status()
        logger.info(f"Status: {status.value}")
        
        # Read marking data
        logger.info("Reading marking data...")
        marking_data = keyence.get_marking_data()
        
        logger.info(f"  Status: {marking_data.status.value}")
        logger.info(f"  Marking Text: '{marking_data.marking_text}'")
        logger.info(f"  Job Number: {marking_data.job_number}")
        logger.info(f"  Blocks Read: {marking_data.block_number}")
        
        # Display individual block texts if available
        if marking_data.block_texts:
            logger.info("  Block Details:")
            for block_info in marking_data.block_texts:
                logger.info(f"    Block {block_info['block']}: '{block_info['text']}'")
        
        if marking_data.error_code:
            logger.warning(f"  Error Code: {marking_data.error_code}")
        
        # New API Flow
        if config.PRODUCTION_ORDERS_API:
            logger.info("Processing scan transaction...")
            try:
                # 1. Get Production Order
                logger.info("1. Fetching current production order...")
                api_response = api.get_current_production_order()
                logger.debug(f"Production Order Response: {api_response}")
                
                # Extract first order from response data array
                orders = api_response.get("data", [])
                if not orders:
                    logger.error("No active production order found for today")
                    return marking_data
                
                prod_order = orders[0]
                logger.info(f"Using production order: {prod_order.get('orderNo', 'N/A')}")
                
                # 2. Prepare Injection Scan Payload
                scan_payload = {
                    "productionOrderNo": prod_order.get("orderNo", ""),
                    "modelCode": prod_order.get("modelCode", ""),
                    "productSerialNumber": marking_data.marking_text,
                    "partCount": 1,
                    "partStatus": "OK",
                    "createdBy": config.USER_ID,
                    "deviceName": config.DEVICE_NAME,
                    "stationName": config.STATION_NAME,
                    "deviceId": config.DEVICE_ID
                }
                
                # 3. Send to Injection Scan API
                logger.info("2. Sending injection scan data...")
                logger.debug(f"Scan Payload: {scan_payload}")
                response = api.send_injection_scan(scan_payload)
                logger.info(f"Transaction completed. API Response: {response}")
                
            except APIClientError as e:
                logger.error(f"API Transaction Error: {e}")
        elif config.API_ENDPOINT and config.API_ENDPOINT != "http://your-api-endpoint.com/api/marking-data":
            # Legacy fallback
            logger.info("Sending data to Legacy API...")
            try:
                response = api.send_marking_data(marking_data)
                logger.info(f"API Response: {response}")
            except APIClientError as e:
                logger.error(f"API Error: {e}")
        else:
            logger.warning("No API endpoints configured.")
        
        return marking_data
        
    except KeyenceError as e:
        logger.error(f"Keyence Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None



def run_continuous(
    keyence: KeyenceMDX2000, 
    api: APIClient, 
    logger: logging.Logger, 
    poll_interval: float = None
) -> None:
    """
    Run in continuous polling mode.
    
    Args:
        keyence: Keyence client instance
        api: API client instance
        logger: Logger instance
        poll_interval: Polling interval in seconds
    """
    global running
    
    interval = poll_interval or config.POLL_INTERVAL
    reconnect_attempts = 0
    last_marking_text = None
    
    logger.info("=" * 50)
    logger.info("Starting continuous monitoring mode")
    logger.info(f"Poll interval: {interval} seconds")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 50)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    while running:
        try:
            # Connect if not connected
            if not keyence.is_connected:
                logger.info("Connecting to laser marker...")
                keyence.connect()
                reconnect_attempts = 0
            
            # Read marking data
            marking_data = keyence.get_marking_data()
            
            # Log status
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(
                f"[{timestamp}] Status: {marking_data.status.value} | "
                f"Text: '{marking_data.marking_text}' | "
                f"Job: {marking_data.job_number}"
            )
            
            # Send to API only if marking text changed (new marking)
            if marking_data.marking_text and marking_data.marking_text != last_marking_text:
                last_marking_text = marking_data.marking_text
                
                logger.info(f"New marking detected: '{marking_data.marking_text}'")
                
                if config.PRODUCTION_ORDERS_API:
                    try:
                        # 1. Get Production Order
                        logger.info("Fetching production order...")
                        api_response = api.get_current_production_order()
                        
                        # Extract first order from response data array
                        orders = api_response.get("data", [])
                        if not orders:
                            logger.error("No active production order found for today")
                            continue
                        
                        prod_order = orders[0]
                        
                        # 2. Prepare Injection Scan Payload
                        scan_payload = {
                            "productionOrderNo": prod_order.get("orderNo", ""),
                            "modelCode": prod_order.get("modelCode", ""),
                            "productSerialNumber": marking_data.marking_text,
                            "partCount": 1,
                            "partStatus": "OK",
                            "createdBy": config.USER_ID,
                            "deviceName": config.DEVICE_NAME,
                            "stationName": config.STATION_NAME,
                            "deviceId": config.DEVICE_ID
                        }
                        
                        # 3. Send Scan
                        logger.info("Sending injection scan...")
                        logger.debug(f"Scan Payload: {scan_payload}")
                        response = api.send_injection_scan(scan_payload)
                        logger.info(f"Scan sent successfully. Response: {response}")
                        
                    except APIClientError as e:
                        logger.error(f"API Transaction Error: {e}")
                        
                elif config.API_ENDPOINT and config.API_ENDPOINT != "http://your-api-endpoint.com/api/marking-data":
                    try:
                        logger.info(f"Sending to legacy API...")
                        response = api.send_marking_data(marking_data)
                        logger.info(f"API Response: {response}")
                    except APIClientError as e:
                        logger.error(f"API Error: {e}")
            
            # Wait for next poll
            time.sleep(interval)
            
        except KeyenceError as e:
            logger.error(f"Keyence Error: {e}")
            keyence.disconnect()
            
            # Reconnect logic
            if config.AUTO_RECONNECT and reconnect_attempts < config.MAX_RECONNECT_ATTEMPTS:
                reconnect_attempts += 1
                logger.info(f"Attempting to reconnect ({reconnect_attempts}/{config.MAX_RECONNECT_ATTEMPTS})...")
                time.sleep(2)  # Wait before reconnecting
            else:
                logger.error("Max reconnection attempts reached. Stopping.")
                running = False
                
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(interval)
    
    # Cleanup
    keyence.disconnect()
    api.close()
    logger.info("Monitoring stopped.")


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Keyence MD-X2000 Laser Marker Communication Script"
    )
    parser.add_argument(
        '--continuous', '-c',
        action='store_true',
        help='Run in continuous polling mode'
    )
    parser.add_argument(
        '--test-connection', '-t',
        action='store_true',
        help='Test connection only'
    )
    parser.add_argument(
        '--poll-interval', '-p',
        type=float,
        default=None,
        help='Polling interval in seconds (for continuous mode)'
    )
    parser.add_argument(
        '--host', '-H',
        type=str,
        default=None,
        help='Keyence host IP address'
    )
    parser.add_argument(
        '--port', '-P',
        type=int,
        default=None,
        help='Keyence port number'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("  Keyence MD-X2000 Laser Marker Communication Script")
    logger.info("=" * 60)
    
    # Create clients
    keyence = KeyenceMDX2000(
        host=args.host or config.KEYENCE_HOST,
        port=args.port or config.KEYENCE_PORT
    )
    api = APIClient()
    
    try:
        if args.test_connection:
            # Test connection mode
            success = test_connection(keyence, api, logger)
            sys.exit(0 if success else 1)
            
        elif args.continuous:
            # Continuous polling mode
            run_continuous(keyence, api, logger, args.poll_interval)
            
        else:
            # Single read mode
            marking_data = read_and_send_once(keyence, api, logger)
            
            if marking_data:
                logger.info("\n" + "=" * 50)
                logger.info("Summary:")
                logger.info(f"  Status: {marking_data.status.value}")
                logger.info(f"  Marking Text: '{marking_data.marking_text}'")
                logger.info(f"  Job Number: {marking_data.job_number}")
                logger.info("=" * 50)
            else:
                logger.error("Failed to read marking data")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        keyence.disconnect()
        api.close()


if __name__ == "__main__":
    main()
