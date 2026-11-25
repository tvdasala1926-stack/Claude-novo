from __future__ import annotations

from statistics import median

from maquina.models import VideoAnalysis


def _fmt(value, spec: str = "") -> str:
    return "n/d" if value is None else format(value, spec)


def build_report(ranked: list[dict], analyses: list[VideoAnalysis], errors: list[dict]) -> str:
    out = ["# Relatório de análise", ""]

    out += ["## Produtos (ranking)", ""]
    if ranked:
        out += ["| # | Produto | Score | Preço | Comissão | Vendas | Avaliação |", "|---|---|---|---|---|---|---|"]
        for i, r in enumerate(ranked, start=1):
            p = r["product"]
            out.append(
                f"| {i} | {p.name} | {r['score']:.2f} | {_fmt(p.price, '.2f')} | "
                f"{_fmt(p.commission_rate, 'g')} | {_fmt(p.sales)} | {_fmt(p.rating, 'g')} |"
            )
        out += ["", "n/d = dado não informado; não foi estimado.", ""]
    else:
        out += ["Nenhum produto informado.", ""]

    out += ["## Vídeos analisados", ""]
    if not analyses:
        out += ["Nenhum vídeo analisado com sucesso.", ""]
    for n, a in enumerate(analyses, start=1):
        out += [
            f"### Vídeo {n}: {a.ref.url or a.ref.path}",
            f"- Duração: {a.probe.duration:.1f}s | {a.probe.width}x{a.probe.height} | {a.probe.fps:.0f} fps",
            f"- Desempenho: {_fmt(a.ref.views)} visualizações | {_fmt(a.ref.likes)} curtidas | "
            f"{_fmt(a.ref.comments)} comentários",
            f"- Cortes: {len(a.cuts)} ({a.cuts_per_minute:.1f}/min)",
            f"- Primeiros 3 segundos (transcrição): {a.first3s_text or '(sem fala detectada)'}",
            "", "| Parte | Início | Fim | Duração |", "|---|---|---|---|",
        ]
        out += [f"| {s.name} | {s.start:.1f}s | {s.end:.1f}s | {s.end - s.start:.1f}s |"
                for s in a.segments]
        out.append("")

    if analyses:
        durations = [a.probe.duration for a in analyses]
        rhythm = [a.cuts_per_minute for a in analyses]
        hook_len = [a.segments[0].end - a.segments[0].start for a in analyses]
        out += [
            "## Padrões comuns", "",
            f"- Duração mediana: {median(durations):.1f}s",
            f"- Ritmo mediano: {median(rhythm):.1f} cortes/min",
            f"- Gancho mediano: {median(hook_len):.1f}s", "",
            "## Ideias de vídeo", "",
            f"Estrutura recomendada (derivada dos padrões; conteúdo deve ser original):", "",
            f"1. Gancho nos primeiros {median(hook_len):.0f}s, com o benefício ou problema do produto.",
            f"2. Duração alvo: cerca de {median(durations):.0f}s.",
            f"3. Cerca de {median(rhythm):.0f} cortes por minuto para manter o ritmo.",
            "4. Problema → demonstração do produto → virada → prova → chamada para ação no final.",
            "",
        ]

    if errors:
        out += ["## Falhas", ""] + [f"- {e['video']}: {e['error']}" for e in errors] + [""]
    return "\n".join(out)
