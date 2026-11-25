# Máquina de Edição IA — Etapa 1

Analisa produtos e vídeos do TikTok Shop e gera ranking + relatório de estrutura.

## Instalar
    pip install -e ".[dev]"      # precisa de ffmpeg no sistema

## Entradas
- `produtos.csv` (ou `.tsv`): colunas `nome;preco;comissao;vendas;avaliacao` (só `nome` é obrigatório).
  Aceita `R$ 1.299,90`, `12,5 mil`, `1,2 mi`, `12%`. Dado ausente fica `n/d`.
- `videos.txt`: um link do TikTok ou caminho de arquivo por linha. `#` comenta.

- `perfis.txt`: um perfil público por linha (`@usuario`). O sistema lista os vídeos, lê visualizações e curtidas, e analisa os mais vistos.

## Usar
    python -m maquina.cli --videos videos.txt --products produtos.csv --out runs
    python -m maquina.cli --profiles perfis.txt --per-profile 10 --top 30 --products produtos.csv

Saída em `runs/<data-hora>/`: `report.md`, `products_ranked.json`,
`videos/<n>/analysis.json`, `errors.json`, `state.json`.

## Testes
    pytest
