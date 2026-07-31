import pytest

from core.validator import (
    ValidationError,
    mount_command,
    validate_parameters,
    validate_tool_name,
)


def test_validate_tool_name_existente_retorna_config():
    config = validate_tool_name("memoria_livre")
    assert config["comando"] == "free -h"
    assert config["seguranca"] == "alta"


def test_validate_tool_name_inexistente_levanta_erro():
    with pytest.raises(ValidationError):
        validate_tool_name("comando_que_nao_existe")


def test_validate_tool_name_nao_aceita_comando_shell_direto():
    with pytest.raises(ValidationError):
        validate_tool_name("free -h")


def test_validate_parameters_valor_simples_ok():
    assert validate_parameters("nginx") == "nginx"


def test_validate_parameters_vazio_levanta_erro():
    with pytest.raises(ValidationError):
        validate_parameters("")


def test_validate_parameters_none_levanta_erro():
    with pytest.raises(ValidationError):
        validate_parameters(None)


def test_validate_parameters_so_espacos_levanta_erro():
    with pytest.raises(ValidationError):
        validate_parameters("   ")


def test_validate_parameters_strip_espacos_nas_bordas():
    assert validate_parameters("  nginx  ") == "nginx"


@pytest.mark.parametrize("payload", [
    "nginx; rm -rf /",
    "nginx && echo pwned",
    "nginx | cat /etc/passwd",
    "`whoami`",
    "$(whoami)",
    "container{1}",
    "container[0]",
    "a\\b",
])
def test_validate_parameters_bloqueia_caracteres_perigosos(payload):
    with pytest.raises(ValidationError):
        validate_parameters(payload)


def test_validate_parameters_permite_espaco_interno():
    resultado = validate_parameters("meu container")
    assert resultado == "'meu container'"


def test_validate_parameters_aceita_numero_convertendo_para_string():
    assert validate_parameters(8080) == "8080"


def test_mount_command_sem_parametro():
    comando = mount_command("memoria_livre")
    assert comando == "free -h"


def test_mount_command_com_parametro_valido():
    comando = mount_command("docker_logs", {"container": "nginx"})
    assert comando == "docker logs --tail=50 nginx"


def test_mount_command_com_parametro_contendo_espaco():
    comando = mount_command("docker_logs", {"container": "meu app"})
    assert comando == "docker logs --tail=50 'meu app'"


def test_mount_command_tool_inexistente_levanta_erro():
    with pytest.raises(ValidationError):
        mount_command("comando_que_nao_existe")


def test_mount_command_parametro_faltando_levanta_erro():
    with pytest.raises(ValidationError):
        mount_command("docker_logs")


def test_mount_command_parametro_com_injecao_e_bloqueado():
    with pytest.raises(ValidationError):
        mount_command("ping", {"host": "8.8.8.8; rm -rf /"})


def test_mount_command_string_no_lugar_de_dict_falha():
    with pytest.raises(AttributeError):
        mount_command("curl_test", "https://google.com")


def test_mount_command_forma_correta_de_passar_parametro():
    comando = mount_command("curl_test", {"url": "https://google.com"})
    assert "https://google.com" in comando
    assert comando == "curl -I -s -m 5 https://google.com | head -5"
