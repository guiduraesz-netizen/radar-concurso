"""Radar de Concursos — servidor web local.

Rode:  python app.py          (abre o navegador em http://127.0.0.1:8765)
Opções: --porta 8765   --sem-navegador   --sem-atualizar
Só usa a biblioteca padrão do Python 3.8+ (não precisa instalar nada).
"""
import argparse
import json
import os
import sys
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import atualizador
import db
import extrator
import municipios_sp as mun
import seed

PASTA = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(PASTA, "static")


def _dias(iso):
    if not iso:
        return None
    try:
        return (date.fromisoformat(iso[:10]) - date.today()).days
    except ValueError:
        return None


def montar_lista():
    cfg = db.get_config()
    base = cfg.get("cidade_base", "Nova Odessa")
    out = []
    for c in db.listar():
        det = c.get("detalhe") or {}
        cargos = det.get("cargos") or []
        textos_ti = " ".join([c.get("orgao") or "", c.get("titulo") or "", c.get("cargos_resumo") or ""] +
                             [x.get("cargo", "") for x in cargos])
        niveis = list(c.get("niveis") or [])
        for x in cargos:
            for n in x.get("niveis") or []:
                if n not in niveis:
                    niveis.append(n)
        cidades = det.get("cidades_citadas") or []
        dist = mun.distancia_km(base, c["cidade"]) if c.get("cidade") else None
        dist_citadas = [d for d in (mun.distancia_km(base, x) for x in cidades) if d is not None]
        cargos_ti = [x["cargo"] for x in cargos if extrator.eh_ti(x.get("cargo", ""))]
        cargos_medio = [x["cargo"] for x in cargos if set(x.get("niveis") or []) & {"Médio", "Técnico"}]
        out.append({
            "id": c["id"], "fonte": c.get("fonte"), "url": c.get("url"), "orgao": c.get("orgao"),
            "titulo": c.get("titulo"), "uf": c.get("uf"), "escopo": c.get("escopo"),
            "cidade": c.get("cidade"), "distancia_km": dist,
            "menor_dist_citada": min(dist_citadas) if dist_citadas else None,
            "cidades_citadas": cidades,
            "insc_inicio": c.get("insc_inicio") or det.get("insc_inicio_txt"),
            "insc_fim": c.get("insc_fim") or det.get("insc_fim_txt"),
            "insc_obs": c.get("insc_obs"), "dias_fim": _dias(c.get("insc_fim") or det.get("insc_fim_txt")),
            "prova_data": det.get("prova_data"), "dias_prova": _dias(det.get("prova_data")),
            "vagas_txt": c.get("vagas_txt"), "vagas": c.get("vagas"),
            "salario_max": c.get("salario_max"), "salario_unidade": c.get("salario_unidade") or "mês",
            "salario_faixa": [det.get("salario_min_txt"), det.get("salario_max_txt")],
            "taxa": [det.get("taxa_min"), det.get("taxa_max")],
            "cargos_resumo": c.get("cargos_resumo"), "cargos": cargos,
            "cargos_ti": cargos_ti, "cargos_medio": cargos_medio,
            "niveis": niveis, "eh_ti": extrator.eh_ti(textos_ti),
            "site_inscricao": det.get("site_inscricao"), "banca": det.get("banca"),
            "descricao": det.get("descricao"), "texto": det.get("texto"),
            "beneficios": det.get("beneficios"), "jornada": det.get("jornada"), "regime": det.get("regime"),
            "etapas": det.get("etapas"), "prova_frase": det.get("prova_frase"),
            "salario_frase": det.get("salario_frase"), "taxa_frase": det.get("taxa_frase"),
            "insc_frase": det.get("insc_frase"),
            "previsto": bool(det.get("previsto")),
            "tem_detalhe": bool(c.get("detalhe_em")),
            "primeiro_visto": c.get("primeiro_visto"), "ultimo_visto": c.get("ultimo_visto"),
            "ativo": bool(c.get("ativo")), "manual": bool(c.get("manual")),
            "acompanhar": bool(c.get("acompanhar")), "status": c.get("status") or "",
            "prioridade": c.get("prioridade") or "", "inscrito": bool(c.get("inscrito")),
            "notas": c.get("notas") or "", "oculto": bool(c.get("oculto")),
        })
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "RadarConcursos/1.0"

    def log_message(self, fmt, *args):  # silencioso
        pass

    # ------------------------------------------------------------ helpers
    def _json(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return {}

    def _arquivo(self, caminho, tipo):
        try:
            with open(caminho, "rb") as f:
                b = f.read()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    # ------------------------------------------------------------ rotas
    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._arquivo(os.path.join(STATIC, "index.html"), "text/html; charset=utf-8")
        if u.path == "/api/concursos":
            return self._json({"itens": montar_lista(), "config": db.get_config(),
                               "ultima": db.ultima_execucao(), "hoje": date.today().isoformat()})
        if u.path == "/api/status":
            return self._json(atualizador.estado)
        if u.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if u.path == "/api/cidades":
            return self._json(sorted({v[0] for v in mun.MUNICIPIOS.values()}))
        self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path)
        b = self._body()
        if u.path == "/api/atualizar":
            ok = atualizador.executar(forcar_detalhes=bool(b.get("forcar")))
            return self._json({"iniciado": ok})
        if u.path == "/api/pessoal":
            if not b.get("id"):
                return self._json({"erro": "id obrigatório"}, 400)
            db.salvar_pessoal(b["id"], b.get("campos") or {})
            return self._json({"ok": True})
        if u.path == "/api/config":
            if "cidade_base" in b:
                nome = mun.nome_oficial(b["cidade_base"])
                if not nome:
                    return self._json({"erro": "Cidade não encontrada em SP"}, 400)
                db.set_config("cidade_base", nome)
            return self._json(db.get_config())
        if u.path == "/api/manual":
            return self._salvar_manual(b)
        if u.path == "/api/manual/excluir":
            db.excluir_manual(b.get("id", ""))
            return self._json({"ok": True})
        self.send_error(404)

    def _salvar_manual(self, b):
        if not (b.get("orgao") or "").strip():
            return self._json({"erro": "Informe o órgão"}, 400)
        id_ = b.get("id") or ("manual:" + str(abs(hash((b["orgao"], db.agora())))))
        cidade = mun.nome_oficial(b.get("cidade") or "") or (b.get("cidade") or None)

        def num(x):
            try:
                return float(str(x).replace(".", "").replace(",", ".")) if x not in (None, "") else None
            except ValueError:
                return None
        antigo = db.existente(id_) or {}
        det = {}
        try:
            det = json.loads(antigo.get("detalhe") or "{}")
        except ValueError:
            det = {}
        det.update({"descricao": b.get("descricao", det.get("descricao", "")),
                    "prova_data": b.get("prova_data") or None,
                    "site_inscricao": b.get("site_inscricao") or det.get("site_inscricao"),
                    "previsto": b.get("previsto", det.get("previsto", False)),
                    "taxa_min": num(b.get("taxa")), "taxa_max": num(b.get("taxa"))})
        item = {"id": id_, "fonte": "Manual", "manual": 1, "ativo": 1,
                "orgao": b["orgao"].strip(), "cargos_resumo": b.get("cargos_resumo", ""),
                "url": b.get("url") or None, "uf": "NACIONAL" if b.get("nacional") else "SP",
                "escopo": "NACIONAL" if b.get("nacional") else "SP", "cidade": cidade,
                "insc_inicio": b.get("insc_inicio") or None, "insc_fim": b.get("insc_fim") or None,
                "salario_max": num(b.get("salario_max")), "vagas_txt": b.get("vagas_txt", ""),
                "niveis": b.get("niveis") or [], "detalhe": det}
        db.salvar(item)
        return self._json({"ok": True, "id": id_})


def main():
    ap = argparse.ArgumentParser(description="Radar de Concursos (local)")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--sem-navegador", action="store_true")
    ap.add_argument("--sem-atualizar", action="store_true", help="não busca automaticamente ao abrir")
    a = ap.parse_args()

    db.con()
    seed.semear()
    srv, porta = None, a.porta
    for porta in range(a.porta, a.porta + 10):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
            break
        except OSError:
            # a porta está ocupada: se for o próprio Radar já aberto, só abre o navegador
            try:
                import urllib.request
                urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/status", timeout=2).read()
                print(f"\n  O Radar de Concursos já está aberto em http://127.0.0.1:{porta}\n", flush=True)
                if not a.sem_navegador:
                    webbrowser.open(f"http://127.0.0.1:{porta}")
                return 0
            except Exception:
                continue
    if srv is None:
        print("  ERRO: não consegui abrir nenhuma porta entre", a.porta, "e", a.porta + 9, flush=True)
        return 1
    url = f"http://127.0.0.1:{porta}"
    print(f"\n  Radar de Concursos rodando em {url}\n  (feche esta janela para desligar)\n", flush=True)
    if not a.sem_atualizar:
        atualizador.executar()
    if not a.sem_navegador:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
