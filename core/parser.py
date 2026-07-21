"""
It does not replace the LLM's interpretation—it merely
prepares/cleans the text and flags obvious problem
keywords to provide context for the final analysis.
"""

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