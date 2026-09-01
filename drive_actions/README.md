# AdForge Drive Actions

Pipeline Drive → Meta para criação autônoma de ads a partir de artes do time de design.

## Fluxo Completo

```
Time de design sobe artes na pasta do Drive
          ↓
Renato avisa via Telegram: /nova_pasta FOLDER_URL [adset_id]
          ↓
Bot salva em drive_queue.json e confirma
          ↓
Renato abre sessão Claude
          ↓
Claude verifica fila → usa Drive MCP para baixar artes
          ↓
meta_actions.create_ad_from_image() → ads criados (PAUSADOS)
          ↓
Telegram: "X criativos criados — aguardando aprovação"
          ↓
Renato aprova via Meta (ou Fase 2 do bot)
```

## Arquivos

| Arquivo | Função |
|---|---|
| `drive_queue.py` | Fila de pastas aguardando processamento |
| `process_queue.py` | Helpers para processamento em sessão Claude |
| `session_start.py` | Check de início de sessão |

## Estrutura das Pastas SPID Drive

```
QUARTA ETAPA - SPID/          ← evento
├── 01 - ARTE PRINCIPAL/
│   └── REDE SOCIAL/          ← subpasta de formato
│       └── arte.png
├── 06 - INGRESSO A VENDA/
│   └── INGRESSO.png          ← arquivo direto
└── 17 - VÍDEO VT/
    └── video.mp4
```

- Owner: `spidcupmaterial@gmail.com`
- Arquivos aceitos: PNG, JPG, JPEG, MP4, MOV
- Varredura recursiva inclui subpastas (ex: REDE SOCIAL, STORY)

## Uso via Bot Telegram

```
/nova_pasta https://drive.google.com/drive/folders/FOLDER_ID
/nova_pasta FOLDER_ID 23989229 "3ª Etapa artes"
```

## Processamento em Sessão Claude

Quando há itens na fila, Claude processa automaticamente:
1. Lista arquivos via `mcp__claude_ai_Google_Drive__search_files`
2. Baixa cada imagem via `mcp__claude_ai_Google_Drive__download_file_content`
3. Salva em `~/.adforge/temp/drive_assets/`
4. Chama `meta_actions.create_ad_from_image()` para cada arquivo
5. Envia resumo ao Renato via Telegram

## Copy Padrão por Tipo de Arte

| Pasta | Headline sugerida | CTA |
|---|---|---|
| INGRESSO A VENDA | Ingressos disponíveis | BUY_TICKETS |
| ÚLTIMO LOTE | Última chance | BUY_TICKETS |
| SORTEIO | Comprou, ganhou | LEARN_MORE |
| VÍDEO VT | SPID CUP 2026 | LEARN_MORE |
