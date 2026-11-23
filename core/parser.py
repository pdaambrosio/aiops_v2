import os
import re

from utils import get_logger
logger = get_logger(__name__)

ALERT_WORDS = [
    "error", "erro", "failed", "failure", "falha",
    "dead", "inactive", "not running", "não está",
    "refused", "recusada", "timeout", "timed out",
    "cannot", "unable", "denied", "permission denied",
    "critical", "fatal", "panic", "oom", "out of memory",
    "no space", "disk full", "100% packet loss",
]


def detect_alerts(text: str) -> list[str]:
    """Detect alerts in text"""
    if not text:
        return []

    text_lower = text.lower()
    return [
        word for word in ALERT_WORDS
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text_lower)
    ]


DISK_USAGE_LIMIT = 90
PROCESS_CPU_LIMIT = 90.0
LOAD_AVERAGE_PATTERN = re.compile(r"load average:\s*([\d.]+)")


def detect_threshold_alerts(text: str) -> list[str]:
    if not text:
        return []

    alerts = []
    for line in text.splitlines():
        parts = line.split()

        if len(parts) >= 6 and parts[-2].endswith("%") and parts[-2][:-1].isdigit():
            is_snap = parts[0].startswith("/dev/loop") or parts[-1].startswith("/snap")
            if not is_snap and int(parts[-2][:-1]) >= DISK_USAGE_LIMIT:
                alerts.append(f"disco_acima_de_{DISK_USAGE_LIMIT}%")

        ps_parts = line.split(None, 10)
        if len(ps_parts) == 11 and ps_parts[1].isdigit() and not ps_parts[10].startswith("ps "):
            try:
                cpu = float(ps_parts[2])
            except ValueError:
                cpu = 0.0
            if cpu >= PROCESS_CPU_LIMIT:
                alerts.append("processo_com_cpu_alta")

    match = LOAD_AVERAGE_PATTERN.search(text)
    if match and float(match.group(1)) > (os.cpu_count() or 1):
        alerts.append("load_acima_dos_nucleos")

    return list(dict.fromkeys(alerts))


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

    alerts = detect_alerts(alert_source) + detect_threshold_alerts(result.get("stdout", ""))
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
