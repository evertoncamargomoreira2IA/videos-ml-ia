from .models import AnomalyFlag, Cycle, CycleMetrics, Event, TaktInput
from .metrics import classify_cycle_time
from .yamazumi import yamazumi, yamazumi_average

def render_report(cycles: list[Cycle], events: list[Event], stats: CycleMetrics, takt: TaktInput, anomalies: list[AnomalyFlag]) -> str:
    y=yamazumi(cycles,events)
    lines=["# Relatório de análise de manufatura","","## Resumo",f"- Ciclos completos: {stats.n}; ciclos incompletos: {sum(not c.complete for c in cycles)}.",f"- Takt calculado: {takt.takt_time_seconds:.2f} s ({takt.available_time_seconds:g} s / {takt.customer_demand_units:g} unidades).",f"- Cycle Time médio: {stats.mean:.2f} s." if stats.mean is not None else "- Cycle Time médio: sem ciclos completos.","","## Ciclos","| Ciclo | Início (s) | Fim (s) | CT (s) | Estado | Comparação takt |","|---|---:|---:|---:|---|---|"]
    for c in cycles:
        comp=classify_cycle_time(c.duration,takt.takt_time_seconds) if c.complete and c.duration is not None else None
        lines.append(f"| {c.cycle_id} | {c.start_time:.2f} | {c.end_time if c.end_time is not None else '—'} | {c.duration if c.duration is not None else '—'} | {'completo' if c.complete else 'incompleto'} | {comp['classification'] if comp else '—'} |")
    lines.extend(["","## Estatísticas de Cycle Time","| n | Média | Mediana | Mínimo | Máximo | Desvio padrão | P90 | P95 | CV |","|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
    vals=[stats.n,stats.mean,stats.median,stats.min,stats.max,stats.std,stats.p90,stats.p95,stats.cv]
    lines.append("| "+" | ".join("—" if v is None else (str(v) if i==0 else f"{v:.3f}") for i,v in enumerate(vals))+" |")
    lines.extend(["","## Yamazumi por ciclo","| Ciclo | Bucket (s) | Soma eventos | Gap | Sobreposição |","|---|---|---:|---:|---:|"])
    for cid,row in y.items(): lines.append(f"| {cid} | {', '.join(f'{k}: {v:.2f}' for k,v in row['buckets'].items()) or '—'} | {row['event_duration_sum']:.2f} | {row['gap_seconds']:.2f} | {row['overlap_seconds']:.2f} |")
    lines.extend(["","### Média por bucket","| Bucket | Segundos/ciclo |","|---|---:|"])
    for k,v in yamazumi_average(y).items(): lines.append(f"| {k} | {v:.2f} |")
    lines.extend(["","## Anomalias","| Tipo | Evidência | Ciclos | Eventos | Descrição |","|---|---|---|---|---|"])
    if anomalies:
        for a in anomalies: lines.append(f"| {a.anomaly_type} | {a.evidence_class} | {', '.join(a.cycle_ids)} | {', '.join(a.event_ids)} | {a.description} |")
    else: lines.append("| — | — | — | — | Nenhuma regra sinalizou anomalias. |")
    lines.extend(["","## Limitações","Análise determinística baseada apenas nos eventos fornecidos. Lacunas e sobreposições são exibidas; eventos fora de ciclos não entram no Yamazumi.",""])
    return "\n".join(lines)
