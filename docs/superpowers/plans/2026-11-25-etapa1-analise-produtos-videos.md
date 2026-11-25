# Etapa 1 — Análise de Produtos e Vídeos: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Receber produtos e links de vídeos do TikTok, analisar cada vídeo de forma real (probe, cortes, transcrição por palavra, estrutura) e gerar ranking de produtos e relatório de ideias de vídeo.

**Architecture:** Pacote Python `maquina/` com módulos pequenos e independentes, ligados por dataclasses em `models.py` e um `pipeline.py` que grava tudo em `runs/<id>/` (JSON + `report.md`). FFmpeg faz probe e detecção de cortes; faster-whisper faz a transcrição; yt-dlp baixa vídeos. Uma falha em um vídeo não derruba os outros.

**Tech Stack:** Python 3.13, pytest, FFmpeg/ffprobe 6.1, yt-dlp, faster-whisper (CPU, modelo `base`).

**Spec:** `docs/superpowers/specs/2026-11-25-maquina-edicao-ia-design.md`

## Global Constraints

- Gratuito: nenhuma API paga nem assinatura.
- Métrica ausente vira `None`; nunca preencher, estimar ou inventar.
- Não copiar vídeos: o relatório extrai estrutura e princípios, não texto literal para reuso.
- Nada simulado: testes usam FFmpeg e modelos reais. Teste que não puder rodar de verdade é marcado `skip` com motivo e reportado como não verificado.
- Mercado/idioma: Brasil, português (`language="pt"` na transcrição).
- Cada módulo é testável sozinho; sem estado global.

## Review Focus

- Números em formato brasileiro: `R$ 1.299,90`, `12,5 mil`, `1,2 mi`, `3k` viram valores corretos; texto ilegível vira `None`.
- Vídeo sem áudio: transcrição retorna lista vazia e a estrutura ainda é gerada.
- Vídeo sem cortes (plano único): `detect_scenes` retorna `[]` e o ritmo é reportado como 0 cortes.
- Link removido, privado ou encurtado: erro claro por vídeo; os demais vídeos seguem.
- CSV com linhas vazias, duplicadas ou colunas faltando: linhas vazias ignoradas, duplicatas unidas, coluna faltando vira `None`.

---

### Task 1: Esqueleto do projeto e modelos

**Files:**
- Create: `pyproject.toml`, `maquina/__init__.py`, `maquina/models.py`, `tests/conftest.py`, `tests/test_models.py`, `.gitignore`

**Interfaces:**
- Produces (`maquina/models.py`, dataclasses com `to_dict()`):
  - `Product(name: str, price: float | None, commission_rate: float | None, sales: int | None, rating: float | None)`
  - `VideoRef(url: str | None, path: str | None, product: str | None)`
  - `Word(text: str, start: float, end: float)`
  - `VideoProbe(duration: float, width: int, height: int, fps: float, has_audio: bool)`
  - `Segment(name: str, start: float, end: float)`
  - `VideoAnalysis(ref: VideoRef, probe: VideoProbe, cuts: list[float], words: list[Word], segments: list[Segment], hook_text: str, first3s_text: str, cuts_per_minute: float)`
- Produces (`tests/conftest.py`): fixture `sample_video(tmp_path) -> Path`: 6 s, 3 trechos de cor sólida (cortes em 2 s e 4 s), tom senoidal; fixture `silent_video(tmp_path) -> Path`: 4 s de cor única, sem áudio. Ambos gerados com `ffmpeg -f lavfi`.

- [ ] **Step 1: Write failing test** em `tests/test_models.py`: `Product("x", None, None, None, None).to_dict()["price"] is None` e `VideoAnalysis(...).to_dict()` é serializável por `json.dumps`.
- [ ] **Step 2: Run** `pytest tests/test_models.py -v`. Expected: FAIL (módulo não existe).
- [ ] **Step 3: Implement** `pyproject.toml` (pacote `maquina`, dependências `yt-dlp`, `faster-whisper`, `pytest`), `models.py` com dataclasses acima, `conftest.py` com as duas fixtures, `.gitignore` com `runs/`, `__pycache__/`, `.venv/`. Instalar: `pip install -e . pytest`.
- [ ] **Step 4: Run** `pytest tests/test_models.py -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: project skeleton and models`.

