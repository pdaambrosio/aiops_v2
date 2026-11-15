# aiops_v2

Agente de diagnóstico de infraestrutura Linux que roda 100% local. Recebe uma
pergunta em português, escolhe e executa comandos de uma whitelist de
diagnóstico e devolve um relatório com interpretação, severidade e
recomendação.

---

## Requisitos

| Item | Versão / observação |
|---|---|
| Sistema operacional | Linux |
| Python | 3.13 ou superior |
| [uv](https://docs.astral.sh/uv/) | gerenciador de dependências e ambiente |
| Docker Model Runner | serve os modelos localmente (porta `12434`) |
| Modelo de linguagem | `ai/qwen2.5` (precisa suportar tool calling) |
| Modelo de embedding | `ai/embeddinggemma` |

### Dependências Python

Definidas no `pyproject.toml`:

| Pacote | Versão mínima |
|---|---|
| `langchain-core` | 1.4.8 |
| `langchain-ollama` | 1.1.0 |
| `langgraph` | 1.2.10 |
| `pydantic` | 2.13.4 |
| `chromadb` | 1.5.9 |
| `requests` | 2.34.2 |
| `pytest` | 9.1.1 |

---

## Instalação

```bash
git clone https://github.com/pdaambrosio/aiops_v2.git
cd aiops_v2

uv sync

docker model pull ai/qwen2.5
docker model pull ai/embeddinggemma
```

Confirme que o servidor de modelos responde:

```bash
curl -s http://localhost:12434/api/tags
```

---

## Uso

```bash
uv run python main.py
```

O agente exibe as configurações ativas, valida a conexão com o modelo e abre
um prompt interativo:

```
aiops_v2> como está o uso de disco do servidor?

Passo 1: espaco_disco -> df -h

[OK] O disco principal está com 21% de uso e as demais partições estão
dentro do normal.
Próximo passo: Nenhum.
```

Exemplos de perguntas:

- `faça uma avaliação geral de cpu, memória e disco`
- `quais processos estão consumindo mais memória?`
- `o nginx está rodando?`
- `o site https://exemplo.com está respondendo?`

Comandos que recebem parâmetro (`ping`, `curl_test`, `docker_logs`) pedem
confirmação antes de executar:

```
Comandos que exigem confirmação antes de executar:
  - curl_test (seguranca=alta): $ curl -I -s -m 5 'https://exemplo.com' | head -5
Confirma a execução? [s/n]
```

Para encerrar: `sair`, `exit`, `quit`, `q` ou `Ctrl+D`.

---

## Configuração

As opções podem ser sobrescritas por variáveis de ambiente.

| Variável | Padrão | Descrição |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:12434` | endereço do servidor de modelos |
| `OLLAMA_MODEL` | `docker.io/ai/qwen2.5:latest` | modelo de linguagem |
| `OLLAMA_EMBEDDINGS_MODEL` | `docker.io/ai/embeddinggemma:latest` | modelo de embedding |
| `LLM_TEMPERATURE` | `0.3` | temperatura da análise |
| `LLM_TOOL_TEMPERATURE` | `0.0` | temperatura da escolha de comandos |
| `OLLAMA_NUM_CTX` | `8192` | janela de contexto (tokens) |
| `OLLAMA_NUM_GPU` | `8` | camadas enviadas para a GPU |
| `PLAYBOOK_TOP_K` | `1` | quantidade de playbooks recuperados |
| `PLAYBOOK_MAX_DISTANCE` | `0.82` | distância máxima para um playbook ser usado |
| `COMMAND_TIMEOUT` | `30` | timeout padrão dos comandos (segundos) |
| `MAX_OUTPUT_LENGTH` | `5000` | tamanho máximo da saída enviada ao modelo |
| `MAX_ERROR_LENGTH` | `1000` | tamanho máximo do erro enviado ao modelo |
| `LOG_LEVEL` | `INFO` | nível de log |
| `DEBUG` | `false` | modo de depuração |

Exemplo:

```bash
LOG_LEVEL=WARNING uv run python main.py
```

---

## Comandos disponíveis

Definidos em `config/commands.py`.

| Categoria | Comandos |
|---|---|
| Serviços | `status_nginx`, `status_apache`, `listar_servicos` |
| Docker | `docker_ps`, `docker_stats`, `docker_logs` |
| Logs | `logs_nginx`, `logs_apache`, `logs_app_error` |
| Disco | `espaco_disco`, `tamanho_diretorios`, `tamanho_logs` |
| Rede | `conexoes_ativas`, `conexoes_abertas`, `ping`, `curl_test` |
| Processos | `top_cpu`, `top_memoria` |
| Sistema | `uptime`, `uname`, `memoria_livre`, `pacotes_atualizaveis` |

---

## Playbooks

Os runbooks em `playbooks/*.md` são indexados em `.chroma/` na primeira
execução. Após adicionar ou editar um playbook, apague a pasta para
reindexar:

```bash
rm -rf .chroma/
```

---

## Testes

```bash
# testes rápidos, sem modelo rodando
uv run pytest tests/ --ignore=tests/test_e2e.py

# testes ponta a ponta, com o modelo real
uv run pytest tests/test_e2e.py
```

---

## Licença

MIT. Ver [LICENSE](LICENSE).
