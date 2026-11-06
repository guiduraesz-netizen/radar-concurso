"""Concursos PREVISTOS (ainda sem inscrição) levantados na pesquisa de 05/11/2026.
A PCI só lista concursos com inscrição aberta, então estes entram como cadastro manual.
São gravados só na primeira vez que o sistema roda; depois você edita/apaga pela tela."""
import db

PREVISTOS = [
    {"id": "manual:cetesb", "orgao": "CETESB – Companhia Ambiental do Estado de SP",
     "cargos_resumo": "Analista de Tecnologia da Informação (4 vagas) e outros", "niveis": ["Médio", "Superior"],
     "vagas_txt": "107 vagas (4 de TI)", "salario_max": 11620.30, "cidade": "São Paulo",
     "notas_fonte": "Banca FCC contratada; edital anunciado para novembro/2026. Analista de TI: R$ 8.654,10 (pode chegar a R$ 11.620,30). Provas em 10 cidades, incluindo Campinas.",
     "url": "https://www.novaconcursos.com.br/portal/?p=317118"},
    {"id": "manual:camara-guarulhos", "orgao": "Câmara Municipal de Guarulhos",
     "cargos_resumo": "Consultor Legislativo – Administração de Rede; Consultor Legislativo – Segurança da Informação; Técnico Legislativo",
     "niveis": ["Médio", "Superior"], "vagas_txt": "40 vagas", "salario_max": None, "cidade": "Guarulhos",
     "notas_fonte": "Edital previsto para o 2º semestre de 2026. Taxa prevista: R$ 76,90 (médio) e R$ 111,51 (superior).",
     "url": "https://tribunadejundiai.com.br/economia/concursos/concurso-camara-guarulhos-2026-vagas-edital-provas/"},
    {"id": "manual:pref-campinas", "orgao": "Prefeitura de Campinas",
     "cargos_resumo": "Analista de Tecnologia da Informação (2 vagas, R$ 7.930,17); Agente de Suporte a Tecnologias (2 vagas, R$ 4.101,84) e muitos outros",
     "niveis": ["Fundamental", "Médio", "Superior"], "vagas_txt": "485 vagas previstas", "salario_max": 7930.17,
     "cidade": "Campinas", "notas_fonte": "FCC homologada em 22/10/2026; edital sem data.",
     "url": "https://tribunadejundiai.com.br/economia/concursos/concurso-prefeitura-campinas-485-vagas/"},
    {"id": "manual:coren-sp", "orgao": "COREN-SP – Conselho Regional de Enfermagem",
     "cargos_resumo": "Assistente Administrativo (29 vagas, R$ 4.850,00, CLT) e cargos de nível superior",
     "niveis": ["Médio", "Superior"], "vagas_txt": "76 vagas", "salario_max": 4850.0, "cidade": "São Paulo",
     "notas_fonte": "Banca Quadrix contratada em ago/2026. Provas em São Paulo, Marília, S. J. Campos, Ribeirão Preto e S. J. Rio Preto.",
     "url": "https://concursosnobrasil.com/concursos/sp/2026/08/18/concurso-coren-sp-tem-edital-previsto-para-76-vagas-de-niveis-medio-e-superior/"},
    {"id": "manual:funcamp", "orgao": "FUNCAMP – Fundação de Desenvolvimento da Unicamp",
     "cargos_resumo": "Técnico de Suporte em Informática (editais avulsos, CLT)", "niveis": ["Técnico"],
     "vagas_txt": "1 por edital", "salario_max": 4099.64, "cidade": "Campinas",
     "notas_fonte": "Abre seletivos de TI várias vezes por ano, com prazo de ~2 semanas. Olhe os editais toda semana.",
     "url": "https://www.funcamp.unicamp.br"},
    {"id": "manual:cnu-2027", "orgao": "CNU 2027 – Concurso Nacional Unificado", "uf": "NACIONAL", "escopo": "NACIONAL",
     "cargos_resumo": "Diversos cargos federais (TI ainda não confirmado)", "niveis": ["Superior"],
     "vagas_txt": "2.000 a 3.000 (estimativa)", "salario_max": None,
     "notas_fonte": "Prova prevista para o 2º semestre de 2027; depende de autorização.",
     "url": "https://blog.grancursosonline.com.br/cnu-2027-ate-3-mil-vagas/amp/"},
    {"id": "manual:banco-do-brasil", "orgao": "Banco do Brasil", "uf": "NACIONAL", "escopo": "NACIONAL",
     "cargos_resumo": "Escriturário (Agente Comercial; Agente de Tecnologia não confirmado)", "niveis": ["Médio"],
     "vagas_txt": "A definir", "salario_max": 4189.05,
     "notas_fonte": "Total com benefícios ~R$ 6.412,42. Banca em escolha (Cesgranrio, FGV ou Cebraspe).",
     "url": "https://diariodopara.com.br/concursos-e-empregos/concurso-banco-do-brasil-avanca-e-3-bancas-disputam-organizacao-veja-salarios-e-requisitos/"},
    {"id": "manual:caixa", "orgao": "Caixa Econômica Federal", "uf": "NACIONAL", "escopo": "NACIONAL",
     "cargos_resumo": "Técnico Bancário – Tecnologia da Informação", "niveis": ["Médio"],
     "vagas_txt": "A definir", "salario_max": 3762.0,
     "notas_fonte": "Edital esperado em 2027. Em 2024 houve 2 mil vagas de TI (salário de referência R$ 3.762).",
     "url": "https://portaldeprefeitura.com.br/oportunidades/oncurso-caixa-tecnico-bancario-edital-previsto-2027/630444/"},
]


def semear():
    if db.con().execute("SELECT COUNT(*) FROM concursos WHERE manual=1").fetchone()[0]:
        return
    if db.get_config().get("seed_feito"):
        return
    for p in PREVISTOS:
        item = {"fonte": "Manual (previsto)", "uf": p.get("uf", "SP"), "escopo": p.get("escopo", "SP"),
                "ativo": 1, "manual": 1, "detalhe": {"descricao": p["notas_fonte"], "previsto": True},
                **{k: v for k, v in p.items() if k != "notas_fonte"}}
        db.salvar(item)
        db.salvar_pessoal(p["id"], {"status": "Previsto"})
    db.set_config("seed_feito", "1")
