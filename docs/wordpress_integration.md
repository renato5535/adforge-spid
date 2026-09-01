# AdForge — Integração WordPress (SPID CUP)

Capacita o AdForge a criar e atualizar LPs autonomamente via REST API,  
com aprovação do Renato via Telegram (Fase 2).

**Status:** Ambiente configurado — aguardando credenciais para primeiro teste.  
**Data:** 2026-07-11

---

## 1. Biblioteca escolhida: `requests` (direto, sem wrapper WordPress)

### Decisão

**Não existe biblioteca Python para WordPress REST API ativamente mantida em 2026.**

| Opção | Status | Problema |
|---|---|---|
| `python-wordpress-xmlrpc` | ❌ Deprecated | Usa XML-RPC (desabilitado por padrão no WP moderno) |
| `wordpress-api` (PyPI) | ❌ Abandonado | Último commit 2019, não suporta Application Passwords |
| `requests` (stdlib-adjacent) | ✅ Mantido | Versão 2.34.2, release 2025, suporte ativo |
| `requests` + wrapper próprio | ✅ **Escolhido** | Total controle, zero lock-in, já instalado no venv |

### Justificativa

Application Passwords autenticam via HTTP Basic Auth padrão — exatamente o que  
`requests.auth.HTTPBasicAuth` resolve com 1 linha. Não há valor em adicionar um  
wrapper de terceiro não-mantido por cima de algo tão direto.

O `wp_client.py` em `~/.adforge/wp/` é nosso wrapper próprio (thin client, ~150 linhas).

### Instalação

```
venv: ~/.adforge/venv_wp/
pip:  requests 2.34.2
```

Para rodar qualquer script WordPress:
```powershell
C:\Users\User\.adforge\venv_wp\Scripts\python script.py
```

---

## 2. Autenticação via Application Password

### Como gerar (você faz uma vez no WordPress)

1. WordPress Admin → **Usuários → [seu usuário] → Editar**
2. Role até **Application Passwords**
3. Nome: `AdForge` → clique **Add New Application Password**
4. Copie a senha gerada (formato: `xxxx xxxx xxxx xxxx xxxx xxxx`)
5. Adicione ao `~/.adforge/.env`:

```env
WP_URL=https://seusite.com.br
WP_USER=renato
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

### Como funciona

```
GET /wp-json/wp/v2/pages
Authorization: Basic base64(renato:xxxx xxxx xxxx xxxx xxxx xxxx)
```

O WordPress verifica o Application Password e concede permissão conforme o papel  
do usuário (Administrator = acesso total à REST API).

---

## 3. Plugins de segurança — configuração necessária

### Wordfence Security 8.2.2 ⚠️ BLOQUEIO POR PADRÃO

**Problema:** Wordfence desabilita Application Passwords por padrão (proteção contra bots).

**Solução obrigatória antes do primeiro teste:**

1. WordPress Admin → **Wordfence → All Options**
2. Seção **"Login Security"** → desmarcar **"Disable WordPress Application Passwords"**
3. Salvar

**Se ainda bloquear (WAF):**
1. Wordfence → Firewall → Manage WAF → mudar para **Learning Mode**
2. Em outra aba: gere o Application Password
3. Volte → mude de volta para **Enabled and Protecting**

**Whitelist por IP (alternativa mais robusta):**
- Wordfence → Tools → IP Allowlist → adicionar IP do servidor/máquina
- Todo tráfego desse IP bypassa as verificações do WAF

### Really Simple Security 9.6.1

RSL geralmente não bloqueia REST API autenticada com Application Password.  
Se bloquear:
- Settings → Security → REST API → garantir que não está com "Disable REST API" ativo
- Ou whitelist o namespace: `wp/v2`

---

## 4. Estrutura do `_elementor_data`

O Elementor armazena o conteúdo da página como JSON no `wp_postmeta`,  
campo `_elementor_data`. A estrutura é uma árvore de elementos aninhados:

```
Page
└── Section (elType: "section")
    └── Column (elType: "column")
        └── Widget (elType: "widget", widgetType: "heading")
            └── settings: { title: "Texto aqui" }
```

### JSON real (simplificado)

```json
[
  {
    "id": "abc123",
    "elType": "section",
    "settings": { "content_width": "full" },
    "elements": [
      {
        "id": "def456",
        "elType": "column",
        "settings": { "_column_size": 100 },
        "elements": [
          {
            "id": "ghi789",
            "elType": "widget",
            "widgetType": "heading",
            "settings": {
              "title": "Bem-vindo ao SPID CUP 2026",
              "title_html_tag": "h1",
              "align": "center"
            },
            "elements": []
          }
        ]
      }
    ]
  }
]
```

### Nota sobre serialização dupla

O WordPress retorna `_elementor_data` como **string JSON dentro do JSON da API**:

```python
# Errado (retorna string):
page["meta"]["_elementor_data"]  # → '[ { "id": "abc123", ... } ]'