### Task 2: Importador de produtos e vídeos

**Files:**
- Create: `maquina/importer.py`, `tests/test_importer.py`

**Interfaces:**
- Consumes: `Product`, `VideoRef`.
- Produces:
  - `parse_number(text: str | None) -> float | None`
  - `load_products(path: Path) -> list[Product]` (CSV ou TSV; separador detectado; cabeçalhos aceitos: nome/name/produto, preço/preco/price, comissão/comissao/commission, vendas/sales, avaliação/avaliacao/rating)
  - `load_video_refs(path: Path) -> list[VideoRef]` (um item por linha: URL `http(s)` ou caminho local; linhas vazias e `#` ignoradas; duplicatas removidas)

- [ ] **Step 1: Write failing tests**: `parse_number("R$ 1.299,90") == 1299.90`; `parse_number("12,5 mil") == 12500`; `parse_number("1,2 mi") == 1_200_000`; `parse_number("3k") == 3000`; `parse_number("12%") == 12` ; `parse_number("abc") is None`; `parse_number("") is None`. CSV com cabeçalho em português, uma linha vazia e uma duplicada: duas linhas distintas, duplicata unida (maior `sales`); coluna `avaliacao` ausente → `rating is None`. Lista de links com `#comentário`, vazia e repetida → itens únicos; item sem `http` vira `path`.
- [ ] **Step 2: Run** `pytest tests/test_importer.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** as três funções. `parse_number`: remover `R$`, espaços e `%`; sufixos `mil`/`k`=1e3, `mi`/`m`=1e6; vírgula decimal, ponto de milhar. Comissão `12%` e `0,12` ficam como o usuário digitou; `rank` normaliza.
- [ ] **Step 4: Run** testes. Expected: PASS.
- [ ] **Step 5: Commit** `feat: importer for products and video links`.

### Task 3: Download de vídeo

**Files:**
- Create: `maquina/fetch.py`, `tests/test_fetch.py`

**Interfaces:**
- Consumes: `VideoRef`.
- Produces:
  - `class FetchError(Exception)`
  - `fetch_video(ref: VideoRef, out_dir: Path) -> Path` — se `ref.path`, valida existência e devolve o caminho; se `ref.url`, usa yt-dlp (Python API), salva `out_dir/<id>.mp4`, até 3 tentativas com espera crescente; erro final levanta `FetchError` com a causa legível.

- [ ] **Step 1: Write failing tests**: caminho local existente devolve o mesmo caminho; caminho inexistente → `FetchError`; URL inválida (`https://www.tiktok.com/@x/video/1`) → `FetchError` com mensagem não vazia (usa a rede real; sem mock).
- [ ] **Step 2: Run** `pytest tests/test_fetch.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `fetch_video`. Formato `mp4` melhor qualidade, sem playlist, sem logs no stdout.
- [ ] **Step 4: Run** testes. Expected: PASS. Depois, teste manual com um link real de TikTok fornecido pelo usuário; registrar resultado (funciona/falha e por quê). Se o TikTok bloquear o download, reportar e propor alternativa (cookies do usuário ou arquivo local).
- [ ] **Step 5: Commit** `feat: video fetching with retries`.

### Task 4: Probe e detecção de cortes

**Files:**
- Create: `maquina/probe.py`, `maquina/scenes.py`, `tests/test_probe_scenes.py`

**Interfaces:**
- Consumes: `VideoProbe`, fixtures `sample_video`, `silent_video`.
- Produces:
  - `probe_video(path: Path) -> VideoProbe` (via `ffprobe -print_format json`)
  - `detect_scenes(path: Path, threshold: float = 0.3) -> list[float]` — instantes (s) dos cortes, via filtro `select='gt(scene,T)'` + `showinfo`.

- [ ] **Step 1: Write failing tests**: `sample_video`: `duration ≈ 6.0 (±0.2)`, `has_audio is True`, `detect_scenes` devolve 2 cortes perto de 2.0 e 4.0 (±0.2). `silent_video`: `has_audio is False`, `detect_scenes == []`.
- [ ] **Step 2: Run** `pytest tests/test_probe_scenes.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** as duas funções. Arquivo inexistente ou corrompido levanta `ValueError` com mensagem clara.
- [ ] **Step 4: Run** testes. Expected: PASS.
- [ ] **Step 5: Commit** `feat: ffprobe and scene detection`.

