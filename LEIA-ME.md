# Radar de Concursos

**Site online:** https://guiduraesz-netizen.github.io/radar-concurso/

O GitHub busca os concursos sozinho todo dia às **7h e às 19h** (horário de Brasília) e atualiza o site.
Para buscar na hora: aba **Actions** do repositório → **Buscar concursos e publicar site** → **Run workflow**.
No site online, suas estrelas, status, notas e cadastros ficam salvos **no navegador** de cada aparelho
(use o botão **Meus dados** para fazer backup ou passar para outro aparelho).

---

## Versão local (opcional)

Sistema web que roda **no seu computador**. Toda vez que você abre, ele busca os concursos com inscrição aberta no **estado de São Paulo** e os **nacionais**, lê os detalhes de cada um (cargos, salário, datas de inscrição e de prova, taxa, site da banca) e mostra tudo numa página com filtros.

## Como usar

1. Precisa do **Python 3.8 ou mais novo** (não precisa instalar mais nada).
   - Windows: baixe em https://www.python.org/downloads/ e, na instalação, marque **"Add Python to PATH"**.
2. Extraia a pasta onde quiser (ex.: `Documentos\RadarConcursos`).
3. **Windows:** dê dois cliques em `iniciar.bat`.
   **Linux/macOS:** rode `./iniciar.sh` no terminal.
4. O navegador abre sozinho em **http://127.0.0.1:8765** e a busca começa automaticamente.
   - A primeira busca demora uns **3 a 5 minutos**, porque ele abre a página de cada concurso (com uma pausa entre elas para não sobrecarregar o site). Nas próximas vezes só lê o que é novo ou mudou.
   - A janela preta precisa ficar aberta enquanto você usa. Fechou, desligou.

Dica: clique com o botão direito em `iniciar.bat` → *Enviar para* → *Área de trabalho (criar atalho)*.

## O que dá para fazer na tela

- **Atalhos:** *Perto (até 50 km)*, *Só TI*, *Nível médio + R$ 4 mil*, *Fecha em 7 dias*, *Novos*.
- **Filtros:** distância de Nova Odessa (dá para trocar a cidade), escolaridade, só cargos de TI, salário mínimo, prazo, nacionais sim/não.
- **Ordenar** por prazo, distância, salário, data da prova ou mais recentes.
- **Acompanhar (★)**, marcar status (*Vou me inscrever*, *Inscrito*, *Estudando*…), prioridade, **anotações** e **ocultar** o que não interessa. Tudo fica salvo.
- Aviso de **prova no mesmo dia** entre os concursos que você acompanha.
- **Previstos e manuais:** concursos que ainda não abriram (CETESB, Câmara de Guarulhos, Prefeitura de Campinas, COREN-SP…) e qualquer um que você quiser cadastrar à mão em **+ Adicionar concurso**.
- **Exportar planilha:** gera um CSV (abre no Excel) com o que está filtrado na tela.

## De onde vêm os dados

- **PCI Concursos** (pciconcursos.com.br): listas de SP e nacionais + página de cada notícia.
- O link do **edital** no PCI fica atrás de uma verificação anti-robô (captcha). O sistema **não** tenta burlar isso: ele mostra o link da notícia (o edital está lá) e o site da banca.
- O salário mostrado na lista é o **maior do edital** ("até R$"). O salário de cada cargo está no edital.
- A distância é aproximada (linha reta × 1,25) até a cidade do órgão. Para nacionais, o sistema lista as cidades de SP citadas no texto da notícia — confira no edital onde haverá prova.
- Sempre confirme no edital oficial antes de se inscrever.

## Arquivos

- `app.py` – servidor web (porta 8765). Opções: `--porta 9000`, `--sem-navegador`, `--sem-atualizar`.
- `fonte_pci.py` – lê o PCI Concursos. Se o site mudar o layout, o aviso aparece em amarelo no topo da tela.
- `extrator.py` – tira datas, valores e cargos do texto.
- `municipios_sp.py` – coordenadas dos 645 municípios de SP.
- `dados/concursos.db` – seu banco de dados (apague para começar do zero).
- `tests/` – testes: `python -m unittest discover tests`.

## Como funciona no GitHub

- `.github/workflows/coletar.yml` – roda `coletar.py` 2x por dia, salva `dados/cache.json` e publica a pasta `docs/` no GitHub Pages.
- `coletar.py` – faz a busca e gera `docs/dados/concursos.json`, `meta.json` e `municipios.json`.
- `docs/index.html` – é gerado a partir de `static/index.html` (não edite o de `docs/`, ele é sobrescrito).
- Se o PCI bloquear os servidores do GitHub, o aviso aparece em amarelo no site; dá para rodar `python coletar.py` no seu PC e enviar o resultado.