# Correto (parse duplo — já feito pelo wp_client.parse_elementor_data):
import json
elements = json.loads(page["meta"]["_elementor_data"])  # → lista Python
```

---

## 5. Widgets: seguros vs. arriscados

### ✅ Seguros para editar via API

| widgetType | Campo editável | Valor |
|---|---|---|
| `heading` | `settings.title` | string (aceita HTML básico) |
| `text-editor` | `settings.editor` | HTML completo |
| `button` | `settings.text` | string |
| `button` | `settings.link.url` | URL string |
| `image` | `settings.image.url` | URL da imagem |
| `image` | `settings.caption` | string |
| `icon-box` | `settings.title_text` | string |
| `icon-box` | `settings.description_text` | string |
| `icon-list` | `settings.icon_list[n].text` | string por item |

**Regra:** edite APENAS o conteúdo dentro de `settings`. Nunca o `id`, `elType` ou `widgetType`.

### 🚫 Não tocar (alto risco de quebrar a página)

| elType / widgetType | Por quê não tocar |
|---|---|
| `section`, `column`, `container` | Estrutura de layout — qualquer erro desfaz o design |
| `inner-section` | Idem |
| Qualquer `id` | Elementor usa como âncora CSS e JS |
| `settings._column_size` | Define proporção da grade |
| `settings.content_width` | Define layout full/boxed |
| `settings.__globals__` | Referências ao Global Kit (cores, tipografia) |
| `_elementor_css` | Cache CSS — nunca editar diretamente (zerar só para limpar cache) |

### ⚠️ Revisar caso a caso

| widgetType | Observação |
|---|---|
| `video` | URL editável, mas configurações de player são complexas |
| `countdown` | Data editável (`settings.due_date`), formato específico |
| `form` | Campos de email/ação — risco de quebrar fluxo de lead |
| `testimonial-carousel` | Slides são array, edição cuidadosa por índice |

---

## 6. Fluxo de edição seguro

```python
from wp_client import WPClient

wp = WPClient(WP_URL, WP_USER, WP_APP_PASSWORD)

# 1. Lê a página com contexto de edição
page = wp.get_page_meta(PAGE_ID)

# 2. Parseia o tree do Elementor
elements = wp.parse_elementor_data(page)

# 3. Encontra o widget alvo
headings = wp.find_widgets(elements, "heading")
# → inspecione headings[0]["id"] e headings[0]["settings"]["title"]

# 4. Atualiza SOMENTE o campo de conteúdo (in-place no tree)
wp.update_widget_setting(elements, widget_id="ghi789", setting_key="title", new_value="SPID FEST 2027 — Novo Texto")

# 5. Envia de volta (inclui limpeza de cache CSS)
wp.push_elementor_data(PAGE_ID, elements)
```

---

## 7. Handling de erros

| Código | Classe | Causa provável | Ação |
|---|---|---|---|
| 401 | `WPAuthError` | Application Password inválido ou expirado | Regerar em Usuários → Application Passwords |
| 403 | `WPAuthError` | Wordfence bloqueando | Desabilitar "Disable Application Passwords" no Wordfence |
| 403 | `WPAuthError` | Usuário sem permissão | Verificar papel (deve ser Administrator ou Editor) |
| 404 | `WPNotFoundError` | page_id errado | Confirmar ID em `list_pages()` |
| 500 | `requests.HTTPError` | Erro no WordPress | Ver log do WordPress (`/wp-content/debug.log`) |

### Handling no código

```python
try:
    pages = wp.list_pages()
except WPAuthError as e:
    # Envia alerta via Telegram ao Renato
    tg.send(chat_id, "❌ Erro de auth WordPress: %s" % e)
except Exception as e:
    tg.send(chat_id, "❌ Erro WordPress inesperado: %s" % e)
```

---

## 8. Exposição do `_elementor_data` na REST API

Por padrão, o WordPress não expõe campos de post_meta na REST API  
a menos que estejam registrados. O Elementor **registra automaticamente**  
`_elementor_data` em versões recentes — mas se não aparecer no response,  
adicione ao `functions.php` do tema ativo:

```php
// Expõe _elementor_data na REST API
add_action('init', function() {
    register_post_meta('page', '_elementor_data', [
        'show_in_rest' => true,
        'single'       => true,
        'type'         => 'string',
        'auth_callback' => function() {
            return current_user_can('edit_posts');
        },
    ]);
});
```

---

## 9. Arquivos do ambiente

```
~/.adforge/
├── venv_wp/              — virtual env Python (requests 2.34.2)
├── docs/
│   └── wordpress_integration.md  — este arquivo
└── wp/
    ├── wp_client.py      — thin client REST API + helpers Elementor
    └── test_read.py      — teste de leitura (seguro, sem modificações)
```

---

## 10. Próximos passos — Fase 2

A Fase 2 integra o WordPress ao fluxo de aprovação Telegram:

```
daily-analyst detecta necessidade de atualizar LP
    ↓
Gera diff: campo atual → campo proposto
    ↓
Envia via bot Telegram com botões [✅ Aprovar] [❌ Rejeitar] [✏️ Modificar]
    ↓
Renato aprova
    ↓
wp_client.push_elementor_data() executa a atualização
    ↓
decisions.log registra: página, campo, valor anterior, valor novo
```

**Itens a implementar na Fase 2:**
- [ ] `meta_actions.py` — integra wp_client ao fluxo bot (Fase 2 do bot)
- [ ] Cache de IDs de páginas (evitar listar a cada execução)
- [ ] Backup do `_elementor_data` antes de cada edição (rollback via /desfazer_ultima)
- [ ] Teste de smoke após update (GET na página e valida se widget foi atualizado)
- [ ] Credenciais WP_URL / WP_USER / WP_APP_PASSWORD adicionadas ao .env

---

*Última atualização: 2026-07-11 — Orion (aiox-master)*
