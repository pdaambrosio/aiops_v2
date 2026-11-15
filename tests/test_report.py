import pytest
from pydantic import ValidationError

from agents.report import SEVERITY_LABELS, DiagnosisReport, render_report


def report(**overrides) -> DiagnosisReport:
    campos = {
        "interpretacao": "O disco / está com 96% de uso.",
        "problema_detectado": True,
        "severidade": "alta",
        "recomendacao": "Limpar logs antigos em /var/log.",
        "proximo_passo": "Rodar tamanho_diretorios.",
    }
    campos.update(overrides)
    return DiagnosisReport(**campos)


def test_valid_report():
    assert report().severidade == "alta"


def test_severity_outside_of_list_is_rejected():
    with pytest.raises(ValidationError):
        report(severidade="média")


def test_issue_with_no_severity_is_rejected():
    with pytest.raises(ValidationError, match="nenhuma"):
        report(problema_detectado=True, severidade="nenhuma")


def test_with_no_issues_of_high_severity_is_rejected():
    with pytest.raises(ValidationError, match="nenhuma"):
        report(problema_detectado=False, severidade="alta")


def test_field_missing_and_rejected():
    with pytest.raises(ValidationError):
        DiagnosisReport(interpretacao="só isso")


def interpretation_comes_before_the_decision():
    campos = list(DiagnosisReport.model_fields)
    assert campos.index("interpretacao") < campos.index("problema_detectado")
    assert campos.index("problema_detectado") < campos.index("severidade")


def test_json_round_trip_report():
    original = report()
    assert DiagnosisReport.model_validate_json(original.model_dump_json()) == original


def test_render_with_issue_shows_severity_and_recommendation():
    texto = render_report(report())

    assert texto.startswith("[ALTA] O disco / está com 96% de uso.")
    assert "Recomendação: Limpar logs antigos em /var/log." in texto
    assert "Próximo passo: Rodar tamanho_diretorios." in texto


def test_render_without_issues_omits_the_recommendation():
    texto = render_report(report(
        problema_detectado=False, severidade="nenhuma",
        recomendacao="Nenhuma ação necessária.", proximo_passo="Nenhum.",
    ))

    assert texto.startswith("[OK] ")
    assert "Recomendação" not in texto


def test_every_severity_has_a_label():
    severidades = DiagnosisReport.model_fields["severidade"].annotation.__args__
    assert set(severidades) == set(SEVERITY_LABELS)
