# Videos ML IA

Projeto de análise de vídeos de montagem e debug industrial com visão computacional, eventos estruturados e métricas Lean.

## Estrutura
- `AI_Manufacturing_Video_Analyzer_MVP_v0.1.md`: arquitetura e escopo do MVP.
- `SKILL.md`: regras do agente de análise.
- `mva/`: núcleo Python para ciclos, métricas, anomalias, Yamazumi, ingestão de vídeo e relatórios.
- `mva/schemas/manufacturing_event_schema.json`: contrato de eventos de manufatura.
- `mva/examples/`: eventos de exemplo e relatório ilustrativo.
- `mva/labeler/`: ferramenta HTML de anotação.
- `mva/tests/`: testes automatizados.

## Princípios
1. Vídeo é convertido em eventos estruturados antes da análise por LLM.
2. Métricas são calculadas por código determinístico.
3. Conclusões e hipóteses devem ser sustentadas por evidências e confiança.
4. Correções humanas podem alimentar a melhoria futura dos modelos.

## Requisitos
Python 3.10 ou superior. Consulte `mva/README.md` para instalação e comandos.