### Task 5: Transcrição por palavra

**Files:**
- Create: `maquina/transcribe.py`, `tests/test_transcribe.py`

**Interfaces:**
- Consumes: `Word`, `probe_video`.
- Produces: `transcribe(path: Path, model_size: str = "base", language: str = "pt") -> list[Word]` — extrai áudio com FFmpeg (mono 16 kHz), roda faster-whisper com `word_timestamps=True`; vídeo sem áudio devolve `[]` sem carregar o modelo.

- [ ] **Step 1: Write failing tests**: `silent_video` → `[]`. Teste com fala real: gerar um WAV em português com `espeak-ng -v pt-br "compre agora pelo link"`, converter para vídeo e verificar que `words` tem `start < end`, tempos crescentes e contém "link" (comparação sem acentos/caixa). Se `espeak-ng` não estiver disponível, o teste faz `pytest.skip("espeak-ng ausente")`.
- [ ] **Step 2: Run** `pytest tests/test_transcribe.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `transcribe`. Baixar o modelo na primeira execução (depende de `huggingface.co`). Carregar o modelo uma vez por processo (cache em módulo).
- [ ] **Step 4: Run** testes. Expected: PASS ou SKIP com motivo. Reportar honestamente se o teste de fala foi pulado.
- [ ] **Step 5: Commit** `feat: word-level transcription`.

### Task 6: Estrutura do vídeo e ritmo

**Files:**
- Create: `maquina/structure.py`, `tests/test_structure.py`

**Interfaces:**
- Consumes: `Word`, `Segment`.
- Produces:
  - `split_structure(duration: float, words: list[Word], cuts: list[float]) -> list[Segment]` — sempre retorna, em ordem e sem lacunas, os segmentos: `gancho`, `introducao`, `desenvolvimento`, `problema`, `virada`, `climax`, `conclusao`, `cta`.
  - `first_seconds_text(words: list[Word], seconds: float = 3.0) -> str`
  - `cuts_per_minute(duration: float, cuts: list[float]) -> float`

Regras (decisão do plano): `gancho` = 0 até 3 s (ou até a duração, se menor). `cta` começa na primeira palavra-chave de chamada (`link`, `carrinho`, `compre`, `clique`, `garanta`, `comenta`, `segue`, `aproveita`) encontrada na metade final; sem palavra-chave, os últimos 15% da duração. O trecho entre `gancho` e `cta` é dividido nos seis segmentos restantes na proporção 8/17/25/15/25/10 (%), puxando cada fronteira para o corte mais próximo dentro de ±10% do trecho, se houver.

- [ ] **Step 1: Write failing tests**: duração 30 s, sem palavras nem cortes → 8 segmentos contíguos, primeiro começa em 0, último termina em 30, `gancho.end == 3`. Palavra "link" em 27 s → `cta.start == 27`. Duração 2 s → todos os segmentos têm `start <= end` e cobrem 0–2. `first_seconds_text` junta só palavras com `start < 3`. `cuts_per_minute(30, [5,10,15]) == 6.0`; `cuts_per_minute(0, []) == 0.0`.
- [ ] **Step 2: Run** `pytest tests/test_structure.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** as três funções conforme as regras.
- [ ] **Step 4: Run** testes. Expected: PASS.
- [ ] **Step 5: Commit** `feat: structure splitting and pacing`.

### Task 7: Ranking de produtos

**Files:**
- Create: `maquina/rank.py`, `tests/test_rank.py`

**Interfaces:**
- Consumes: `Product`.
- Produces: `rank_products(products: list[Product], weights: dict[str, float] | None = None) -> list[dict]` — cada item: `{"product": Product, "score": float, "used_fields": list[str], "missing_fields": list[str]}`, ordem decrescente de `score`. Pesos padrão: `sales` 0.6, `commission_rate` 0.3, `rating` 0.1.

