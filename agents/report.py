from typing import Literal
from pydantic import BaseModel, Field, model_validator

Severity = Literal["nenhuma", "baixa", "media", "alta", "critica"]
SEVERITY_LABELS: dict[str, str] = {
    "nenhuma": "OK",
    "baixa": "BAIXA",
    "media": "MÉDIA",
    "alta": "ALTA",
    "critica": "CRÍTICA",
}

class DiagnosisReport(BaseModel):
    """Final diagnosis returned by the finalize node"""
    interpretacao: str = Field(
        description=(
            "O que as saídas dos comandos mostram, respondendo diretamente à "
            "pergunta do usuário. De 2 a 4 frases, sem repetir comando por comando."
        )
    )

    problema_detectado: bool = Field(
        description=(
            "true se as saídas mostram um problema real; false se está tudo normal."
        )
    )

    severidade: Severity = Field(
        description=(
            "nenhuma (sem problema), baixa, media, alta ou critica "
            "(serviço fora do ar ou risco imediato)."
        )
    )

    recomendacao: str = Field(
        description=(
            "Ação prática para resolver o problema. Se não houver problema, "
            "escreva 'Nenhuma ação necessária.'"
        )
    )

    proximo_passo: str = Field(
        description=(
            "A próxima verificação útil, ou 'Nenhum.' se a investigação está completa."
        )
    )

    @model_validator(mode="after")
    def _severity_matches_problem(self) -> "DiagnosisReport":
        if self.problema_detectado == (self.severidade == "nenhuma"):
            raise ValueError(
                "severidade 'nenhuma' se e somente se problema_detectado for false"
            )
        return self


def render_report(report: DiagnosisReport) -> str:
    """Human-readable text of a DiagnosisReport (CLI and conversation memory)"""
    lines = [f"[{SEVERITY_LABELS[report.severidade]}] {report.interpretacao}"]
    if report.problema_detectado:
        lines.append(f"\nRecomendação: {report.recomendacao}")
    lines.append(f"Próximo passo: {report.proximo_passo}")
    return "\n".join(lines)