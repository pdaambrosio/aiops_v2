from agents.graph import NextDecision
from agents.prompts import (
    SYSTEM_DECIDE_NEXT,
    SYSTEM_FINALIZE,
    mount_end_human_choice,
    mount_human_analysis,
    mount_human_choice,
    mount_next_human_choice,
)
from agents.report import SEVERITY_LABELS, DiagnosisReport


def step(tool="memoria_livre", comando="free -h", alertas=None):
    return {
        "tool": tool,
        "comando": comando,
        "saida": "Mem: 3.9Gi",
        "alertas": alertas or [],
    }


def test_primeira_rodada_manda_a_pergunta_pura():
    assert mount_human_choice("como está a memória?", []) == "como está a memória?"


def test_rodada_seguinte_inclui_o_que_ja_foi_executado():
    saida = mount_human_choice("como estão cpu e disco?", ["top_cpu", "espaco_disco"])

    assert "Pergunta atual do usuário: como estão cpu e disco?" in saida
    assert "Comandos já executados nesta investigação: top_cpu, espaco_disco" in saida


def test_rodada_seguinte_nao_tem_quebras_de_linha_duplicadas():
    assert "\n\n\n" not in mount_human_choice("cpu?", ["top_cpu"])


def test_pergunta_de_seguimento_inclui_a_conversa_anterior():
    conversa = [{"pergunta": "como está a memória?", "resposta": "Normal."}]
    saida = mount_human_choice("e os processos?", [], conversa)

    assert "- Pergunta: como está a memória?" in saida
    assert "Resposta: Normal." in saida
    assert "Pergunta atual do usuário: e os processos?" in saida


def test_analise_recebe_todas_as_observacoes_da_rodada():
    saida = mount_human_analysis("q", ["$ free -h\nMem: 3.9Gi", "$ df -h\n/dev/sda1 21% /"])

    assert "$ free -h" in saida
    assert "$ df -h" in saida
    assert saida.endswith("Analise os resultados e responda ao usuário.")


def test_decide_next_lista_tools_e_alertas():
    saida = mount_next_human_choice(
        "q", [step(), step("status_nginx", "systemctl status nginx", ["comando_falhou"])]
    )

    assert "1, tool=memoria_livre | alertas=nenhum" in saida
    assert "2, tool=status_nginx | alertas=comando_falhou" in saida


def test_decide_next_inclui_as_analises_da_rodada():
    saida = mount_next_human_choice("q", [step()], ["Memória com folga."])

    assert "Análises:" in saida
    assert "- Memória com folga." in saida


def test_decide_next_sem_analises_nao_imprime_secao():
    assert "Análises:" not in mount_next_human_choice("q", [step()])


def test_finalize_lista_comando_e_saida():
    saida = mount_end_human_choice("q", [step()], ["analise consolidada"])

    assert "$ free -h" in saida
    assert "Mem: 3.9Gi" in saida
    assert "analise consolidada" in saida
    assert "Escreva a resposta final" in saida


def test_finalize_inclui_os_alertas_de_cada_passo():
    saida = mount_end_human_choice(
        "q", [step("tamanho_diretorios", "du -xsh /*", ["comando_falhou"])]
    )

    assert "alertas: comando_falhou" in saida


def test_finalize_marca_passo_sem_alerta_como_nenhum():
    assert "alertas: nenhum" in mount_end_human_choice("q", [step()])


def test_finalize_aceita_ser_chamado_sem_analises():
    saida = mount_end_human_choice("q", [step()])

    assert "$ free -h" in saida
    assert "Analises:" not in saida


def test_finalize_inclui_a_conversa_anterior():
    conversa = [{"pergunta": "como está a memória?", "resposta": "Normal."}]
    saida = mount_end_human_choice("e o disco?", [step()], conversation=conversa)

    assert saida.startswith("Conversa até agora nesta sessão:")
    assert "- Pergunta: como está a memória?" in saida


def test_finalize_inclui_o_trecho_do_playbook():
    saida = mount_end_human_choice("q", [step()], playbook="# Disco cheio\nSintoma: ...")

    assert "Trecho de runbook interno relevante" in saida
    assert "# Disco cheio" in saida
    assert saida.endswith("Escreva a resposta final consolidada do usuário.")


def test_finalize_sem_playbook_nao_cita_runbook():
    assert "runbook" not in mount_end_human_choice("q", [step()]).lower()


def test_decide_next_usa_o_nome_real_do_campo_do_schema():
    assert "needs_more" in NextDecision.model_fields
    assert "needs_more" in SYSTEM_DECIDE_NEXT


def test_decide_next_pede_verificacao_de_cobertura():
    assert "COBERTURA" in SYSTEM_DECIDE_NEXT
    assert "ainda NÃO foi investigado" in SYSTEM_DECIDE_NEXT


def test_finalize_instrui_a_nao_preencher_lacuna_de_comando_que_falhou():
    assert "comando_falhou" in SYSTEM_FINALIZE
    assert "Nunca preencha a lacuna com a saída de outro" in SYSTEM_FINALIZE


def test_finalize_contains_actual_report_fields():
    for field in DiagnosisReport.model_fields:
        assert field in SYSTEM_FINALIZE

    for severity in SEVERITY_LABELS:
        assert severity in SYSTEM_FINALIZE
