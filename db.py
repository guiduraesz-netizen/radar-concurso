"""Banco de dados local (SQLite, um arquivo só: dados/concursos.db)."""
import json
import os
import sqlite3
import threading
from datetime import datetime

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
ARQUIVO = os.path.join(PASTA, "concursos.db")
_lock = threading.RLock()

CAMPOS = ["id", "fonte", "url", "orgao", "titulo", "uf", "escopo", "insc_inicio", "insc_fim", "insc_obs",
          "vagas_txt", "vagas", "salario_max", "salario_unidade", "cargos_resumo", "niveis", "cidade",
          "distancia_km", "detalhe", "detalhe_em", "primeiro_visto", "ultimo_visto", "ativo", "manual"]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS concursos (
  id TEXT PRIMARY KEY, fonte TEXT, url TEXT, orgao TEXT, titulo TEXT, uf TEXT, escopo TEXT,
  insc_inicio TEXT, insc_fim TEXT, insc_obs TEXT, vagas_txt TEXT, vagas INTEGER,
  salario_max REAL, salario_unidade TEXT, cargos_resumo TEXT, niveis TEXT, cidade TEXT,
  distancia_km INTEGER, detalhe TEXT, detalhe_em TEXT, primeiro_visto TEXT, ultimo_visto TEXT,
  ativo INTEGER DEFAULT 1, manual INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pessoal (
  id TEXT PRIMARY KEY, acompanhar INTEGER DEFAULT 0, status TEXT, prioridade TEXT,
  inscrito INTEGER DEFAULT 0, notas TEXT, oculto INTEGER DEFAULT 0, atualizado_em TEXT
);
CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS execucoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, inicio TEXT, fim TEXT, total INTEGER, novos INTEGER, erros TEXT
);
"""

CONFIG_PADRAO = {"cidade_base": "Nova Odessa"}


def conectar():
    os.makedirs(PASTA, exist_ok=True)
    c = sqlite3.connect(ARQUIVO, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


_con = None


def con():
    global _con
    with _lock:
        if _con is None:
            _con = conectar()
            _con.executescript(ESQUEMA)
            _con.commit()
        return _con


def agora():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- config
def get_config():
    cfg = dict(CONFIG_PADRAO)
    for r in con().execute("SELECT chave, valor FROM config"):
        cfg[r["chave"]] = r["valor"]
    return cfg


def set_config(chave, valor):
    with _lock:
        con().execute("INSERT INTO config(chave, valor) VALUES(?,?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
                      (chave, str(valor)))
        con().commit()


# ---------------------------------------------------------------- concursos
def existente(id_):
    r = con().execute("SELECT * FROM concursos WHERE id=?", (id_,)).fetchone()
    return dict(r) if r else None


def salvar(item):
    """Insere ou atualiza um concurso (campos ausentes não apagam os existentes)."""
    with _lock:
        atual = existente(item["id"])
        dados = dict(atual or {})
        for k, v in item.items():
            if k in CAMPOS:
                if k in ("niveis", "detalhe") and not isinstance(v, str) and v is not None:
                    v = json.dumps(v, ensure_ascii=False)
                dados[k] = v
        dados.setdefault("primeiro_visto", agora())
        cols = [k for k in CAMPOS if k in dados]
        con().execute(
            f"INSERT INTO concursos({','.join(cols)}) VALUES({','.join('?' * len(cols))}) "
            f"ON CONFLICT(id) DO UPDATE SET " + ",".join(f"{k}=excluded.{k}" for k in cols if k != "id"),
            [dados[k] for k in cols])
        con().commit()
        return atual is None


def marcar_inativos(ids_ativos):
    """Concursos da PCI que sumiram da lista = inscrições encerradas."""
    with _lock:
        ids = set(ids_ativos)
        for r in con().execute("SELECT id FROM concursos WHERE manual=0 AND ativo=1").fetchall():
            if r["id"] not in ids:
                con().execute("UPDATE concursos SET ativo=0 WHERE id=?", (r["id"],))
        con().commit()


def excluir_manual(id_):
    with _lock:
        con().execute("DELETE FROM concursos WHERE id=? AND manual=1", (id_,))
        con().execute("DELETE FROM pessoal WHERE id=?", (id_,))
        con().commit()


def listar():
    rows = con().execute("""SELECT c.*, p.acompanhar, p.status, p.prioridade, p.inscrito, p.notas, p.oculto
                            FROM concursos c LEFT JOIN pessoal p ON p.id=c.id""").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for k in ("niveis", "detalhe"):
            try:
                d[k] = json.loads(d[k]) if d.get(k) else ([] if k == "niveis" else {})
            except ValueError:
                d[k] = [] if k == "niveis" else {}
        out.append(d)
    return out


# ---------------------------------------------------------------- dados pessoais
def salvar_pessoal(id_, campos):
    permitidos = {"acompanhar", "status", "prioridade", "inscrito", "notas", "oculto"}
    campos = {k: v for k, v in campos.items() if k in permitidos}
    if not campos:
        return
    with _lock:
        con().execute("INSERT OR IGNORE INTO pessoal(id) VALUES(?)", (id_,))
        sets = ",".join(f"{k}=?" for k in campos)
        con().execute(f"UPDATE pessoal SET {sets}, atualizado_em=? WHERE id=?", [*campos.values(), agora(), id_])
        con().commit()


# ---------------------------------------------------------------- execuções
def registrar_execucao(inicio, total, novos, erros):
    with _lock:
        con().execute("INSERT INTO execucoes(inicio, fim, total, novos, erros) VALUES(?,?,?,?,?)",
                      (inicio, agora(), total, novos, json.dumps(erros, ensure_ascii=False)))
        con().commit()


def ultima_execucao():
    r = con().execute("SELECT * FROM execucoes ORDER BY id DESC LIMIT 1").fetchone()
    if not r:
        return None
    d = dict(r)
    d["erros"] = json.loads(d["erros"] or "[]")
    return d
