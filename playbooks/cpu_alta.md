# CPU alta / carga alta

Sintoma: `uptime` mostra load average bem acima do número de núcleos da
máquina, ou o sistema está lento de forma geral.

Causas comuns:
- Um processo específico em loop ou processamento pesado.
- Volume de requisições muito acima do normal.
- Um processo "preso" consumindo CPU sem terminar.

Diagnóstico sugerido:
1. Rodar `top_cpu` (`ps aux --sort=-%cpu | head -11`) pra identificar qual
   processo está consumindo mais.
2. Se for um serviço conhecido (nginx, apache, um container), checar os
   logs desse serviço pra entender se há um padrão anormal de requisições.

Recomendação: se for um processo específico travado, avaliar reiniciá-lo;
se for volume de tráfego, investigar se é legítimo (pico de uso) ou um
possível abuso/ataque.