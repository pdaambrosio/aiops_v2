COMANDOS_PERMITIDOS = {
    # === SERVIÇOS ===
    "status_nginx": {
        "comando": "systemctl status nginx",
        "descricao": "Verifica status do nginx",
        "categoria": "servicos",
        "seguranca": "alta",
        "timeout": 10,
    },
    "status_apache": {
        "comando": "systemctl status apache2",
        "descricao": "Verifica status do apache2",
        "categoria": "servicos",
        "seguranca": "alta",
        "timeout": 10,
    },
    "listar_servicos": {
        "comando": "systemctl list-units --type=service --state=running | head -20",
        "descricao": "Lista serviços em execução",
        "categoria": "servicos",
        "seguranca": "alta",
        "timeout": 15,
    },

    # === DOCKER ===
    "docker_ps": {
        "comando": "docker ps",
        "descricao": "Lista containers em execução",
        "categoria": "docker",
        "seguranca": "alta",
        "timeout": 10,
    },
    "docker_stats": {
        "comando": "docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}'",
        "descricao": "Mostra consumo de recursos dos containers",
        "categoria": "docker",
        "seguranca": "alta",
        "timeout": 15,
    },
    "docker_logs": {
        "comando": "docker logs --tail=50 {container}",
        "descricao": "Mostra últimos 50 logs de um container",
        "categoria": "docker",
        "seguranca": "media",
        "timeout": 10,
        "requer_parametro": "container",
    },

    # === LOGS ===
    "logs_nginx": {
        "comando": "journalctl -u nginx -n 50 --no-pager",
        "descricao": "Últimos 50 logs do nginx",
        "categoria": "logs",
        "seguranca": "alta",
        "timeout": 10,
    },
    "logs_apache": {
        "comando": "journalctl -u apache2 -n 50 --no-pager",
        "descricao": "Últimos 50 logs do apache2",
        "categoria": "logs",
        "seguranca": "alta",
        "timeout": 10,
    },
    "logs_app_error": {
        "comando": "grep ERROR /var/log/app.log | tail -20",
        "descricao": "Últimos 20 erros do app",
        "categoria": "logs",
        "seguranca": "alta",
        "timeout": 10,
    },

    # === DISCO ===
    "espaco_disco": {
        "comando": "df -h",
        "descricao": "Espaço em disco do sistema",
        "categoria": "disco",
        "seguranca": "alta",
        "timeout": 10,
    },
    "tamanho_diretorios": {
        "comando": "du -sh /* 2>/dev/null | sort -h | tail -10",
        "descricao": "Top 10 diretórios maiores em /",
        "categoria": "disco",
        "seguranca": "alta",
        "timeout": 30,
    },
    "tamanho_logs": {
        "comando": "du -sh /var/log/* 2>/dev/null | sort -h",
        "descricao": "Tamanho dos arquivos em /var/log",
        "categoria": "disco",
        "seguranca": "alta",
        "timeout": 15,
    },

    # === REDE ===
    "conexoes_ativas": {
        "comando": "netstat -tuln | grep LISTEN",
        "descricao": "Portas em modo LISTEN",
        "categoria": "rede",
        "seguranca": "alta",
        "timeout": 10,
    },
    "conexoes_abertas": {
        "comando": "ss -tuln | head -15",
        "descricao": "Conexões ativas (socket statistics)",
        "categoria": "rede",
        "seguranca": "alta",
        "timeout": 10,
    },
    "ping": {
        "comando": "ping -c 4 {host}",
        "descricao": "Testa conectividade com um host",
        "categoria": "rede",
        "seguranca": "media",
        "timeout": 15,
        "requer_parametro": "host",
    },
    "curl_test": {
        "comando": "curl -I -s -m 5 {url} | head -5",
        "descricao": "Testa resposta HTTP de uma URL",
        "categoria": "rede",
        "seguranca": "media",
        "timeout": 10,
        "requer_parametro": "url",
    },

    # === PROCESSOS ===
    "top_cpu": {
        "comando": "ps aux --sort=-%cpu | head -11",
        "descricao": "Top 10 processos por CPU",
        "categoria": "processos",
        "seguranca": "alta",
        "timeout": 10,
    },
    "top_memoria": {
        "comando": "ps aux --sort=-%mem | head -11",
        "descricao": "Top 10 processos por memória",
        "categoria": "processos",
        "seguranca": "alta",
        "timeout": 10,
    },

    # === PACOTES ===
    "pacotes_atualizaveis": {
        "comando": "apt list --upgradable 2>/dev/null | head -20",
        "descricao": "Pacotes disponíveis para atualizar",
        "categoria": "pacotes",
        "seguranca": "alta",
        "timeout": 15,
    },

    # === SISTEMA ===
    "uptime": {
        "comando": "uptime",
        "descricao": "Tempo que o sistema está ligado e load average",
        "categoria": "sistema",
        "seguranca": "alta",
        "timeout": 5,
    },
    "uname": {
        "comando": "uname -a",
        "descricao": "Informações do kernel e da máquina",
        "categoria": "sistema",
        "seguranca": "alta",
        "timeout": 5,
    },
    "memoria_livre": {
        "comando": "free -h",
        "descricao": "Uso de memória RAM e swap",
        "categoria": "sistema",
        "seguranca": "alta",
        "timeout": 5,
    },
}

CATEGORIAS_COMANDOS: dict[str, list[str]] = {}
for _nome, _cfg in COMANDOS_PERMITIDOS.items():
    CATEGORIAS_COMANDOS.setdefault(_cfg["categoria"], []).append(_nome)