"""Busca os concursos e publica o site estático em docs/ (usado pelo GitHub Actions).

Rode:  python coletar.py
- Usa dados/cache.json para não baixar de novo os detalhes que já tem.
- Gera docs/dados/concursos.json, docs/dados/meta.json e docs/dados/municipios.json.
- Copia static/index.html para docs/index.html em modo "site estático".
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import db  # noqa: E402

TMP = tempfile.mkdtemp()
db.PASTA = TMP
db.ARQUIVO = os.path.join(TMP, "coleta.db")

import app  # noqa: E402
import atualizador  # noqa: E402
import municipios_sp as mun  # noqa: E402
import seed  # noqa: E402

CACHE = os.path.join(AQUI, "dados", "cache.json")
DOCS = os.path.join(AQUI, "docs")
REPO = os.environ.get("GITHUB_REPOSITORY", "guiduraesz-netizen/radar-concurso")
DIAS_MANTER_ENCERRADOS = 45
PESSOAIS = ("acompanhar", "status", "prioridade", "inscrito", "notas", "oculto")


def carregar_cache():
    if not os.path.exists(CACHE):
        return 0
    with open(CACHE, encoding="utf-8") as f:
        linhas = json.load(f)
    for r in linhas:
        db.salvar(r)
    return len(linhas)


def salvar_cache():
    limite = (date.today() - timedelta(days=DIAS_MANTER_ENCERRADOS)).isoformat()
    linhas = []
    for r in db.listar():
        if not r.get("ativo") and (r.get("insc_fim") or "") < limite and not r.get("manual"):
            continue
        linhas.append({k: v for k, v in r.items() if k in db.CAMPOS})
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(linhas, f, ensure_ascii=False, indent=0, sort_keys=True)


def publicar_site():
    os.makedirs(os.path.join(DOCS, "dados"), exist_ok=True)
    limite = (date.today() - timedelta(days=DIAS_MANTER_ENCERRADOS)).isoformat()
    itens = []
    for c in app.montar_lista():
        if not c["ativo"] and (c.get("insc_fim") or "") < limite and not c["manual"]:
            continue
        for k in PESSOAIS:
            c.pop(k, None)
        c.pop("distancia_km", None)        # o navegador calcula a partir da cidade escolhida
        c.pop("menor_dist_citada", None)
        c.pop("dias_fim", None)
        c.pop("dias_prova", None)
        itens.append(c)
    itens.sort(key=lambda c: (c.get("insc_fim") or "9999", c["orgao"]))
    with open(os.path.join(DOCS, "dados", "concursos.json"), "w", encoding="utf-8") as f:
        json.dump(itens, f, ensure_ascii=False, separators=(",", ":"))
    ult = db.ultima_execucao() or {}
    meta = {"inicio": ult.get("inicio"), "fim": ult.get("fim"), "total": ult.get("total"), "novos": ult.get("novos"),
            "erros": ult.get("erros") or [], "log": atualizador.estado.get("log", [])[-60:], "repo": REPO}
    with open(os.path.join(DOCS, "dados", "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    coords = {v[0]: [v[1], v[2]] for v in mun.MUNICIPIOS.values()}
    with open(os.path.join(DOCS, "dados", "municipios.json"), "w", encoding="utf-8") as f:
        json.dump(coords, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(AQUI, "static", "index.html"), encoding="utf-8") as f:
        html = f.read()
    flag = f'<script>window.MODO_ESTATICO = true; window.REPO = "{REPO}";</script>\n</head>'
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(html.replace("</head>", flag, 1))
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    return len(itens)


def main():
    so_publicar = "--so-publicar" in sys.argv
    db.con()
    n = carregar_cache()
    seed.semear()
    print(f"Cache: {n} concursos", flush=True)
    if not so_publicar:
        atualizador.estado.update(rodando=True, inicio=db.agora(), novos=0, erros=[], log=[])
        atualizador._rodar("--forcar" in sys.argv)
    salvar_cache()
    total = publicar_site()
    print(f"Site gerado com {total} concursos em docs/", flush=True)
    erros = (db.ultima_execucao() or {}).get("erros") or []
    for e in erros:
        print("AVISO:", e, flush=True)


if __name__ == "__main__":
    main()
