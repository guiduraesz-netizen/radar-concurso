"""Coletor do PCI Concursos (pciconcursos.com.br).

- Lista: /concursos/sudeste/ (filtra SP) e /concursos/nacional/
- Detalhe: página da notícia, de onde tiramos cargos, data de prova, taxa etc.
Os links de edital do site ficam atrás de um captcha; não tentamos burlar isso:
guardamos o link da notícia e o site da banca para você abrir no navegador.
"""
import re
import time
import urllib.request
import urllib.error

import htmldom
import extrator
import municipios_sp as mun

BASE = "https://www.pciconcursos.com.br"
LISTAS = {
    "SP": BASE + "/concursos/sudeste/",
    "NACIONAL": BASE + "/concursos/nacional/",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


class ErroFonte(Exception):
    pass


def baixar(url, tentativas=2, timeout=25):
    ultimo = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                bruto = r.read()
                cs = r.headers.get_content_charset() or "utf-8"
                return bruto.decode(cs, errors="replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            ultimo = e
            time.sleep(2 * (i + 1))
    raise ErroFonte(f"Não consegui abrir {url}: {ultimo}")


# ---------------------------------------------------------------------------
# Lista
# ---------------------------------------------------------------------------
def parse_lista(html, escopo):
    """escopo 'SP' (só itens com UF SP) ou 'NACIONAL'. Devolve lista de dicts."""
    raiz = htmldom.parse(html)
    itens = []
    blocos = [n for n in raiz.iter() if n.tag == "div" and ({"da", "na"} & set(n.classes()))]
    for b in blocos:
        a = None
        ca = b.find("div", cls="ca")
        if ca:
            a = ca.find("a")
        if not a or not a.get("href"):
            continue
        uf = (b.find("div", cls="cc").text() if b.find("div", cls="cc") else "").strip()
        if escopo == "SP" and uf != "SP":
            continue
        cd = b.find("div", cls="cd")
        ce = b.find("div", cls="ce")
        resumo = extrator.resumo_cd(cd.text() if cd else "")
        ini, fim, obs = extrator.data_ce(ce.text(sep_br=" ") if ce else "")
        url = a.get("href")
        if url.startswith("/"):
            url = BASE + url
        itens.append({
            "id": "pci:" + url.rstrip("/").rsplit("/", 1)[-1],
            "fonte": "PCI Concursos",
            "url": url,
            "orgao": a.text().strip(),
            "titulo": (a.get("title") or "").strip(),
            "uf": uf or ("NACIONAL" if escopo == "NACIONAL" else ""),
            "escopo": escopo,
            "insc_inicio": ini.isoformat() if ini else None,
            "insc_fim": fim.isoformat() if fim else None,
            "insc_obs": obs,
            **resumo,
        })
    return itens


# ---------------------------------------------------------------------------
# Cidade do órgão
# ---------------------------------------------------------------------------
_TODOS = sorted(((k, v[0]) for k, v in mun.MUNICIPIOS.items() if len(k) >= 3), key=lambda x: -len(x[0]))


# Órgãos conhecidos cujo nome não traz a cidade
_ORGAOS_CIDADE = {"funcamp": "Campinas", "unicamp": "Campinas", "fascamp": "Campinas", "ima campinas": "Campinas",
                  "8o distrito naval": "São Paulo", "8º distrito naval": "São Paulo", "instituto de pesquisas ambientais": "São Paulo"}


def cidade_do_orgao(orgao, titulo, texto=""):
    """Tenta descobrir em qual município de SP fica o órgão."""
    low = (orgao or "").lower() + " " + (titulo or "").lower()
    for chave, cidade in _ORGAOS_CIDADE.items():
        if chave in low:
            return cidade
    cand = []
    if titulo and " - SP" in titulo:
        cand.append(titulo.split(" - SP")[0])
    cand.append(orgao or "")
    for c in cand:
        n = mun.norm(c)
        for chave, oficial in _TODOS:
            if re.search(r"(?<![a-z])" + re.escape(chave) + r"(?![a-z])", n):
                return oficial
    m = re.search(r"munic[ií]pio de ([A-ZÁ-Ú][\wÀ-ú' -]+?)(?:[,.;]| abriu| divulgou| publicou| no Estado)", texto or "")
    if m and mun.nome_oficial(m.group(1)):
        return mun.nome_oficial(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Detalhe
# ---------------------------------------------------------------------------
def parse_detalhe(html):
    raiz = htmldom.parse(html)
    art = raiz.find("article") or raiz
    corpo = None
    for n in art.iter():
        if n.get("itemprop") == "articleBody":
            corpo = n
            break
    corpo = corpo or art
    desc = ""
    for n in art.iter():
        if n.get("itemprop") == "description":
            desc = n.text()
            break
    publicado = None
    ab = art.find("abbr", cls="published")
    if ab and ab.get("title"):
        publicado = ab.get("title")[:10]

    # cargos agrupados pelo parágrafo que vem antes de cada lista
    cargos = []
    titulo_grupo = ""
    for filho in corpo.children:
        if not isinstance(filho, htmldom.Node):
            continue
        if filho.tag == "p":
            t = filho.text()
            if len(t) < 60 and not re.match(r"(segundo|conforme|de acordo|as oportunidades|os cargos)", t, re.I):
                titulo_grupo = t.rstrip(":")
            else:
                titulo_grupo = ""
        elif filho.tag in ("ul", "ol"):
            for li in filho.find_all("li"):
                t = li.text()
                if t:
                    cargos.append({"cargo": t, "grupo": titulo_grupo,
                                   "niveis": extrator.niveis_de(titulo_grupo)})
        elif filho.tag == "table":
            for tr in filho.find_all("tr")[1:]:
                cels = [td.text() for td in tr.find_all("td")]
                if cels:
                    cargos.append({"cargo": " | ".join(cels), "grupo": "", "niveis": extrator.niveis_de(" ".join(cels))})

    # parágrafos de texto (sem a propaganda de apostila/podcast do final)
    paragrafos = []
    for p in corpo.find_all("p"):
        t = p.text()
        if re.search(r"apostila|podcast|Otimize sua prepara|Prefere ouvir", t, re.I):
            continue
        paragrafos.append(t)
    texto = "\n".join(paragrafos)
    links_texto = [a.text() for a in corpo.find_all("a")]

    info = extrator.extrair_detalhe(texto, cargos, links_texto)
    info["descricao"] = desc
    info["texto"] = texto
    info["publicado"] = publicado
    info["cidades_citadas"] = mun.cidades_no_texto(texto)
    return info


def coletar_listas(log=print):
    """Baixa as listas (SP e nacional). Devolve lista de itens e lista de erros."""
    itens, erros = [], []
    for escopo, url in LISTAS.items():
        try:
            html = baixar(url)
            achados = parse_lista(html, escopo)
            if not achados:
                erros.append(f"PCI {escopo}: a página abriu mas não encontrei concursos (o site pode ter mudado o layout).")
            log(f"PCI {escopo}: {len(achados)} concursos")
            itens.extend(achados)
        except ErroFonte as e:
            erros.append(str(e))
            log(str(e))
    return itens, erros
