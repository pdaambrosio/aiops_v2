def test_finalize_contains_actual_report_fields():
    from agents.prompts import SYSTEM_FINALIZE
    from agents.report import SEVERITY_LABELS, DiagnosisReport

    for field in DiagnosisReport.model_fields:
        assert field in SYSTEM_FINALIZE

    for severity in SEVERITY_LABELS:
        assert severity in SYSTEM_FINALIZE