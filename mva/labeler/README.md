# Laboratório de anotação por frame

Protótipo sem dependências para rotular manualmente quadros de vídeos de manufatura.

## Abrir

A interface é um arquivo estático. Abra `index.html` em um navegador moderno ou sirva esta pasta localmente:

```bash
python -m http.server 8000
```

Depois acesse `http://localhost:8000` dentro de `mva/labeler`.

## Fluxo

1. Selecione um arquivo MP4, MOV ou WebM. O vídeo é carregado localmente no navegador.
2. Pause e use os controles ou as setas ← / → para navegar. Escolha o FPS nominal para o passo de um frame.
3. Selecione ação, classe de valor, categoria, posto e objeto; salve o rótulo do frame.
4. Exporte JSON para preservar miniaturas JPEG junto aos rótulos, ou CSV para metadados sem imagens.

Os rótulos ficam somente na memória da aba. Exporte antes de fechar ou recarregar a página. Substituir um rótulo no mesmo número de frame atualiza a anotação existente.

## Formato exportado

O JSON usa `schema_version: mva.frame_annotations.v1`, contendo timestamp, número do frame, rótulo humano, confiança manual, metadados do vídeo e uma miniatura JPEG em base64. É um formato de anotação para frames e **não** é diretamente o Manufacturing Event Schema: um frame isolado não define duração ou intervalo temporal de um evento.

O protótipo não envia o vídeo ou os rótulos a um servidor e não treina um modelo. Para montar um pipeline de treinamento, o próximo passo é uma API que recebe esse dataset, valida os rótulos, extrai/normaliza frames e registra versões do dataset.

## Limitações

- O passo por frame usa o FPS nominal escolhido; vídeos com taxa variável podem não avançar exatamente para o próximo frame codificado.
- A exportação JSON inclui uma miniatura JPEG por rótulo, então arquivos podem ficar grandes. Use CSV quando não precisar das imagens.
- O vídeo original não é incluído na exportação.
