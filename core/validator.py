import shlex

from config import ALLOWED_COMMANDS
from utils import get_logger

logger = get_logger(__name__)

DANGEROUS_CHARACTERS = [
    ";", "&", "|", "`", "$", "(", ")", "<", ">",
    "\n", "\r", "{", "}", "[", "]", "!", "\\", "'", '"',
]


class ValidationError(Exception):
    """Exception raised when a validation error occurs"""


def validate_tool_name(name: str) -> dict:
    """Validates a tool name"""
    command_config = ALLOWED_COMMANDS.get(name)
    if command_config is None:
        raise ValidationError(
            f"Comando '{name}' não está na whitelist ALLOWED_COMMANDS"
        )

    return command_config


def validate_parameters(parameter: str) -> str:
    """Validates a parameters"""
    if parameter is None or str(parameter).strip() == "":
        raise ValidationError("Parâmetro obrigatório está vazio.")

    parameter = str(parameter).strip()

    validade_dangerous_characters = [caracter for caracter in DANGEROUS_CHARACTERS if caracter in parameter]
    if validade_dangerous_characters:
        raise ValidationError(
            f"Parâmetro '{parameter}' contém caracteres não permitidos: {validade_dangerous_characters}"
        )

    return shlex.quote(parameter)


def mount_command(name: str, parameter: dict | None = None) -> str:
    """Mounts a command"""
    command_config = validate_tool_name(name)
    template = command_config["comando"]
    parameter = parameter or {}

    requires_parameter = command_config.get("requer_parametro")
    if requires_parameter:
        value = parameter.get(requires_parameter)
        security = validate_parameters(value)
        command = template.replace("{" + requires_parameter + "}", security)
    else:
        command = template

    if "{" in command and "}" in command:
        raise ValidationError(
            f"Comando '{name}' ainda tem placeholder não preenchido: {command!r}"
        )

    logger.debug(f"Comando montado para {name}: {command}")
    return command


# local test
if "__main__" == __name__:
    url = "https://google.com"
    print(mount_command("curl_test", {"url": "https://google.com; rm -rf /"}))
