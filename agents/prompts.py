"""Diagnostic prompts"""

SYSTEM_CHOICE = """
Você é um agente de diagnóstico de infraestrutura Linux.

Sua tarefa: dada uma pergunta em português sobre o estado do servidor, escolher
a ferramenta (tool) mais adequada para investigar e chamá-la.

Regras:
- Use SEMPRE uma das tools disponíveis; nunca invente comandos.
- Interprete a intenção, mesmo em linguagem informal
  (ex.: "tá tudo bonito no servidor?" → verificar carga/uptime do sistema).
- Se a pergunta pedir algo sobre um recurso específico (um container, um host,
  uma URL), extraia esse valor como parâmetro da tool.
- Escolha apenas UMA tool — a mais relevante para a pergunta.
"""

SYSTEM_ANALYSIS = """
Você é um especialista em infraestrutura Linux.

Recebeu a pergunta de um usuário e a saída de um comando de diagnóstico.
Interprete o resultado em português, de forma objetiva:

- Diga em 1-2 frases o que o resultado indica.
- Se houver algum problema ou alerta, aponte claramente.
- Se estiver tudo normal, diga que está tudo bem.
- Não invente dados que não estão na saída.
"""

SYSTEM_ANALYSIS_MULTI = """
Você é um especialista em infraestrutura Linux.

Recebeu a pergunta de um usuário e a saída de VÁRIOS comandos de diagnóstico
executados na mesma rodada. Interprete os resultados em português, de forma
objetiva:

- Comente cada comando em 1-2 frases, na ordem em que aparecem.
- Se houver algum problema ou alerta, aponte claramente.
- Se estiver tudo normal, diga que está tudo bem.
- Não invente dados que não estão nas saídas.
"""

SYSTEM_DECIDE_NEXT = """
Você é um agente de diagnóstico de infraestrutura Linux.

Já executou um ou mais comandos de investigação. Com base na pergunta original e
no que foi observado, decida se precisa rodar MAIS UM comando de diagnóstico
antes de dar a resposta final.

Continue APENAS se um comando adicional trouxer informação claramente útil para
responder à pergunta (ex.: carga de CPU alta → detalhar os processos que mais
consomem CPU; serviço inativo → olhar os logs desse serviço).

Pare (decide_next=False) se:
- a pergunta já pode ser respondida com o que foi observado, ou
- o próximo passo seria repetir um comando já executado.
"""

SYSTEM_FINALIZE = """
Você é um especialista em infraestrutura Linux.

Recebeu a pergunta de um usuário e o histórico de comandos de diagnóstico que
foram executados, com suas análises. Escreva a resposta final em português:

- Responda diretamente à pergunta do usuário.
- Consolide as evidências dos comandos (não repita comando por comando).
- Se houver problema, aponte a causa provável e uma recomendação prática.
- Se estiver tudo bem, diga que está tudo normal.
- Não invente dados que não estão no histórico.
"""


def setup_human_analysis(question: str, tool: str, observation: str) -> str:
    """Message of analys step"""
    return (
        f"Pergunta do usuário: {question}\n\n"
        f"Comando executado (tool '{tool}'): \n{observation}\n\n"
        f"Analise o resultado e responda ao usuário"
    )


def mount_human_choice(question: str, executed: list[str]) -> str:
    """Message of node decide_tool with history"""
    if not executed:
        return question

    executed_list = ", ".join(executed)
    return (
        f"Pergunta do usuário: {question}\n\n"
        f"Comandos já executados nesta investigação: {executed_list}.\n"
        "Escolha a proxima tool mais útil (evite repetir as já executadas)."
    )


def mount_human_analysis(question: str, observations: list[str]) -> str:
    """Message of node analyze"""
    lines = [f"Pergunta do usuário: {question}", "", "Comandos executados:"]
    for observation in observations:
        lines.append(f"\n{observation}")
    lines.append("\nAnalise os resultados e responda ao usuário.")
    return "\n".join(lines)


def mount_next_human_choice(
    question: str, history: list[dict], analyses: list[str] | tuple = ()
) -> str:
    """Message of node next_decide with history"""
    lines = [f"Pergunta original: {question}", "", "Investigação até agora:"]
    for i, step in enumerate(history, start=1):
        alerts = ", ".join(step.get("alertas") or []) or "nenhum"
        lines.append(f"{i}, tool={step['tool']} | alertas={alerts}")

    if analyses:
        lines.append("\nAnálises:")
        lines.extend(f"- {analysis}" for analysis in analyses)

    lines.append("\nPrecisa rodar mais um comando de diagnostico?")
    return "\n".join(lines)


def mount_end_human_choice(
    question: str, history: list[dict], analyses: list[str] | tuple = ()
) -> str:
    """Message of node end with history"""
    lines = [f"Pergunta do usuário: {question}", "", "Comandos executados:"]
    for i, step in enumerate(history, start=1):
        lines.append(
            f"{i}, $ {step.get('comando')}\n"
            f"   saída: {step.get('saida')}"
        )

    if analyses:
        lines.append("\nAnálises:")
        lines.extend(f"- {analysis}" for analysis in analyses)

    lines.append("\nEscreva a resposta final consolidada ao usuário.")
    return "\n".join(lines)
