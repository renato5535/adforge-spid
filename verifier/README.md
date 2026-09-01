# @verifier — Anti-alucinação do AdForgeSquad

## Papel
Verificador independente que valida dados de campanha diretamente na Meta API,
sem depender de relatórios anteriores ou memória de outros agentes.

## Loop de execução

```
daily-analyst gera relatório
       ↓
@verifier puxa dados frescos da Meta API (independente)
       ↓
    OK → relatório segue normal para o bot
  WARN → relatório vai com ⚠️ e dados reais no Telegram
 ALERT → bloqueia, notifica Renato diretamente com dados divergentes
```

## Verificações executadas

1. **Adsets sem entrega** — quantos adsets "ativos" tiveram spend=0 hoje
2. **Divergência de spend** — compara spend real da API vs o que foi reportado (>30% = ALERT)
3. **Dados frescos da conta** — spend/ROAS/compras direto da Graph API

## Arquivos

| Arquivo | Função |
|---|---|
| `verifier.py` | Verificações + veredicto + Telegram |
| `verify_loop.py` | Integração com daily-analyst; modo `--watch` para campanhas críticas |

## Uso manual

```powershell
# Verificação única
python ~/.adforge/verifier/verify_loop.py

# Modo watch (verifica a cada 5 min — usar em dia de evento)
python ~/.adforge/verifier/verify_loop.py --watch 300
```

## Integração com daily-analyst

Em `~/.adforge/daily_analyst/run.py`, após gerar o relatório, adicionar:

```python
from verifier.verify_loop import run_verification
ok = run_verification(reported_data={"spend_today": spend, "roas_today": roas})
if not ok:
    print("[run] ALERTA do @verifier — relatório bloqueado")
    sys.exit(2)
```

## Scheduler (Windows Task Scheduler)

Task sugerida: `\AdForge\AdForgeVerifier`
- Modo: `python verify_loop.py` (verificação única)
- Horário: 30min após o daily-analyst (08:30) + repetição a cada 2h
- Em dias de evento: usar modo `--watch 300` em terminal dedicado
