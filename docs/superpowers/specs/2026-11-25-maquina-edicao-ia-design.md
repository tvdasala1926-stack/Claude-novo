# Máquina de Edição IA — Design (Etapa 1)

Data: 2026-11-25. Status: aguardando aprovação.

## Intenção

O usuário é afiliado do TikTok Shop (conta ativa). Quer descobrir quais produtos
vendem mais e quais vídeos vendem, e produzir vídeos novos com a mesma estrutura
narrativa. Só TikTok. Meta final: escolher nicho, apertar um botão e receber o
vídeo pronto. Isso é um projeto de várias etapas; este documento cobre a
arquitetura geral e a Etapa 1.

## Metas

- Software real: nada simulado, nada declarado pronto sem teste real.
- Gratuito por padrão; sem assinatura obrigatória.
- Modular: cada módulo com entrada/saída em arquivos JSON, testável sozinho.
- Mínima intervenção humana; pedir aprovação só quando necessário.
- Não inventar métricas: campo ausente fica `null`.

## Não-metas / anti-metas

- Não raspar TikTok nem automatizar o painel do afiliado (viola termos, arrisca a conta).
- Não copiar vídeos literalmente: extrair estrutura e princípios, produzir conteúdo original.
- Não usar áudio sem licença.
- Não prometer geração de cenas 3D gratuita local: sem GPU, depende de serviço externo (Etapa futura, a verificar).

## Restrições verificadas neste ambiente

- Python 3.13, Node 22, FFmpeg/ffprobe 6.1 presentes. 4 CPUs, 15 GB, sem GPU.
- yt-dlp e Whisper não instalados. PyPI acessível.
- **Rede bloqueada pelo proxy (403):** `www.tiktok.com` e `huggingface.co`.
  Sem TikTok, não baixa vídeos por link. Sem Hugging Face, não baixa modelos Whisper.
  Precisa liberar hosts no ambiente (ver Aberto) ou o usuário fornece os arquivos de vídeo.
- Claude como analista: via esta sessão (sem custo de API) ou via API paga (opcional, módulo plugável).

## Abordagens consideradas

- **A. Importação (escolhida pelo usuário).** Usuário fornece dados de produtos
  (CSV/colagem do Centro de Afiliados) e links/arquivos de vídeos. Confiável, grátis, seguro.
- B. Automação do painel logado. Rejeitada: zona cinzenta, frágil, risco à conta.
- C. Ferramenta paga com API. Rejeitada por ora; fica como coletor plugável futuro.

## Arquitetura

Python. Pacote `maquina/` com módulos independentes; painel web local (FastAPI + HTML).
Orquestrador executa etapas, registra progresso em `runs/<id>/state.json`, tenta de novo
em falha e permite retomar.

Módulos (um por pasta, interface `run(input_dir, output_dir)`):

1. `import_data` — lê CSV de produtos e lista de vídeos. Valida, normaliza, nunca preenche métrica ausente.
2. `fetch` — baixa vídeo por link (yt-dlp) ou aceita arquivo local.
3. `analyze_video` — ffprobe (duração), detecção de cortes (FFmpeg), transcrição com tempo por palavra (faster-whisper), primeiros 3 s, ritmo.
4. `structure` — divide em gancho, desenvolvimento, problema, virada, clímax, conclusão, CTA, com durações.
5. `rank` — ranqueia produtos por vendas/comissão/engajamento informados; pontua vídeos com justificativa.
6. `report` — relatório de produtos e de ideias de vídeo (Markdown + JSON).
7. (Etapas futuras) `script`, `scenes`, `voice`, `assemble`, `qa`, `deliver`.

Análise qualitativa (gancho, problema, solução, potencial) é feita pelo Claude sobre
os dados mecânicos dos módulos 3–4, por uma interface `Analyst` com dois backends:
sessão do Claude Code (padrão, grátis) e API Anthropic (opcional, pago).

## Etapa 1 (escopo)

Módulos 1, 3, 4, 5, 6 e orquestrador mínimo por linha de comando, com testes reais
em vídeos de teste gerados por FFmpeg (e um vídeo real se o usuário fornecer).
Módulo 2 funciona para arquivos locais; download por link depende da liberação do TikTok.
Painel web, roteiro, voz, cenas 3D e montagem ficam para etapas seguintes.

Saída: `runs/<id>/` com `products_ranked.json`, `videos/<n>/analysis.json`,
`structure.json`, `report.md`.

## Decisões minhas (a conferir)

- Python + FFmpeg + faster-whisper (CPU, modelo pequeno/`base` por padrão).
- Painel web só depois da Etapa 1.
- Ranking de produtos usa apenas campos fornecidos; pesos configuráveis.

## Aberto

- Liberar `tiktok.com` (e CDNs de vídeo) e `huggingface.co` no ambiente, ou fornecer arquivos/modelos manualmente.
- Formato exato do que o usuário consegue exportar do Centro de Afiliados (definir ao ver um exemplo).
- País/idioma do mercado (assumo Brasil, português).
