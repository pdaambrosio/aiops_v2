from typing import Any
from langchain_core.tools import StructuredTool
from pydantic import Field, create_model

from config import ALLOWED_COMMANDS
from core import execute, mount_command, summarize_result
from utils import get_logger

logger = get_logger(__name__)


def execute_tool_command(name: str, parameter: dict[str, Any] | None = None) -> dict:
    """Execute tool command"""
    command_config = ALLOWED_COMMANDS[name]
    command = mount_command(name, parameter)
    result = execute(command, timeout=command_config.get("timeout"))
    summarize = summarize_result(result)
    summarize["comando"] = command
    summarize["tool"] = name
    return summarize


def _format_to_llm(summarize: dict) -> str:
    """Format the tool text to LLM"""
    parts = [f"$ {summarize['comando']}", summarize["text"] or "(sem saída)"]
    if summarize["alerts"]:
        parts.append(f"[alertas detectados: {', '.join(summarize['alerts'])}]")

    return "\n".join(parts)


def _create_tool(name: str, config: dict) -> StructuredTool:
    """Create a structured tool to commands in the whitelist"""
    requires_parameters = config.get("requer_parametro")

    if requires_parameters:
        args_schema = create_model(
            f"{name}_args",
            **{requires_parameters: (
                str,
                Field(
                    description=f"Valor de '{requires_parameters}' para: {config['descricao']}"
                )
            )}
        )

        def _func(**kwargs: Any) -> str:
            return _format_to_llm(execute_tool_command(name, kwargs))
    else:
        args_schema = None
        def _func() -> str:
            return _format_to_llm(execute_tool_command(name, {}))

    description = f"{config['descricao']} (categoria: {config['categoria']})"

    return StructuredTool.from_function(
        func=_func,
        name=name,
        description=description,
        args_schema=args_schema
    )


def build_tools() -> list[StructuredTool]:
    """Generate a tool list based on ALLOWED_COMMANDS"""
    tools = [_create_tool(name, config) for name, config in ALLOWED_COMMANDS.items()]
    logger.info(f"Geradas {len(tools)} tools dinâmicas da whitelist.")
    return tools

# local tests
import json

## without parameter
print(f"\n WITHOUT PARAMETER")
result_execute_tool_command = execute_tool_command('memoria_livre')
test_without_create_tool = _create_tool('memoria_livre', ALLOWED_COMMANDS['memoria_livre'])
# print(json.dumps(result_execute_tool_command, indent=2, ensure_ascii=False))
# print(_format_to_llm(result_execute_tool_command))
print(test_without_create_tool.name)
print(test_without_create_tool.description)
print(test_without_create_tool.args)
print(test_without_create_tool.args_schema)

## with parameter
print(f"\n WITH PARAMETER")
parameter_result_execute_tool_command = execute_tool_command('curl_test', {'url':'https://www.google.com'})
test_with_create_tool = _create_tool('curl_test', ALLOWED_COMMANDS['curl_test'])
# print(json.dumps(parameter_result_execute_tool_command, indent=2, ensure_ascii=False))
# print(_format_to_llm(parameter_result_execute_tool_command))
print(test_with_create_tool.name)
print(test_with_create_tool.description)
print(test_with_create_tool.args)
print(test_with_create_tool.args_schema)

## with error
print(f"\n WITH ERROR")
error_execute_tool_command = execute_tool_command('status_nginx')
test_error_create_tool = _create_tool('status_nginx', ALLOWED_COMMANDS['status_nginx'])
# print(_format_to_llm(error_execute_tool_command))
print(test_error_create_tool.name)
print(test_error_create_tool.description)
print(test_error_create_tool.args)
print(test_error_create_tool.args_schema)