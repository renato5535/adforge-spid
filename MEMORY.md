# AdForge - Memória do Projeto Spid Cup / Spid Fest

## Eventos
- **Spid Cup 2026 - Etapa 02:** encerrada (faturamento R$ 114.060)
- **Spid Fest 2026:** 02 a 05 de Julho de 2026, São Paulo International Dragway, Itatiba/SP
  - Site: spidfest.com.br
  - Patrocínio: FuelTech
  - Designer: Corvus
  - Status atual: 170 ingressos vendidos de 2000 (8,5%)

## Preços confirmados Spid Fest 2026 (último lote)
- Arquibancada individual: R$ 100,00
- Ingresso Família (2 pessoas + Box): R$ 180,00 (até quarta-feira antes do evento)
- Lounge SPID: R$ 790,00
- Parcelamento: até 12x no cartão
- Bilheteria física no evento: mesmo preço (não fica mais caro)

## Configuração Meta API
- System User: adforge-mcp (ID: 61589485943475)
- App: adforge-marketing (criado no developers.facebook.com)
- Token: persistido em ~/.adforge/.env
- Escopo: ads_management, ads_read, business_management, pages_read_engagement, pages_manage_posts, instagram_basic, instagram_content_publish
- Validade: never expires
- Status: testado e funcionando (GET /me HTTP 200 em 16/06/2026)

## Configuração de modelo LLM (decidido 16/06/2026)
- Todo o AdForge roda em **claude-sonnet-4-6** (Sonnet 4.6), antes era Opus 4.8
- Sessão + 7 agentes do time (skills): `.claude/settings.json` do projeto → `"model": "claude-sonnet-4-6"`
- 29 subagentes (`.claude/agents/*.md`): frontmatter `model: claude-sonnet-4-6`
- Global da máquina (`~/.claude/settings.json`) segue em Opus — não foi tocado; outros projetos intactos
- Exceção a lembrar: `nano-banana-generator` era haiku (barato p/ gerar prompt de imagem) e subiu p/ Sonnet junto — reverter se custo incomodar
- Motivo: redução de custo mantendo qualidade aceitável para tasks de marketing

## Decisões da Fase 1 (em construção)
- Cadência de relatório: diária às 08:00 BRT (Task Scheduler configurado para 08:00)
- Canal de entrega: Telegram bot (✅ funcional — testado 16/06/2026)
- Bot: @adforge_spid_bot (token revogado e regenerado em 16/06/2026 por segurança; Chat ID obtido)
- Escopo: só Meta Ads + dados do Agenda Esportiva via Cowork
- Modelo de execução: loop agêntico
- Guardrails: max 50 chamadas API por execução, max 15 min execução, max R$10 em tokens LLM
- Aprovação humana: zero nessa fase (só leitura)

## Credenciais (todas no Bitwarden, pasta "Token" / "AdForge")
- Token Meta System User adforge-mcp
- App Meta adforge-marketing (App ID + App Secret)
- Token Telegram Bot (regenerado 16/06/2026 — pasta "Token Bot Telegram")
- Chat ID Telegram (obtido 16/06/2026)
- Login Agenda Esportiva (a ser adicionado)

## Aprendizados importantes
- Remarketing carregou faturamento na Etapa 02 (Pageview 180D ROAS 35x, Video View 95% 180D ROAS 11x)
- Lookalike 1% Purchase foi descoberta nova (ROAS 30x)
- Interesses cold queimou dinheiro - pausar logo no início
- Google Ads e TikTok Ads têm tracking quebrado (Agenda Esportiva não envia conversões) - investir só no Meta

## Status da 3ª Etapa SPID Cup 2026 (atualizado 18/07/2026)
- Evento: 28-30/Ago/2026, São Paulo Int'l Dragway, Itatiba/SP
- Campanha Meta: **48 ads ATIVOS** (8 criativos × 6 adsets)
  - 3 vídeos: INGRESSO (copy 0), FAMÍLIA (copy 2), PULSEIRA (copy 1)
  - 5 imagens: INGRESSO, FAMÍLIA, PULSEIRA, brinde-pulseiras, pulseiras-estático
  - Adsets: B-00 Pageview 180D / B-01 Video View 95% / B-02 Purchase 180D / B-03 InitiateCheckout 180D / A-01 LKL 1% Purchase / A-02 Engajamento 365D
- YouTube Shorts: 3 agendados (INGRESSO 20/Jul, PULSEIRA 22/Jul, FAMÍLIA 24/Jul)
- Daily-analyst: ATIVO (08:00 diário, wscript+launcher.vbs, sem janela)
- TikTok: pendente DNS verification (TXT record a ser adicionado pela equipe Agenda em spidcup.com.br)

## Fix crítico Meta API v25+ (18/07/2026)
- `degrees_of_freedom_spec → standard_enhancements` DESCONTINUADO (subcode 3858504)
- Remover o campo `degrees_of_freedom_spec` inteiro dos payloads de /adcreatives
- Scripts `meta_create_ads.py` e `meta_create_image_ads.py` já corrigidos

## Próximo passo imediato
- Monitorar performance dos 48 ads via daily-analyst (primeiro relatório 19/Jul 08:00)
- Pausar criativos com ROAS abaixo do mínimo conforme política de otimização
- TikTok: confirmar com equipe Agenda adição do TXT record no DNS
