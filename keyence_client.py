"""
Keyence MD-X2000 Laser Marker Communication Client.

Communicates with Keyence MD-X2000/2500 series laser markers via TCP/IP.
Protocol Reference: Keyence MD-X2000/2500 Communication Interface User Manual
"""

import socket
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import config


class KeyenceStatus(Enum):
    """Laser marker status codes."""
    READY = "READY"           # 0 = Ready ON - Laser is ready
    NOT_READY = "NOT_READY"   # 1 = Ready OFF - Waiting/standby (not an error)
    BUSY = "BUSY"             # 2 = Ready OFF - Marking in progress
    ERROR = "ERROR"           # Actual error condition
    UNKNOWN = "UNKNOWN"



@dataclass
class MarkingData:
    """Data structure for marking information."""
    status: KeyenceStatus
    marking_text: str
    job_number: int
    block_number: int
    error_code: Optional[str] = None
    raw_response: Optional[str] = None
    block_texts: Optional[list] = None  # List of texts from each block



class KeyenceError(Exception):
    """Exception for Keyence communication errors."""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class KeyenceMDX2000:
    """
    Client for communicating with Keyence MD-X2000 laser marker via TCP/IP.
    
    Attributes:
        host: IP address of the laser marker controller
        port: TCP port number (default: 50002)
    """
    
    # Command terminators
    CR = "\r"  # Carriage Return - command delimiter
    
    # Command prefixes
    CMD_READ = "RX"   # Read command prefix
    CMD_WRITE = "WX"  # Write command prefix
    
    # Common commands
    CMD_READY_STATUS = "RS"      # Request READY status
    CMD_MARKING_STRING = "MS"    # Request final marking string
    CMD_ERROR_STATUS = "ES"      # Request error status
    CMD_JOB_NUMBER = "JN"        # Request current job number
    CMD_TRIGGER_MARK = "MK"      # Trigger marking
    
    def __init__(
        self, 
        host: str = None, 
        port: int = None,
        timeout: float = None,
        target_number: int = None
    ):
        """
        Initialize Keyence MD-X2000 client.
        
        Args:
            host: IP address of laser marker (default from config)
            port: TCP port number (default from config)
            timeout: Connection timeout in seconds (default from config)
            target_number: Target specifier for commands (default from config)
        """
        self.host = host or config.KEYENCE_HOST
        self.port = port or config.KEYENCE_PORT
        self.timeout = timeout or config.CONNECTION_TIMEOUT
        self.target_number = target_number if target_number is not None else config.TARGET_NUMBER
        self._socket: Optional[socket.socket] = None
        self._connected = False
        
        self.logger = logging.getLogger(__name__)
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to laser marker."""
        return self._connected and self._socket is not None
    
    def connect(self) -> bool:
        """
        Establish TCP connection to the laser marker.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            KeyenceError: If connection fails
        """
        try:
            self.logger.info(f"Connecting to Keyence MD-X2000 at {self.host}:{self.port}")
            
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            
            self._connected = True
            self.logger.info("Successfully connected to Keyence MD-X2000")
            return True
            
        except socket.timeout:
            self._connected = False
            raise KeyenceError(f"Connection timeout to {self.host}:{self.port}")
        except socket.error as e:
            self._connected = False
            raise KeyenceError(f"Socket error: {e}")
        except Exception as e:
            self._connected = False
            raise KeyenceError(f"Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Close the TCP connection to the laser marker."""
        if self._socket:
            try:
                self._socket.close()
                self.logger.info("Disconnected from Keyence MD-X2000")
            except Exception as e:
                self.logger.warning(f"Error during disconnect: {e}")
            finally:
                self._socket = None
                self._connected = False
    
    def _send_command(self, command: str) -> str:
        """
        Send a command to the laser marker and receive response.
        
        Args:
            command: Command string to send (without CR terminator)
            
        Returns:
            Response string from laser marker
            
        Raises:
            KeyenceError: If communication fails
        """
        if not self.is_connected:
            raise KeyenceError("Not connected to laser marker")
        
        try:
            # Add CR terminator and encode
            full_command = f"{command}{self.CR}"
            self._socket.send(full_command.encode('ascii'))
            self.logger.debug(f"Sent command: {command}")
            
            # Receive response
            self._socket.settimeout(config.READ_TIMEOUT)
            response = b""
            
            while True:
                chunk = self._socket.recv(1024)
                if not chunk:
                    break
                response += chunk
                # Check for CR terminator
                if response.endswith(b'\r'):
                    break
            
            decoded_response = response.decode('ascii').strip()
            self.logger.debug(f"Received response: {decoded_response}")
            return decoded_response
            
        except socket.timeout:
            raise KeyenceError("Response timeout from laser marker")
        except Exception as e:
            raise KeyenceError(f"Communication error: {e}")
    
    def _parse_response(self, response: str) -> Tuple[bool, str]:
        """
        Parse laser marker response.
        
        Args:
            response: Raw response string
            
        Returns:
            Tuple of (success: bool, data/error_code: str)
        """
        parts = response.split(',')
        
        if len(parts) >= 2:
            prefix = parts[0]
            status = parts[1]
            
            if status == "OK":
                # Successful response - return data after OK
                data = ','.join(parts[2:]) if len(parts) > 2 else ""
                return True, data
            elif status == "NG":
                # Error response
                error_code = parts[3] if len(parts) > 3 else "UNKNOWN"
                return False, error_code
        
        return True, response
    
    def get_ready_status(self) -> KeyenceStatus:
        """
        Get the READY status of the laser marker.
        
        Returns:
            KeyenceStatus enum indicating current status
            
        Raises:
            KeyenceError: If communication fails
        """
        # Simple command format works for MD-X2000
        command = "RS"
        response = self._send_command(command)
        
        # Parse response: RS,<status>,<error_code>
        parts = response.split(',')
        self.logger.debug(f"Ready status parts: {parts}")
        
        if len(parts) >= 2:
            try:
                status_code = int(parts[1])
                # Status: 0 = READY ON, 1 = READY OFF (standby), 2 = READY OFF (Marking)
                if status_code == 0:
                    return KeyenceStatus.READY
                elif status_code == 1:
                    return KeyenceStatus.NOT_READY  # Standby/waiting - not an error
                elif status_code == 2:
                    return KeyenceStatus.BUSY
                else:
                    return KeyenceStatus.UNKNOWN
            except ValueError:
                self.logger.warning(f"Unexpected status value: {parts[1]}")
                return KeyenceStatus.UNKNOWN

        
        return KeyenceStatus.UNKNOWN
    
    def get_marking_string(self, job_number: int = 0, block_number: int = 0) -> str:
        """
        Get the final marking string (text marked on the part).
        
        Args:
            job_number: Job number (0 = current job, 1-1999)
            block_number: Block number (0 = all blocks, 1-255 for specific block)
            
        Returns:
            The marking string text (combined from all blocks if block_number=0)
            
        Raises:
            KeyenceError: If communication fails
        """
        combined_text, _ = self.get_all_block_texts(job_number, block_number)
        return combined_text
    
    def get_all_block_texts(self, job_number: int = 0, block_number: int = 0) -> tuple:
        """
        Get the marking string from all blocks with individual block texts.
        
        Args:
            job_number: Job number (0 = current job, 1-1999)
            block_number: Block number (0 = all blocks, 1-255 for specific block)
            
        Returns:
            Tuple of (combined_text, list_of_block_texts)
            
        Raises:
            KeyenceError: If communication fails
        """
        job_str = str(job_number).zfill(4)
        
        if block_number == 0:
            # Read multiple blocks
            all_text = []
            
            # Determine which blocks to read based on config
            # If config.BLOCKS_TO_READ is set, use those specific blocks
            # Otherwise, use auto-detect mode (1 to 255, stop on error)
            blocks_to_scan = config.BLOCKS_TO_READ if getattr(config, 'BLOCKS_TO_READ', None) else range(1, 256)
            is_auto_detect = not bool(getattr(config, 'BLOCKS_TO_READ', None))
            
            # Retry configuration
            max_retries = getattr(config, 'MAX_READ_RETRIES', 0)
            retry_delay = getattr(config, 'RETRY_DELAY', 0.5)
            
            for block in blocks_to_scan:
                block_str = str(block).zfill(3)
                command = f"RX,MarkedCharacter={job_str},{block_str}"
                
                # Retry loop for this specific block
                for attempt in range(max_retries + 1):
                    try:
                        response = self._send_command(command)
                        
                        if response.startswith("RX,OK,"):
                            text = response[6:]  # Everything after "RX,OK,"
                            if text:  
                                all_text.append({"block": block, "text": text})
                                self.logger.debug(f"Block {block}: '{text}'")
                            elif not is_auto_detect:
                                 pass
                            # Success, break retry loop
                            break
                                 
                        elif response.startswith("RX,NG,"):
                            # Error
                            error_info = response[6:]
                            self.logger.debug(f"Block {block} error: {error_info}")
                            
                            # Check for Busy Error (S009) and retry if configured
                            if "S009" in error_info and attempt < max_retries:
                                self.logger.warning(f"Block {block} busy (S009), retrying in {retry_delay}s ({attempt+1}/{max_retries})...")
                                import time
                                time.sleep(retry_delay)
                                continue
                            
                            # In auto-detect mode, an error typically means we reached the end of valid blocks
                            if is_auto_detect:
                                if "S022" in error_info or "S029" in error_info:
                                    break
                            else:
                                # In specific block mode, just log it and continue to next configured block
                                self.logger.warning(f"Failed to read configured block {block}: {error_info}")
                            
                            # If we got here, it's a non-retryable error or retries exhausted
                            break
                            
                    except KeyenceError as e:
                        self.logger.debug(f"Block {block} exception: {e}")
                        if is_auto_detect:
                            break
                        # For specific blocks, maybe we should also retry connection errors? 
                        # For now, keeping it simple to just S009 as requested.
                        break
            
            # Validation: Ensure we read all configured blocks
            if not is_auto_detect and len(all_text) != len(blocks_to_scan):
                self.logger.warning(f"Incomplete read: Configured to read {len(blocks_to_scan)} blocks, but only got {len(all_text)}. Discarding marking data to prevent partial scans.")
                return "", []

            self.logger.info(f"Read marking text from {len(all_text)} blocks")
            # Sort by block number to ensure correct order
            all_text.sort(key=lambda x: x["block"])
            combined_text = ''.join([item["text"] for item in all_text])
            return combined_text, all_text
        
        else:
            # Read from specific block
            block_str = str(max(1, block_number)).zfill(3)
            command = f"RX,MarkedCharacter={job_str},{block_str}"
            self.logger.debug(f"Requesting marked character with command: {command}")
            response = self._send_command(command)
            
            self.logger.debug(f"MarkedCharacter response: {response}")
            
            if response.startswith("RX,OK,"):
                text = response[6:]
                return text, [{"block": block_number, "text": text}]
            elif response.startswith("RX,NG,"):
                error_info = response[6:]
                self.logger.warning(f"MarkedCharacter error: {error_info}")
                return "", []
        
        return "", []




    
    def get_error_status(self) -> Optional[str]:
        """
        Get the current error status of the laser marker.
        
        Returns:
            Error code string if there's an error, None if no error
            
        Raises:
            KeyenceError: If communication fails
        """
        # Simple command format - ES for Error Status
        command = "ES"
        response = self._send_command(command)
        
        # Parse response: ES,<error_code>
        parts = response.split(',')
        self.logger.debug(f"Error status parts: {parts}")
        
        if len(parts) >= 2:
            error_code = parts[1]
            # Check if no error (empty or specific no-error code)
            if error_code == "" or error_code == "0":
                return None
            return error_code
        
        return None
    
    def get_current_job_number(self) -> int:
        """
        Get the current job number.
        
        Returns:
            Current job number
            
        Raises:
            KeyenceError: If communication fails
        """
        # Simple command format - JN for Job Number
        command = "JN"
        response = self._send_command(command)
        
        # Parse response: JN,<job_number>
        parts = response.split(',')
        self.logger.debug(f"Job number parts: {parts}")
        
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                self.logger.warning(f"Unexpected job number value: {parts[1]}")
                return 0
        
        return 0
    
    def trigger_marking(self) -> bool:
        """
        Trigger a marking operation.
        
        Returns:
            True if marking triggered successfully
            
        Raises:
            KeyenceError: If communication fails
        """
        # Command format: WX,<target>,MK
        command = f"{self.CMD_WRITE},{self.target_number},{self.CMD_TRIGGER_MARK}"
        response = self._send_command(command)
        
        success, data = self._parse_response(response)
        
        if not success:
            raise KeyenceError(f"Failed to trigger marking: {data}", error_code=data)
        
        return True
    
    def get_marking_data(self) -> MarkingData:
        """
        Get comprehensive marking data including status and text.
        
        Returns:
            MarkingData object with all marking information
        """
        status = self.get_ready_status()
        error_code = self.get_error_status()
        
        marking_text = ""
        job_number = 0
        block_texts = []
        
        try:
            # Always try to get marking text - it contains the LAST marked data
            # regardless of current ready status
            # Get all blocks (block_number=0)
            marking_text, block_texts = self.get_all_block_texts(job_number=0, block_number=0)
            job_number = self.get_current_job_number()
        except KeyenceError as e:
            self.logger.warning(f"Could not retrieve marking data: {e}")
        
        return MarkingData(
            status=status,
            marking_text=marking_text,
            job_number=job_number,
            block_number=len(block_texts),  # Number of blocks read
            error_code=error_code,
            block_texts=block_texts
        )

    
    def __enter__(self):

        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
