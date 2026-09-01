"""AdForge WordPress REST API client.

Autenticação via Application Password (WordPress 5.6+, nativo).
Dependência: requests (instalado em ~/.adforge/venv_wp/).

Uso:
    from wp_client import WPClient, WPAuthError
    wp = WPClient("https://seusite.com", "usuario", "xxxx xxxx xxxx xxxx xxxx xxxx")
    pages = wp.list_pages()

Elementor:
    page    = wp.get_page_meta(123)
    tree    = wp.parse_elementor_data(page)      # converte JSON-string → list
    widgets = wp.find_widgets(tree, "heading")   # busca por tipo
    wp.update_widget_setting(tree, "abc123", "title", "Novo Título")
    wp.push_elementor_data(123, tree)            # envia de volta + limpa cache CSS
"""
import json
import cloudscraper
from requests.auth import HTTPBasicAuth


class WPAuthError(Exception):
    """401/403 — credenciais inválidas ou bloqueio de plugin de segurança."""


class WPNotFoundError(Exception):
    """404 — recurso não encontrado."""


class WPClient:
    def __init__(self, base_url, username, app_password):
        self.base     = base_url.rstrip("/") + "/wp-json/wp/v2"
        self.auth     = HTTPBasicAuth(username, app_password)
        self.session  = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
        self.session.auth = self.auth

    # ── HTTP base ─────────────────────────────────────────────────────────────

    def _get(self, endpoint, params=None):
        resp = self.session.get(self.base + endpoint, params=params or {}, timeout=30)
        self._raise_for_status(resp)
        return resp.json()

    def _post(self, endpoint, data):
        resp = self.session.post(self.base + endpoint, json=data, timeout=30)
        self._raise_for_status(resp)
        return resp.json()

    def _raise_for_status(self, resp):
        if resp.status_code in (401, 403):
            try:
                msg = resp.json().get("message", "")
            except Exception:
                msg = resp.text[:200]
            raise WPAuthError("[%d] %s" % (resp.status_code, msg))
        if resp.status_code == 404:
            raise WPNotFoundError("Recurso não encontrado: %s" % resp.url)
        resp.raise_for_status()

    # ── Pages API ─────────────────────────────────────────────────────────────

    def list_pages(self, per_page=20, status="any"):
        """Lista páginas. status='any' inclui rascunhos e publicadas."""
        return self._get("/pages", {"per_page": per_page, "status": status})

    def get_page(self, page_id):
        """Leitura pública (sem meta privada)."""
        return self._get("/pages/%d" % page_id)

    def get_page_meta(self, page_id):
        """Leitura com contexto de edição — inclui _elementor_data nos meta."""
        return self._get("/pages/%d" % page_id, {"context": "edit"})

    def update_page(self, page_id, data):
        """
        Atualiza campos da página.
        data: dict com qualquer combinação de {title, content, status, meta, ...}
        Retorna o objeto atualizado.
        """
        return self._post("/pages/%d" % page_id, data)

    # ── Elementor helpers ─────────────────────────────────────────────────────

    @staticmethod
    def parse_elementor_data(page_response):
        """
        Extrai _elementor_data do response de get_page_meta() e converte para list.

        O WordPress armazena o campo como string JSON serializada dentro do JSON
        da resposta — são dois json.loads() necessários na prática.
        Retorna list (tree de elementos) ou None se não presente.
        """
        meta = page_response.get("meta") or {}
        raw  = meta.get("_elementor_data")
        if not raw:
            return None
        if isinstance(raw, list):
            return raw  # algumas versões já retornam parseado
        return json.loads(raw)

    @staticmethod
    def find_widgets(elements, widget_type=None, _acc=None):
        """
        Busca recursiva por widgets no tree Elementor.

        widget_type: None = todos | 'heading' | 'text-editor' | 'button' | 'image' etc.
        Retorna lista de dicts de widget (referências ao tree original).
        """
        if _acc is None:
            _acc = []
        for el in (elements or []):
            if el.get("elType") == "widget":
                if widget_type is None or el.get("widgetType") == widget_type:
                    _acc.append(el)
            WPClient.find_widgets(el.get("elements", []), widget_type, _acc)
        return _acc

    @staticmethod
    def update_widget_setting(elements, widget_id, setting_key, new_value):
        """
        Localiza o widget com id=widget_id e atualiza settings[setting_key].
        Modifica in-place no tree (não cria cópia).

        REGRA: altere apenas 'settings'. NUNCA altere 'id', 'elType', 'widgetType'.
        Retorna True se encontrou e atualizou, False se widget_id não existe.
        """
        for el in (elements or []):
            if el.get("id") == widget_id and el.get("elType") == "widget":
                el.setdefault("settings", {})[setting_key] = new_value
                return True
            if WPClient.update_widget_setting(el.get("elements", []), widget_id, setting_key, new_value):
                return True
        return False

    def push_elementor_data(self, page_id, elements):
        """
        Envia tree modificado de volta ao WordPress.

        - Serializa elements para string JSON (formato esperado pelo WordPress)
        - Zera _elementor_css para forçar regeneração na próxima visita
        - Retorna response completo do WordPress
        """
        data = {
            "meta": {
                "_elementor_data": json.dumps(elements, ensure_ascii=False),
                "_elementor_css":  "",   # limpa cache CSS do Elementor
            }
        }
        return self.update_page(page_id, data)

    # ── Utilitários ───────────────────────────────────────────────────────────

    @staticmethod
    def summarize_widgets(elements):
        """
        Lista todos os widgets com tipo, ID e preview do conteúdo.
        Útil para inspecionar uma LP antes de editar.
        """
        SAFE   = {"heading", "text-editor", "button", "image", "icon-box", "icon-list"}
        RISKY  = {"section", "column", "container", "inner-section"}
        rows   = []
        widgets = WPClient.find_widgets(elements)
        for w in widgets:
            wt      = w.get("widgetType", "?")
            wid     = w.get("id", "?")
            setts   = w.get("settings", {})
            preview = (
                setts.get("title")
                or setts.get("editor", "")[:60]
                or setts.get("text")
                or ""
            )
            status = "✅ seguro" if wt in SAFE else ("🚫 não editar" if wt in RISKY else "⚠️ revisar")
            rows.append({"id": wid, "type": wt, "status": status, "preview": preview[:60]})
        return rows
