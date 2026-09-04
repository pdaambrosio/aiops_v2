from utils import get_logger
logger = get_logger(__name__)

ALERT_WORDS = [
    "error", "erro", "failed", "failure", "falha",
    "dead", "inactive", "not running", "não está",
    "refused", "recusada", "timeout", "timed out",
    "cannot", "unable", "denied", "permission denied",
    "critical", "fatal", "panic", "oom", "out of memory",
    "no space", "disk full", "100%",
]


def detect_alerts(text: str) -> list[str]:
    """Detect alerts in text"""
    if not text:
        return []

    text_lower = text.lower()
    return [word for word in ALERT_WORDS if word in text_lower]


def summarize_result(result: dict, max_lines: int = 40) -> dict:
    """Summarize result"""
    if result.get("error"):
        text = result["error"]
    elif result.get("stdout", "").strip():
        text = result["stdout"]
    else:
        text = result.get("stderr", "") or "(sem saída)"

    lines = text.splitlines()
    if len(lines) > max_lines:
        hidden_lines = len(lines) - max_lines
        lines = lines[:max_lines] + [f"...({hidden_lines} linhas omitidas)"]

    sumarized_text = "\n".join(lines).strip()

    alert_source = " ".join(
        [
            result.get("stdout", ""),
            result.get("stderr", ""),
            result.get("error", "") or "",
        ]
    )

    alerts = detect_alerts(alert_source)
    if not result.get("success"):
        alerts = list(dict.fromkeys(["comando_falhou", *alerts]))

    return {
        "text": sumarized_text,
        "alerts": alerts,
        "success": bool(result.get("success"))
    }

# local test
if __name__ == "__main__":
    print(detect_alerts("tudo funcionando normalmente, sem problemas"))
    print(detect_alerts("O time foi hypercritical sobre a decisão"))
    print(detect_alerts("O prazo (deadline) do projeto é sexta-feira"))
    print(detect_alerts("O valor foi calculado erroneamente pelo script"))
    print()
    print(summarize_result({"success": False, "stdout": "algo aqui", "stderr": "", "error": "Command timed out"}))
    print(summarize_result({"success": True, "stdout": "tudo ok", "stderr": "warning irrelevante", "error": None}))
    print(summarize_result({"success": False, "stdout": "", "stderr": "connection refused", "error": None}))
    print(summarize_result({"success": True, "stdout": "", "stderr": "", "error": None}))
    stdout = "\n".join(f"linha {i}" for i in range(60))
    print(summarize_result({"success": True, "stdout": stdout, "stderr": "", "error": None}))
    stdout = "\n".join(f"linha {i}" for i in range(5))
    print(summarize_result({"success": True, "stdout": stdout, "stderr": "", "error": None}))
    print(summarize_result( {"success": True, "stdout": "ok", "stderr": "", "error": None}))
    print(summarize_result({"success": False, "stdout": "", "stderr": "", "error": "boom"}))
    print(summarize_result({"success": True, "stdout": "tudo certo", "stderr": "connection refused", "error": None}))