"""Teste de ponta a ponta sem internet: simula o site com as páginas de exemplo."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

import db  # noqa: E402

TMP = tempfile.mkdtemp()
db.PASTA = TMP
db.ARQUIVO = os.path.join(TMP, "teste.db")

import app  # noqa: E402
import atualizador  # noqa: E402
import fonte_pci  # noqa: E402
import seed  # noqa: E402


def ler(nome):
    with open(os.path.join(AQUI, "fixtures", nome), encoding="utf-8") as f:
        return f.read()


def falso_baixar(url, **kw):
    if url.endswith("/concursos/sudeste/"):
        return ler("lista_sudeste.html")
    if url.endswith("/concursos/nacional/"):
        return "<html><body><div class='uf'>NACIONAL</div></body></html>"
    if "setec" in url:
        return ler("detalhe_setec.html")
    if "boituva" in url:
        return ler("detalhe_boituva.html")
    return "<html><article><div itemprop='articleBody'><p>Sem detalhes.</p></div></article></html>"


class TestSistema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fonte_pci.baixar = falso_baixar
        atualizador.PAUSA_ENTRE_PAGINAS = 0
        db.con()
        seed.semear()
        atualizador.estado["rodando"] = True
        atualizador._rodar(False)

    def test_lista_api(self):
        itens = {c["orgao"]: c for c in app.montar_lista()}
        s = itens["SETEC - Serviços Técnicos Gerais de Campinas"]
        self.assertEqual(s["cidade"], "Campinas")
        self.assertTrue(25 <= s["distancia_km"] <= 45)
        self.assertEqual(s["prova_data"], "2027-01-17")
        self.assertTrue(s["eh_ti"])
        self.assertIn("Médio", s["niveis"])
        self.assertTrue(any("Agente de Suporte" in x for x in s["cargos_medio"]))
        self.assertIn("CETESB – Companhia Ambiental do Estado de SP", itens)   # seed
        self.assertEqual(itens["Câmara de Boituva"]["cidade"], "Boituva")
        self.assertIsNotNone(atualizador.estado["terminou_em"])

    def test_pessoal_e_http(self):
        srv = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        porta = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{porta}"
        html = urllib.request.urlopen(base + "/").read().decode()
        self.assertIn("Radar de Concursos", html)
        req = urllib.request.Request(base + "/api/pessoal", method="POST",
                                     data=json.dumps({"id": "pci:camara-de-boituva-sp-abre-concursos-com-salarios-de-ate-8595",
                                                      "campos": {"acompanhar": 1, "notas": "estudar regimento"}}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req).read()
        j = json.loads(urllib.request.urlopen(base + "/api/concursos").read())
        b = [c for c in j["itens"] if c["orgao"] == "Câmara de Boituva"][0]
        self.assertTrue(b["acompanhar"])
        self.assertEqual(b["notas"], "estudar regimento")
        req = urllib.request.Request(base + "/api/manual", method="POST",
                                     data=json.dumps({"orgao": "Teste Manual", "cidade": "americana", "salario_max": "4.500,00",
                                                      "insc_fim": "2026-12-01"}).encode(),
                                     headers={"Content-Type": "application/json"})
        r = json.loads(urllib.request.urlopen(req).read())
        j = json.loads(urllib.request.urlopen(base + "/api/concursos").read())
        m = [c for c in j["itens"] if c["id"] == r["id"]][0]
        self.assertEqual((m["cidade"], m["salario_max"]), ("Americana", 4500.0))
        srv.shutdown()


if __name__ == "__main__":
    unittest.main()
