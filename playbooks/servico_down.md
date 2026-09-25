# Serviço fora do ar

Sintoma: `systemctl status` mostra o serviço como `inactive` ou `failed`.

Causas comuns:
- A aplicação travou ou encerrou com erro (crash).
- Configuração inválida impedindo o serviço de subir.
- A porta que o serviço usa já está ocupada por outro processo.

Diagnóstico sugerido:
1. Rodar `status_nginx`/`status_apache` (ou o status do serviço em questão)
   pra confirmar o estado.
2. Rodar `logs_nginx`/`logs_apache` (ou `journalctl` equivalente) pra ver a
   última mensagem de erro antes da queda.
3. Rodar `conexoes_ativas` pra checar se a porta esperada está em uso por
   outro processo.

Recomendação: corrigir a causa raiz apontada no log (configuração, porta em
conflito, dependência faltando) antes de simplesmente reiniciar — reiniciar
sem entender a causa tende a repetir o problema.