"""Funções que tiram informação de textos em português (datas, valores, níveis, cidades)."""
import re
from datetime import date

MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
         "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}

RE_DATA_EXTENSO = re.compile(
    r"(\d{1,2})(?:º|°)?\s+de\s+(janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|"
    r"outubro|novembro|dezembro)(?:\s+de\s+(\d{4}))?", re.I)
RE_DATA_NUM = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
RE_VALOR = re.compile(r"R\$\s*([\d.]+,\d{2})")


def valor(txt):
    """'4.850,00' -> 4850.0"""
    try:
        return float(txt.replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


def valores(txt):
    return [v for v in (valor(m) for m in RE_VALOR.findall(txt or "")) if v is not None]


def datas_extenso(txt, ano_padrao=None):
    """Acha datas tipo '17 de janeiro de 2027' (ou '8 e 18 de setembro de 2026' -> pega as duas)."""
    out = []
    for m in RE_DATA_EXTENSO.finditer(txt or ""):
        d, mes, a = int(m.group(1)), MESES[m.group(2).lower()], m.group(3)
        ano = int(a) if a else None
        if ano is None:
            # procura o ano mais próximo à frente (ex.: "8 de setembro a 4 de dezembro de 2026")
            resto = (txt or "")[m.end():m.end() + 60]
            am = re.search(r"\b(20\d{2})\b", resto)
            ano = int(am.group(1)) if am else (ano_padrao or date.today().year)
        try:
            out.append(date(ano, mes, d))
        except ValueError:
            pass
    for m in RE_DATA_NUM.finditer(txt or ""):
        try:
            out.append(date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        except ValueError:
            pass
    return out


def frases(txt):
    partes = re.split(r"(?<=[.;!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9])|\n+", txt or "")
    return [p.strip() for p in partes if p.strip()]


NIVEIS = ("Fundamental", "Médio", "Técnico", "Superior")


def niveis_de(txt):
    t = (txt or "").lower()
    out = []
    if "fundamental" in t or "alfabetizado" in t:
        out.append("Fundamental")
    if "médio" in t or "medio" in t:
        out.append("Médio")
    if "técnico" in t or "tecnico" in t:
        out.append("Técnico")
    if "superior" in t or "graduação" in t:
        out.append("Superior")
    return out


def data_ce(texto, hoje=None):
    """Interpreta a coluna de inscrições da PCI.
    Formatos: '18/11/2026', '06 a 25/11/2026', '03/11 a 07/12/2026',
              '08/09/2026 a 04/12/2026', 'Prorrogado até 09/11/2026', 'Reaberto até ...'.
    Devolve (inicio, fim, observacao)."""
    t = " ".join((texto or "").split())
    obs = ""
    low = t.lower()
    if "prorrogad" in low:
        obs = "Prorrogado"
    elif "reabert" in low:
        obs = "Reaberto"
    fim = None
    ms = list(RE_DATA_NUM.finditer(t))
    if ms:
        m = ms[-1]
        try:
            fim = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            fim = None
    inicio = None
    if fim and " a " in t:
        ini_txt = t.split(" a ")[0].strip()
        m1 = re.search(r"(\d{1,2})(?:/(\d{1,2}))?(?:/(\d{4}))?", ini_txt)
        if m1:
            d = int(m1.group(1))
            mes = int(m1.group(2)) if m1.group(2) else fim.month
            ano = int(m1.group(3)) if m1.group(3) else (fim.year if mes <= fim.month else fim.year - 1)
            try:
                inicio = date(ano, mes, d)
            except ValueError:
                inicio = None
    return inicio, fim, obs


def resumo_cd(texto):
    """'7 vagas até R$ 8.595,15\nVários Cargos\nFundamental / Médio' -> dict"""
    linhas = [l.strip() for l in (texto or "").split("\n") if l.strip()]
    r = {"vagas_txt": "", "vagas": None, "salario_max": None, "salario_unidade": "mês",
         "cargos_resumo": "", "niveis": []}
    if not linhas:
        return r
    primeira = linhas[0]
    r["vagas_txt"] = primeira.split(" até ")[0].strip()
    mv = re.match(r"([\d.]+)\s+vaga", primeira)
    if mv:
        r["vagas"] = int(mv.group(1).replace(".", ""))
    vs = valores(primeira)
    if vs:
        r["salario_max"] = max(vs)
    if "hora" in primeira.lower():
        r["salario_unidade"] = "hora"
    if len(linhas) >= 2:
        r["cargos_resumo"] = linhas[1]
    if len(linhas) >= 3:
        r["niveis"] = niveis_de(linhas[2])
    return r


PALAVRAS_TI = ("informática", "informatica", "tecnologia da informação", "tecnologia da informacao",
               " ti ", "(ti)", "ti)", "sistemas", "desenvolvimento de sistemas", "programador",
               "analista de dados", "ciência de dados", "ciencia de dados", "redes", "suporte técnico",
               "suporte em", "segurança da informação", "computação", "computacao", "software",
               "banco de dados", "infraestrutura de ti", "devops", "cibersegurança", "telecomunica",
               "processamento de dados", "dados")


def eh_ti(texto):
    t = " " + (texto or "").lower() + " "
    t = t.replace("ti-", "ti ").replace("ti/", "ti ")
    return any(p in t for p in PALAVRAS_TI)


def extrair_detalhe(article_text, cargos_por_nivel, links_texto):
    """Recebe o texto da notícia e devolve campos estruturados."""
    txt = article_text or ""
    fs = frases(txt)
    out = {}

    # ---- prova -------------------------------------------------------------
    prova = None
    for f in fs:
        fl = f.lower()
        if "prova" in fl and not re.search(r"isen[çc]", fl):
            ds = datas_extenso(f) or []
            if ds:
                prova = ds[0]
                out["prova_frase"] = f
                break
    out["prova_data"] = prova.isoformat() if prova else None

    # ---- inscrições --------------------------------------------------------
    for f in fs:
        fl = f.lower()
        if "inscri" in fl and "isen" not in fl.split("inscri")[0][-40:]:
            ds = datas_extenso(f)
            if ds:
                out["insc_frase"] = f
                if len(ds) >= 2:
                    out["insc_inicio_txt"] = ds[0].isoformat()
                    out["insc_fim_txt"] = ds[1].isoformat()
                else:
                    out["insc_fim_txt"] = ds[0].isoformat()
                break

    # ---- taxa --------------------------------------------------------------
    for f in fs:
        if "taxa" in f.lower() and "R$" in f:
            vs = valores(f)
            if vs:
                out["taxa_min"], out["taxa_max"] = min(vs), max(vs)
                out["taxa_frase"] = f
                break

    # ---- salário e benefícios ---------------------------------------------
    for f in fs:
        fl = f.lower()
        if any(k in fl for k in ("remunera", "salári", "salario", "vencimento", "subsídio", "ganho")) and "R$" in f:
            # ignora valores de benefícios citados na mesma frase (vale-alimentação etc.)
            corte = re.split(r"soma|al[ée]m d|vale[- ]|aux[ií]lio|ajuda de custo|benef[ií]cio|acrescid", f, maxsplit=1, flags=re.I)[0]
            vs = valores(corte) or valores(f)
            if vs:
                out["salario_frase"] = f
                out["salario_min_txt"], out["salario_max_txt"] = min(vs), max(vs)
                break
    ben = [f for f in fs if re.search(r"vale[- ]|aux[ií]lio|ajuda de custo|benef[ií]cio|plano de sa[úu]de", f, re.I)
           and f != out.get("salario_frase")]
    if ben:
        out["beneficios"] = " ".join(ben[:2])

    # ---- outras infos curtas -------------------------------------------------
    for chave, padrao in (("jornada", r"jornada|horas semanais"), ("regime", r"regime|celetista|estatut|CLT"),
                          ("validade", r"validade"), ("etapas", r"etapas|prova objetiva|prova pr[áa]tica")):
        for f in fs:
            if re.search(padrao, f, re.I) and f not in (out.get("prova_frase"), out.get("salario_frase")):
                out[chave] = f
                break

    # ---- banca / site de inscrição ------------------------------------------
    site = None
    for t in links_texto:
        tl = t.lower().strip()
        if re.search(r"\.(com|org|br|net)(\.br)?\b|www\.", tl):
            site = t.strip()
            break
    if not site:
        m = re.search(r"\b((?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|gov)(?:\.br)?)\b", txt, re.I)
        if m:
            site = m.group(1)
    out["site_inscricao"] = site
    m = re.search(r"(?:organiza[çc][ãa]o|organizado|banca)[^.]{0,60}?(Funda[çc][ãa]o [A-ZÁ-Ú][\w ]+|Instituto [A-ZÁ-Ú][\w ]+|Vunesp|VUNESP|FGV|Cebraspe|FCC|Indepac|INDEPAC|Consesp|IBAM|Quadrix)", txt)
    if m:
        out["banca"] = m.group(1).strip()

    # ---- cargos -------------------------------------------------------------
    out["cargos"] = cargos_por_nivel
    return out
