"""Testes dos leitores de página. Rode: python -m unittest discover tests  (dentro da pasta do sistema)."""
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

import extrator  # noqa: E402
import fonte_pci  # noqa: E402
import municipios_sp as mun  # noqa: E402


def ler(nome):
    with open(os.path.join(AQUI, "fixtures", nome), encoding="utf-8") as f:
        return f.read()


class TestLista(unittest.TestCase):
    def setUp(self):
        self.itens = fonte_pci.parse_lista(ler("lista_sudeste.html"), "SP")
        self.por_org = {i["orgao"]: i for i in self.itens}

    def test_so_sp(self):
        self.assertEqual(len(self.itens), 6)
        self.assertNotIn("Prefeitura do Rio", self.por_org)

    def test_campos_basicos(self):
        b = self.por_org["Câmara de Boituva"]
        self.assertEqual(b["vagas"], 7)
        self.assertEqual(b["salario_max"], 8595.15)
        self.assertEqual(b["insc_fim"], "2026-11-09")
        self.assertEqual(b["niveis"], ["Fundamental", "Médio", "Técnico", "Superior"])
        self.assertTrue(b["id"].startswith("pci:camara-de-boituva"))

    def test_periodos(self):
        s = self.por_org["SETEC - Serviços Técnicos Gerais de Campinas"]
        self.assertEqual((s["insc_inicio"], s["insc_fim"]), ("2026-09-08", "2026-12-04"))
        f = self.por_org["FEG - Fundação Educacional Guaçuana"]
        self.assertEqual(f["insc_fim"], "2026-11-19")
        self.assertEqual(f["insc_obs"], "Prorrogado")
        sb = self.por_org["Prefeitura de Santa Bárbara d'Oeste"]
        self.assertEqual((sb["insc_inicio"], sb["insc_fim"]), ("2026-11-03", "2026-12-07"))
        self.assertEqual(sb["salario_unidade"], "hora")
        d = self.por_org["Defensoria Pública"]
        self.assertEqual((d["insc_inicio"], d["insc_fim"]), ("2026-11-06", "2026-11-25"))
        self.assertIsNone(d["salario_max"])
        pm = self.por_org["PM SP - Polícia Militar do Estado de São Paulo"]
        self.assertEqual(pm["vagas"], 2000)
        self.assertEqual(pm["niveis"], ["Médio"])

    def test_cidade(self):
        self.assertEqual(fonte_pci.cidade_do_orgao("SETEC - Serviços Técnicos Gerais de Campinas",
                                                   "SETEC Campinas - SP abre concurso"), "Campinas")
        self.assertEqual(fonte_pci.cidade_do_orgao("Prefeitura de Santa Bárbara d'Oeste", ""), "Santa Bárbara d'Oeste")
        self.assertEqual(fonte_pci.cidade_do_orgao("FEG - Fundação Educacional Guaçuana", "Fundação Educacional Guaçuana - SP",
                                                   "no município de Mogi Guaçu, abriu"), "Mogi Guaçu")


class TestDetalhe(unittest.TestCase):
    def test_setec(self):
        d = fonte_pci.parse_detalhe(ler("detalhe_setec.html"))
        self.assertEqual(d["prova_data"], "2027-01-17")
        self.assertEqual(d["insc_inicio_txt"], "2026-09-08")
        self.assertEqual(d["insc_fim_txt"], "2026-12-04")
        self.assertEqual((d["taxa_min"], d["taxa_max"]), (48.0, 78.0))
        self.assertEqual((d["salario_min_txt"], d["salario_max_txt"]), (2571.28, 10428.05))
        self.assertEqual(d["site_inscricao"], "indepac.selecao.net.br")
        self.assertEqual(len(d["cargos"]), 14)
        medio = [c["cargo"] for c in d["cargos"] if "Médio" in c["niveis"]]
        self.assertIn("Agente de Suporte Técnico (4 vagas + CR)", medio)
        ti = [c["cargo"] for c in d["cargos"] if extrator.eh_ti(c["cargo"])]
        self.assertEqual(ti, ["Agente de Suporte Técnico (4 vagas + CR)", "Analista Técnico (Informática) (1 vaga + CR)"])
        self.assertIn("Campinas", d["cidades_citadas"])
        self.assertNotIn("São Paulo", d["cidades_citadas"])
        self.assertNotIn("apostila", d["texto"].lower())

    def test_boituva(self):
        d = fonte_pci.parse_detalhe(ler("detalhe_boituva.html"))
        self.assertEqual(d["prova_data"], "2026-12-06")
        self.assertEqual(d["insc_fim_txt"], "2026-11-09")
        self.assertEqual((d["taxa_min"], d["taxa_max"]), (54.0, 87.0))
        self.assertIn("vale-alimentação", d["salario_frase"])
        self.assertNotIn("beneficios", d)  # já está na frase do salário
        self.assertEqual(d["publicado"], "2026-09-15")


class TestUtil(unittest.TestCase):
    def test_distancia(self):
        self.assertLess(mun.distancia_km("Nova Odessa", "Americana"), 15)
        self.assertTrue(25 <= mun.distancia_km("Nova Odessa", "Campinas") <= 45)
        self.assertTrue(110 <= mun.distancia_km("Nova Odessa", "São Paulo") <= 160)
        self.assertIsNone(mun.distancia_km("Nova Odessa", "Belém"))

    def test_ti(self):
        self.assertTrue(extrator.eh_ti("Técnico em Informática"))
        self.assertTrue(extrator.eh_ti("Analista de Sistemas"))
        self.assertFalse(extrator.eh_ti("Auxiliar de Serviços Gerais"))
        self.assertFalse(extrator.eh_ti("Motorista"))

    def test_datas(self):
        ini, fim, obs = extrator.data_ce("Reaberto até 30/11/2026")
        self.assertEqual((ini, fim and fim.isoformat(), obs), (None, "2026-11-30", "Reaberto"))
        ds = extrator.datas_extenso("de 8 de setembro a 4 de dezembro de 2026")
        self.assertEqual([d.isoformat() for d in ds], ["2026-09-08", "2026-12-04"])


if __name__ == "__main__":
    unittest.main()
