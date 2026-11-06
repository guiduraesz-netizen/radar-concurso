"""Executa a busca: baixa as listas, grava no banco e completa os detalhes de cada concurso."""
import threading
import time
from datetime import date, datetime, timedelta

import db
import fonte_pci

PAUSA_ENTRE_PAGINAS = 0.8      # segundos entre downloads (para não sobrecarregar o site)
DETALHE_VALIDADE_DIAS = 5      # rebaixa o detalhe depois desse tempo

estado = {"rodando": False, "etapa": "", "feito": 0, "total": 0, "inicio": None,
          "novos": 0, "erros": [], "log": [], "terminou_em": None}
_lock = threading.Lock()


def _log(msg):
    linha = f"{datetime.now():%H:%M:%S} {msg}"
    estado["log"] = (estado["log"] + [linha])[-200:]
    print(linha, flush=True)


def _precisa_detalhe(antigo, novo):
    if not antigo or not antigo.get("detalhe_em"):
        return True
    if antigo.get("insc_fim") != novo.get("insc_fim"):
        return True
    try:
        quando = datetime.fromisoformat(antigo["detalhe_em"])
    except ValueError:
        return True
    return datetime.now() - quando > timedelta(days=DETALHE_VALIDADE_DIAS)


def executar(forcar_detalhes=False):
    with _lock:
        if estado["rodando"]:
            return False
        estado.update(rodando=True, etapa="Baixando listas", feito=0, total=0, inicio=db.agora(),
                      novos=0, erros=[], log=[], terminou_em=None)
    threading.Thread(target=_rodar, args=(forcar_detalhes,), daemon=True).start()
    return True


def _rodar(forcar_detalhes):
    try:
        itens, erros = fonte_pci.coletar_listas(log=_log)
        estado["erros"].extend(erros)
        hoje = date.today().isoformat()
        pendentes = []
        for it in itens:
            antigo = db.existente(it["id"])
            it["ultimo_visto"] = db.agora()
            it["ativo"] = 1
            it["manual"] = 0
            if it["escopo"] == "SP":
                it["cidade"] = fonte_pci.cidade_do_orgao(it["orgao"], it["titulo"])
            novo = db.salvar(it)
            if novo:
                estado["novos"] += 1
            if forcar_detalhes or _precisa_detalhe(antigo, it):
                # não vale a pena abrir notícia de inscrição que já terminou
                if not it.get("insc_fim") or it["insc_fim"] >= hoje:
                    pendentes.append(it)
        if itens:
            db.marcar_inativos([i["id"] for i in itens])

        estado.update(etapa="Lendo os detalhes de cada concurso", total=len(pendentes), feito=0)
        _log(f"{len(itens)} concursos na lista, {estado['novos']} novos, {len(pendentes)} para detalhar")
        for it in pendentes:
            try:
                html = fonte_pci.baixar(it["url"])
                det = fonte_pci.parse_detalhe(html)
                atual = {"id": it["id"], "detalhe": det, "detalhe_em": db.agora()}
                if it["escopo"] == "SP" and not it.get("cidade"):
                    cid = fonte_pci.cidade_do_orgao(it["orgao"], it["titulo"], det.get("texto", ""))
                    if not cid and det.get("cidades_citadas"):
                        cid = det["cidades_citadas"][0]   # ex.: FUNCAMP -> Campinas, Unesp -> cidade do câmpus
                    if cid:
                        atual["cidade"] = cid
                db.salvar(atual)
            except Exception as e:  # um concurso com problema não para a busca toda
                _log(f"Falha no detalhe de {it['orgao']}: {e}")
            estado["feito"] += 1
            time.sleep(PAUSA_ENTRE_PAGINAS)
        db.registrar_execucao(estado["inicio"], len(itens), estado["novos"], estado["erros"])
        _log("Atualização concluída")
    except Exception as e:
        estado["erros"].append(f"Erro inesperado: {e}")
        _log(f"Erro inesperado: {e}")
    finally:
        estado.update(rodando=False, etapa="Concluído", terminou_em=db.agora())
