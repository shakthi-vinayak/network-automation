"""SSH connectivity module.

Provides SSH abstraction over Netmiko/Paramiko with retry and error handling.
"""

from .ssh_client import SSHClient, SSHConnectionError, SSHCommandResult

__all__ = ["SSHClient", "SSHConnectionError", "SSHCommandResult"]
