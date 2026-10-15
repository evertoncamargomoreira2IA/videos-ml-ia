# Videos ML IA

Projeto de análise de vídeos de montagem e debug industrial com visão computacional, eventos estruturados e métricas Lean.

## Rodar no Windows (interface de validação)
Dê duplo clique em **`iniciar.bat`**. Na primeira vez ele cria o ambiente Python e instala as dependências, depois abre http://127.0.0.1:8765/ no navegador. Se o PC não tiver Python, ele oferece baixar o `uv`, que instala um Python só para este projeto, sem precisar de administrador.

O passo a passo de validação e a lista de desenvolvimento estão em **[BACKLOG.md](BACKLOG.md)**.

## Estrutura
- `AI_Manufacturing_Video_Analyzer_MVP_v0.1.md`: arquitetura e escopo do MVP.
- `SKILL.md`: regras do agente de análise.
- `mva/`: núcleo Python para ciclos, métricas, anomalias, Yamazumi, ingestão de vídeo e relatórios.
- `mva/schemas/manufacturing_event_schema.json`: contrato de eventos de manufatura.
- `mva/examples/`: eventos de exemplo e relatório ilustrativo.
- `mva/src/mva/webapp/`: interface web local (servidor FastAPI, tela de análises e rotulagem).
- `mva/tests/`: testes automatizados.

## Princípios
1. Vídeo é convertido em eventos estruturados antes da análise por LLM.
2. Métricas são calculadas por código determinístico.
3. Conclusões e hipóteses devem ser sustentadas por evidências e confiança.
4. Correções humanas podem alimentar a melhoria futura dos modelos.

## Requisitos
Python 3.10 ou superior. Consulte `mva/README.md` para instalação e comandos.
