# Disco cheio

Sintoma: o comando `df -h` mostra uso de disco acima de 90% em alguma
partição.

Causas comuns:
- Logs antigos acumulados em `/var/log`.
- Imagens e containers Docker não utilizados.
- Arquivos temporários ou de backup esquecidos.

Diagnóstico sugerido:
1. Rodar `tamanho_diretorios` (`du -xsh /* | sort -h | tail -10`) pra achar
   o maior consumidor.
2. Se for `/var/log`, rodar `tamanho_logs` pra ver quais arquivos de log
   estão pesados.
3. Se houver Docker, checar `docker_stats`/`docker_ps` — imagens paradas
   também ocupam espaço.

Recomendação: limpar logs antigos (rotacionar ou compactar), remover
containers/imagens não usados (`docker system prune`), e configurar rotação
de log se ainda não existir.