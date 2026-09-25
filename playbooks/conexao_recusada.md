# Conexão recusada

Sintoma: `curl` ou `ping` retornam erro de conexão recusada ou timeout ao
tentar acessar um host/porta.

Causas comuns:
- O serviço de destino não está escutando na porta esperada (não está
  rodando, ou está rodando em outra porta).
- Firewall ou regra de rede bloqueando a conexão.
- O host de destino está fora do ar.

Diagnóstico sugerido:
1. Rodar `conexoes_ativas`/`conexoes_abertas` (`netstat`/`ss`) na máquina de
   destino pra confirmar se a porta está em `LISTEN`.
2. Rodar `curl_test` na URL específica pra ver o código de resposta HTTP,
   se aplicável.
3. Se a porta não estiver em `LISTEN`, o problema é o serviço não estar
   rodando (ver playbook de "Serviço fora do ar").

Recomendação: confirmar primeiro se o processo de destino está de pé antes
de investigar rede/firewall — é a causa mais comum e mais rápida de
descartar.