Regras: cada campo é normalizado por min–max entre os produtos que o têm (se todos iguais, vale 1.0); campo ausente não entra no cálculo e os pesos restantes são renormalizados; produto sem nenhum campo pontuável fica com `score` 0.0 e vai ao fim.

- [ ] **Step 1: Write failing tests**: três produtos com vendas 100/500/1000 → ordem por vendas quando só `sales` existe. Produto com `sales=None` não é penalizado como se fosse 0: seu `used_fields` não contém `sales` e `missing_fields` contém. Lista vazia → `[]`. Todos sem campos → score 0.0 para todos.
- [ ] **Step 2: Run** `pytest tests/test_rank.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `rank_products`.
- [ ] **Step 4: Run** testes. Expected: PASS.
- [ ] **Step 5: Commit** `feat: product ranking without invented metrics`.

### Task 8: Pipeline, relatório e CLI

**Files:**
- Create: `maquina/pipeline.py`, `maquina/report.py`, `maquina/cli.py`, `tests/test_pipeline.py`, `README.md`

**Interfaces:**
- Consumes: todos os módulos anteriores.
- Produces:
  - `analyze_video(ref: VideoRef, work_dir: Path) -> VideoAnalysis`
  - `run_pipeline(products_file: Path | None, videos_file: Path, out_root: Path, run_id: str | None = None) -> Path` — cria `runs/<id>/`; grava `products_ranked.json`, `videos/<n>/analysis.json`, `errors.json` (vídeos que falharam, com causa), `state.json` (etapa e progresso) e `report.md`; uma falha por vídeo não interrompe o restante.
  - `build_report(ranked: list[dict], analyses: list[VideoAnalysis], errors: list[dict]) -> str` (Markdown em português: ranking de produtos; por vídeo: duração, cortes/min, gancho, texto dos 3 primeiros segundos, tabela de estrutura com durações; seção "Padrões comuns" com mediana de duração e de cortes/min; seção "Ideias de vídeo" com a estrutura recomendada derivada dos padrões, sem reutilizar frases do original; seção de falhas).
  - CLI: `python -m maquina.cli --videos links.txt [--products produtos.csv] [--out runs]`, imprime o caminho do relatório.

- [ ] **Step 1: Write failing tests**: `run_pipeline` com arquivo de vídeos contendo `sample_video` e um caminho inexistente: gera `report.md`, `analysis.json` do vídeo válido com `segments` de 8 itens, `errors.json` com 1 erro, `state.json` com progresso completo. Teste do CLI via `subprocess` retorna código 0 e imprime caminho existente. Relatório com zero vídeos válidos não quebra e informa isso.
- [ ] **Step 2: Run** `pytest tests/test_pipeline.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `analyze_video`, `run_pipeline`, `build_report`, CLI. `README.md`: como instalar, formato dos arquivos de entrada e exemplo de uso.
- [ ] **Step 4: Run** `pytest -v`. Expected: tudo PASS (testes pulados listados com motivo).
- [ ] **Step 5: Teste real:** rodar o CLI com os produtos e links reais do usuário; ler o `report.md` gerado e conferir manualmente que durações e cortes batem com o vídeo. Registrar o que funcionou e o que falhou.
- [ ] **Step 6: Commit** `feat: pipeline, report and CLI`.

---

## Self-review

- **Cobertura da spec (Etapa 1):** módulos 1 (Task 2), 2 (Task 3), 3 (Tasks 4–5), 4 (Task 6), 5 (Task 7), 6 (Task 8) e orquestrador mínimo (Task 8). Painel web, roteiro, voz, cenas e montagem ficam fora, conforme a spec.
- **Qualitativo (gancho, problema, solução, potencial):** a Etapa 1 entrega só medições reais e estrutura heurística. O julgamento qualitativo (por que o gancho funciona, pontuação de potencial) será feito pelo Claude lendo `analysis.json`, em etapa seguinte com interface `Analyst`. Está fora deste plano de propósito.
- **Consistência de tipos:** nomes e assinaturas conferem entre Tasks 1–8.
