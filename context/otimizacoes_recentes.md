# Otimizações Recentes — 3ª Etapa SPID Cup 2026

> Arquivo de log de ações executadas na campanha. O daily-analyst usa este contexto
> para NÃO recomendar ações que já foram tomadas e para interpretar corretamente
> as métricas pós-otimização.

---

## ✅ Otimização 1 — 18/Ago/2026 (10 dias antes do evento)

**Objetivo:** Swap de criativos no sprint final — substituir ads com fadiga por copy de urgência

**Ações executadas:**
- B-03 InitiateCheckout 180D → **PAUSED** (ROAS estava 0x)
- Upload de 4 novos vídeos (etapa3-vid-01/02/03/04) + imagem SORTEIO-DRAGSTER.png
- Criação de creative sprint final (copy atualizado: Individual R$90, Família R$135, urgência "faltam X dias")
- PATCH inline nos ads de B-00, B-01 e B-02 com o novo creative

**Estado pós-otimização:**
- B-00, B-01, B-02: ACTIVE com novos criativos ✅
- B-03: PAUSED ✅

**Impacto observado:**
- ROAS 24h no dia 18/Ago: 43,5x (spike pós-troca)
- ROAS 7d em 19/Ago: 14,3x
- Frequência ainda alta (acumulada pré-troca) — vai cair naturalmente nos próximos dias

**O que NÃO fazer após esta ação:**
- ❌ Recomendar "subir criativos novos em B-00/B-01/B-02" — já feito em 18/Ago
- ❌ Pausar B-00/B-01/B-02 por fadiga — a freq alta é herdada, criativos são novos
- ❌ Interpretar freq 17x/26x como "mesmo criativo saturado" — creative rodou menos de 5 dias

---

## ✅ Otimização 2 — 20/Ago/2026 (8 dias antes do evento)

**Objetivo:** Reforço de vídeos + preparação do carrossel

**Ações executadas:**
- Upload vid-04 novo (id 2154051288509185) + vid-05 (id 1786638312585666) → PATCH inline B-00/B-01/B-02 ✅
- Upload vid-01 CORRIGIDO (id 1751357062657146) — substituiu versão com problema de áudio ✅
- Creative RMKT atual: **6 vídeos** (v01-corr, v02, v03, v04, v04-novo, v05) + img SORTEIO-DRAGSTER

**Carrossel — preparado mas NÃO publicado:**
- 11 imagens enviadas para a Meta (hashes salvos)
- 3 creatives de carrossel criados: V1=PROMODS / V2=SORTEIO / V3=FESTIVAL
- Adsets: **NÃO criados** — publicação adiada para 22/Ago por decisão estratégica
- Bloqueio técnico: API bloqueia criação de novos adsets (subcode 3858634); publicação será via Gerenciador de Anúncios (UI)

**O que NÃO fazer após esta ação:**
- ❌ Recomendar "renovar criativos B-00/B-01/B-02" — já têm 6 vídeos novos desde 20/Ago
- ❌ Tratar os criativos atuais como "antigos" — todos foram subidos em 18-20/Ago

---

## 🔜 Pendência — Carrossel (previsto 22/Ago/2026)

**O que será feito:**
- Criar adsets de carrossel via Gerenciador de Anúncios (UI) — API bloqueada (subcode 3858634)
- Ativar os 3 creatives de carrossel: V1=PROMODS / V2=SORTEIO / V3=FESTIVAL
- Alvo: complementar RMKT com formato diferente para reduzir fadiga de vídeo

**Após publicação:** atualizar este arquivo com IDs dos adsets criados.

---

## Contexto para o Analisador

- **Criativos atuais em B-00/B-01/B-02:** todos têm menos de 5 dias de vida (subidos 18-20/Ago)
- **Frequência alta (17–26x):** acumulada pelos criativos anteriores; os novos ainda não atingiram saturação
- **B-03:** pausado intencionalmente — não reativar sem análise de ROAS
- **Próxima ação pendente:** carrossel previsto para 22/Ago
