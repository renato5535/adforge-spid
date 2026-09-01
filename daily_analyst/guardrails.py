"""Guardrails do loop agêntico: teto de chamadas API, deadline de execução e budget LLM.

Filosofia: os guardrails NÃO levantam exceção no meio da coleta — eles sinalizam.
O orquestrador checa api_ok()/time_ok()/budget_ok() antes de cada operação cara e,
se algum limite estourou, encerra o loop graciosamente, salva o parcial e marca truncado.
"""
import time


class Guardrails:
    def __init__(self, max_api_calls=50, max_minutes=15, max_llm_brl=10.0):
        self.max_api_calls = int(max_api_calls)
        self.max_seconds = int(float(max_minutes) * 60)
        self.max_llm_brl = float(max_llm_brl)
        self.api_calls = 0
        self.llm_brl = 0.0
        self.start = time.monotonic()
        self.truncated = False
        self.truncate_reason = None

    def elapsed(self):
        return time.monotonic() - self.start

    # --- checagens (chamar ANTES de cada operação cara) ---
    def time_ok(self):
        if self.elapsed() > self.max_seconds:
            self._mark("timeout", "%.0fs > %ss" % (self.elapsed(), self.max_seconds))
            return False
        return True

    def api_ok(self):
        if self.api_calls >= self.max_api_calls:
            self._mark("api_limit", "%s/%s chamadas" % (self.api_calls, self.max_api_calls))
            return False
        return self.time_ok()

    def budget_ok(self):
        if self.llm_brl >= self.max_llm_brl:
            self._mark("llm_budget", "R$%.2f >= R$%.2f" % (self.llm_brl, self.max_llm_brl))
            return False
        return self.time_ok()

    # --- contadores (chamar DEPOIS de cada operação) ---
    def count_api(self, n=1):
        self.api_calls += n

    def add_llm_cost(self, brl):
        self.llm_brl += float(brl)

    def _mark(self, kind, detail):
        if not self.truncated:
            self.truncated = True
            self.truncate_reason = "%s (%s)" % (kind, detail)

    def metrics(self):
        return {
            "api_calls": self.api_calls,
            "max_api_calls": self.max_api_calls,
            "elapsed_seconds": round(self.elapsed(), 1),
            "max_seconds": self.max_seconds,
            "llm_brl": round(self.llm_brl, 4),
            "max_llm_brl": self.max_llm_brl,
            "truncated": self.truncated,
            "truncate_reason": self.truncate_reason,
        }
