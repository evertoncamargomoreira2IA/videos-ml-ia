# Backlog de desenvolvimento — MVA (análise de vídeo de manufatura)

Cada sprint termina com algo que o Everton consegue **rodar e validar na interface local** (`iniciar.bat`).
Status: ✅ pronto · 🔄 em andamento · ⏳ próximo · ⬜ planejado

## Como validar cada entrega (passo a passo)

1. Dê duplo clique em `iniciar.bat`. O navegador abre em http://127.0.0.1:8765/.
2. Crie uma **Nova análise**: nome, posto, **Takt Time**, **Cycle Time padrão** (opcional) e o vídeo.
3. Clique em **Abrir rotulagem** e marque os eventos pelo teclado (`S` início do ciclo, `E` fim, `1` pick, `3` assemble, `4` fasten, `8` inspect, `Q` search, `A` wait, `D` rework). Salva sozinho.
4. Volte para a análise e clique em **Salvar e rodar análise**.
5. Valide:
   - **Anomalias:** confirmar ou rejeitar, com comentário.
   - **Ciclos:** digite a sua cronometragem; a tela mostra a diferença.
   - **Observações gerais.**
6. Tudo fica em `C:\Users\<você>\mva_dados\analyses\<id>\`: `analysis.json`, `events.csv`, `metrics.json`, `relatorio.md` e `feedback.json`.

## Sprint 1 — Núcleo de métricas ✅
- [x] Schema de eventos (`mva/schemas/manufacturing_event_schema.json`)
- [x] Segmentação de ciclos (incompletos reportados, nunca descartados)
- [x] Cycle Time: média, mediana, mín/máx, desvio, P90, P95, CV
- [x] Takt e classificação abaixo / próximo / acima / muito acima
- [x] Yamazumi por ciclo e médio, com gap e sobreposição
- [x] Anomalias: acima do takt, busca, espera, retrabalho, ciclo incompleto, outlier MAD
- [x] Relatório Markdown determinístico + CLI `mva analyze`

## Sprint 2 — Vídeo e rotulagem manual ✅
- [x] `mva probe` / `mva ingest`: metadados, quadros, folha de miniaturas, manifest
- [x] Tempos corretos em vídeo de celular (fps variável)
- [x] Tela de rotulagem com atalhos, desfazer, validação e exportação CSV

## Sprint 3 — Interface local de validação 🔄 (entregue, aguardando validação com vídeo real)
- [x] `iniciar.bat`: cria o ambiente Python e abre o navegador (instala o Python via uv se faltar)
- [x] Lista de análises, criação com upload de vídeo ou CSV
- [x] Rotulagem integrada à análise (salva no servidor local; "Ver no vídeo" pula para o ciclo)
- [x] Parâmetros editáveis: Takt Time e CT padrão informados direto, limites de busca/espera, faixas de takt
- [x] Comparação de cada ciclo e do CT médio com o takt e com o CT padrão (anomalia "acima do CT padrão")
- [x] Resultado: KPIs, gráfico de CT vs takt, Yamazumi
- [x] Validação: confirmar/rejeitar anomalias, CT manual vs sistema, observações (histórico append-only)
- [ ] **Everton:** rodar com 1 vídeo real do posto piloto e anotar o que falta

## Sprint 4 — Robustez do piloto ⏳
- [ ] Editar os limites de ciclo direto na timeline (arrastar início/fim)
- [ ] Sequência padrão (eSOP) por posto e desvio de sequência como anomalia
- [ ] Comparação entre análises (antes/depois, turnos, operadores)
- [ ] Exportar relatório em PDF/Excel
- [ ] Taxonomia Yamazumi configurável por planta/processo

## Sprint 5 — Detecção assistida por IA ⬜
- [ ] Detecção e rastreamento de pessoa/mãos/peças com modelo pré-treinado (`VisionProvider` substituível)
- [ ] Eventos candidatos com confiança, pré-preenchidos na rotulagem
- [ ] Métricas de precisão/recall contra os rótulos manuais

## Sprint 6 — Aprendizado com as correções ⬜
- [ ] Correções viram dataset versionado (`dataset_v0.1`…)
- [ ] Classificador de eventos treinado com os dados do piloto
- [ ] Avaliação por versão de modelo (nunca sobrescrever rótulos)

## Sprint 7 — Relatório com IA e análise de falhas ⬜
- [ ] Episódios de falha (teste → falha → intervenção → reteste)
- [ ] GPT analisa os dados estruturados, Claude revisa (fato / inferência / hipótese / recomendação)
- [ ] Checklist de qualidade da `SKILL.md` aplicado antes de liberar o relatório

## Dados que o piloto precisa
- 3 a 5 vídeos do posto piloto, câmera fixa, 10+ ciclos cada
- Takt Time e Cycle Time padrão do posto
- Sequência padrão (eSOP) do posto
- Para alguns ciclos, cronometragem manual para comparar
