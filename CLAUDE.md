# Radar de Concursos — contexto para o Claude Code

Este projeto nasceu numa conversa no claude.ai (05/11/2026). Este arquivo resume tudo o que foi decidido para continuar daqui.

## Objetivo do dono
- Mora em **Nova Odessa (SP)**, trabalha com **TI/redes** (formação em Segurança da Informação).
- Quer acompanhar **concursos públicos** sem montar planilha à mão:
  1. **TI** (analista/técnico de TI, sistemas, redes, suporte, segurança da informação) no estado de SP ou nacionais.
  2. **Qualquer área de nível médio com salário acima de R$ 4 mil**.
- Prefere concursos com **prova e trabalho perto de casa** (região de Campinas/Americana/Piracicaba), mas quer ver o estado todo com a distância.
- Responder sempre em **português**, linguagem simples. Ele usa bastante pelo **celular**.

## Como o sistema funciona
- **Fonte:** PCI Concursos (`pciconcursos.com.br`)
  - Listas: `/concursos/sudeste/` (filtra UF=SP) e `/concursos/nacional/`. Cada concurso é um `div.da` ou `div.na` com
    `.ca a` (órgão, href da notícia, title), `.cc` (UF), `.cd` (vagas + "até R$" / cargos / níveis separados por `<br>`),
    `.ce` (datas de inscrição: `dd/mm/aaaa`, `dd a dd/mm/aaaa`, `dd/mm a dd/mm/aaaa`, `Prorrogado até`, `Reaberto até`).
  - Notícia: `article#noticia` → `[itemprop=articleBody]` com `<p>` e `<ul><li>` de cargos (o `<p>` antes de cada `<ul>` costuma ser o nível, ex. "Ensino médio/técnico").
  - **Os links de edital ficam atrás de captcha (Cloudflare Turnstile). NÃO burlar.** Mostramos o link da notícia e o site da banca.
  - Testado em 05/11/2026: os servidores do GitHub Actions acessam o PCI sem bloqueio (194 concursos em ~4 min).
- **Coleta** (`atualizador.py` + `fonte_pci.py` + `extrator.py`): baixa listas, grava no SQLite, abre a notícia de cada concurso novo/alterado (pausa 0,8 s) e extrai prova, inscrições, taxa, salário, benefícios, cargos por nível, site da banca, cidades de SP citadas.
- **Distância:** `municipios_sp.py` tem coordenadas dos 645 municípios de SP; distância = linha reta × 1,25.
- **Previstos** (sem inscrição aberta, não aparecem no PCI): cadastrados em `seed.py` (CETESB, Câmara de Guarulhos, Prefeitura de Campinas, COREN-SP, FUNCAMP, CNU 2027, Banco do Brasil, Caixa).

## Duas formas de rodar
1. **Online (principal):** GitHub Actions + GitHub Pages
   - `.github/workflows/coletar.yml` roda `coletar.py` às 7h e 19h (BRT), em `workflow_dispatch` e em push de código.
     Em push roda só `--so-publicar` (não busca). Salva `dados/cache.json` (cache dos detalhes) e publica `docs/`.
   - Site: https://guiduraesz-netizen.github.io/radar-concurso/ — `docs/index.html` é **gerado** a partir de
     `static/index.html` com `window.MODO_ESTATICO = true` (não editar o de `docs/`).
   - No modo estático, estrelas/status/notas/cadastros ficam no **localStorage** (botão "Meus dados" faz backup/restauração).
2. **Local:** `iniciar.bat` (Windows) ou `python app.py` → http://127.0.0.1:8765, banco em `dados/concursos.db`.

## Regras do projeto
- **Só biblioteca padrão do Python** (3.8+). Sem pip install — precisa rodar no Windows do dono sem configurar nada.
- Front-end num arquivo só (`static/index.html`, JS puro, sem CDN). A mesma interface atende o modo local (rotas `/api/*` em `app.py`) e o estático (`apiEstatica()` no JS).
- Interface em português; datas dd/mm/aaaa; valores em R$.
- Antes de commitar: `python -m unittest discover tests` (há testes com páginas reais do PCI em `tests/fixtures/`).
- Commits de dados feitos pelo bot levam `[skip ci]`.

## Limitações conhecidas
- O salário da lista é o **maior do edital** ("até R$"); o salário por cargo só no edital.
- Detecção de TI é por palavra-chave (`extrator.PALAVRAS_TI`); "suporte técnico" às vezes não é TI.
- Para nacionais, a cidade de prova vem só das cidades citadas no texto da notícia.
- Taxa/prova às vezes não são achadas quando a notícia usa outro formato de frase.

## Ideias para continuar (não feitas ainda)
- Segunda fonte para cruzar dados (ex.: radardeconcurso.com.br — tem filtro por cargo de TI e às vezes o PDF do edital).
- Avisos (e-mail/Telegram/notificação) quando aparecer concurso novo que bate com os filtros.
- Extrair salário por cargo quando a notícia trouxer tabela.
- Sincronizar os dados pessoais entre PC e celular sem backup manual.
- Melhorar a detecção da cidade da prova nos concursos nacionais.
