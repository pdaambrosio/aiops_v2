import subprocess

from config import COMMAND_TIMEOUT, MAX_ERROR_LENGTH, MAX_OUTPUT_LENGTH
from utils import get_logger

logger = get_logger(__name__)


def execute (command: str, timeout: int | None = None) -> dict:
    """Executes a command and returns the output"""
    timeout = timeout or COMMAND_TIMEOUT
    logger.info(f"Executing command: {command} (timeout: {timeout}s)")

    try:
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out: {command} (timeout: {timeout}s)")
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": f"Command timed out: {timeout}s)"
        }
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": f"Command failed: {e}"
        }

    stdout = (process.stdout or "")[:MAX_OUTPUT_LENGTH]
    stderr = (process.stderr or "")[:MAX_ERROR_LENGTH]

    return {
        "success": process.returncode == 0,
        "returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "error": None
    }
