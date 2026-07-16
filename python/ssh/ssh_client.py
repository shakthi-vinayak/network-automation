"""SSH Client - Network device SSH connectivity with retry and error handling.

Provides a robust SSH client for network automation with support for multiple
vendor platforms, automatic retry, connection pooling, and structured output.

Example:
    >>> from python.ssh import SSHClient
    >>> client = SSHClient(host="10.0.1.1", username="admin", password="secret")
    >>> result = client.run_command("show version")
    >>> print(result.output)
    >>> client.close()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class SSHConnectionError(Exception):
    """Raised when SSH connection fails."""

    pass


class SSHCommandError(Exception):
    """Raised when SSH command execution fails."""

    pass


@dataclass
class SSHCommandResult:
    """Result of an SSH command execution.

    Attributes:
        command: The command that was executed.
        output: Raw output string from the device.
        exit_code: Command exit code (0 for success).
        duration: Execution duration in seconds.
        success: Whether the command succeeded.
    """

    command: str
    output: str
    exit_code: int = 0
    duration: float = 0.0
    success: bool = True
    error: str | None = None


# Map vendor/platform to Netmiko device_type
VENDOR_DEVICE_TYPE_MAP = {
    ("cisco", "ios"): "cisco_ios",
    ("cisco", "ios-xe"): "cisco_xe",
    ("cisco", "ios-xr"): "cisco_xr",
    ("cisco", "nx-os"): "cisco_nxos",
    ("juniper", "junos"): "juniper_junos",
    ("juniper", "srx"): "juniper_junos",
    ("arista", "eos"): "arista_eos",
    ("paloalto", "panos"): "paloalto_panos",
    ("fortinet", "fortios"): "fortinet",
    ("f5", "bigip"): "f5_linux",
    ("checkpoint", "gaia"): "checkpoint_gaia",
}


class SSHClient:
    """SSH client for network device connectivity.

    Provides a high-level interface for SSH connections to network devices
    with automatic device type detection, retry logic, and structured output.

    Attributes:
        host: Device IP address or hostname.
        username: SSH username.
        password: SSH password (prefer vault-managed credentials).
        port: SSH port number.
        vendor: Device vendor name.
        platform: Device platform name.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        vendor: str = "cisco",
        platform: str = "ios-xe",
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """Initialize SSHClient.

        Args:
            host: Device IP address or hostname.
            username: SSH username.
            password: SSH password.
            port: SSH port number.
            vendor: Device vendor (cisco, juniper, arista, etc.).
            platform: Device platform (ios-xe, nx-os, eos, etc.).
            timeout: Connection timeout in seconds.
            max_retries: Maximum number of connection retries.
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.vendor = vendor
        self.platform = platform
        self.timeout = timeout
        self.max_retries = max_retries
        self._connection: Any = None

    def _get_device_type(self) -> str:
        """Determine Netmiko device type from vendor and platform.

        Returns:
            Netmiko device type string.
        """
        key = (self.vendor.lower(), self.platform.lower())
        return VENDOR_DEVICE_TYPE_MAP.get(key, "autodetect")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((NetmikoTimeoutException, ConnectionError)),
        reraise=True,
    )
    def connect(self) -> None:
        """Establish SSH connection to the device.

        Raises:
            SSHConnectionError: If connection fails after all retries.
        """
        try:
            device_type = self._get_device_type()
            logger.info(f"Connecting to {self.host}:{self.port} (type={device_type})")

            self._connection = ConnectHandler(
                device_type=device_type,
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
            )
            logger.info(f"Connected to {self.host}")

        except NetmikoAuthenticationException as e:
            logger.error(f"Authentication failed for {self.host}: {e}")
            raise SSHConnectionError(f"Authentication failed: {e}") from e
        except NetmikoTimeoutException as e:
            logger.error(f"Connection timeout for {self.host}: {e}")
            raise SSHConnectionError(f"Connection timeout: {e}") from e
        except Exception as e:
            logger.error(f"Connection failed for {self.host}: {e}")
            raise SSHConnectionError(f"Connection failed: {e}") from e

    def run_command(self, command: str, strip_prompt: bool = True) -> SSHCommandResult:
        """Execute a command on the device.

        Args:
            command: Command to execute.
            strip_prompt: Whether to strip the device prompt from output.

        Returns:
            SSHCommandResult with command output.

        Raises:
            SSHConnectionError: If not connected.
            SSHCommandError: If command execution fails.
        """
        if not self._connection:
            raise SSHConnectionError("Not connected. Call connect() first.")

        try:
            logger.debug(f"Executing on {self.host}: {command}")
            output = self._connection.send_command(
                command, strip_prompt=strip_prompt
            )
            return SSHCommandResult(
                command=command,
                output=output,
                exit_code=0,
                success=True,
            )
        except Exception as e:
            logger.error(f"Command failed on {self.host}: {e}")
            return SSHCommandResult(
                command=command,
                output="",
                exit_code=1,
                success=False,
                error=str(e),
            )

    def run_commands(self, commands: list[str]) -> list[SSHCommandResult]:
        """Execute multiple commands on the device.

        Args:
            commands: List of commands to execute.

        Returns:
            List of SSHCommandResult objects.
        """
        return [self.run_command(cmd) for cmd in commands]

    def configure(self, commands: list[str]) -> SSHCommandResult:
        """Enter configuration mode and apply commands.

        Args:
            commands: List of configuration commands.

        Returns:
            SSHCommandResult with configuration output.
        """
        if not self._connection:
            raise SSHConnectionError("Not connected. Call connect() first.")

        try:
            output = self._connection.send_config_set(commands)
            return SSHCommandResult(
                command="config_set",
                output=output,
                exit_code=0,
                success=True,
            )
        except Exception as e:
            logger.error(f"Configuration failed on {self.host}: {e}")
            return SSHCommandResult(
                command="config_set",
                output="",
                exit_code=1,
                success=False,
                error=str(e),
            )

    def save_config(self) -> SSHCommandResult:
        """Save running configuration to startup.

        Returns:
            SSHCommandResult with save output.
        """
        if not self._connection:
            raise SSHConnectionError("Not connected.")

        try:
            output = self._connection.save_config()
            return SSHCommandResult(
                command="save_config",
                output=output,
                exit_code=0,
                success=True,
            )
        except Exception as e:
            return SSHCommandResult(
                command="save_config",
                output="",
                exit_code=1,
                success=False,
                error=str(e),
            )

    def get_running_config(self) -> str:
        """Get the device running configuration.

        Returns:
            Running configuration as string.
        """
        result = self.run_command("show running-config")
        return result.output if result.success else ""

    @property
    def is_connected(self) -> bool:
        """Check if SSH connection is active."""
        if self._connection is None:
            return False
        try:
            return self._connection.remote_conn.transport.is_active()
        except Exception:
            return False

    def close(self) -> None:
        """Close the SSH connection."""
        if self._connection:
            try:
                self._connection.disconnect()
                logger.info(f"Disconnected from {self.host}")
            except Exception as e:
                logger.warning(f"Error disconnecting from {self.host}: {e}")
            finally:
                self._connection = None

    def __enter__(self) -> "SSHClient":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
