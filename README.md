# Coleta e pré-processamento de notícias do Lance!

Projeto da disciplina de Processamento de Linguagem Natural. A base contém notícias recentes de futebol brasileiro publicadas pelo [Lance!](https://www.lance.com.br/).

## Justificativa da fonte

O Lance! foi escolhido porque publica textos jornalísticos corridos, em português e com diversidade de clubes e competições. Essas características permitem experimentar classificação de textos, análise de frequência, identificação de entidades, agrupamento de matérias e produção de resumos.

A descoberta das matérias usa o [sitemap oficial de notícias](https://www.lance.com.br/sitemap/news/today.xml), mais estável e interpretável que a página inicial. Em seguida, cada página é acessada para obter o texto completo e os metadados estruturados.

## Estrutura

- `coletar_lance.py`: coleta, filtra e limpa as matérias.
- `preprocessar.py`: normaliza, tokeniza, remove ruídos, pontuação e stopwords, além de gerar stems e lemas.
- `pipeline.py`: executa coleta e pré-processamento em uma chamada.
- `analise_lance.ipynb`: notebook que documenta e narra todas as etapas, com análise exploratória e comparação de recortes amostrais (rodada bônus).
- `DICIONARIO_DADOS.md`: explica todos os campos das bases.
- `test/test_pipeline.py`: testes automatizados das etapas principais.
- `outputs/`: bases bruta e processada, nos formatos JSON, JSONL e CSV.

## Instalação

Requer Python 3.9 ou superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

Executar todo o pipeline com até 150 notícias (fonte padrão: artigos recentes de vários dias):

```bash
python pipeline.py --limite 150
```

Somente a coleta:

```bash
python coletar_lance.py --limite 150 --concorrencia 5
```

### Fontes de sitemap

O parâmetro `--fonte` escolhe a abrangência temporal:

- `--fonte recentes` (padrão): sitemap `articles-current.xml`, com ~1200 artigos de **vários dias** — permite montar bases de 100+ notícias.
- `--fonte hoje`: sitemap `news/today.xml`, apenas as notícias **do dia**.

Ambas as fontes são do próprio Lance!; muda somente a janela de tempo.

Somente o pré-processamento de uma base já coletada:

```bash
python preprocessar.py
```

Para explorar todo o fluxo com narrativa, gráficos e a análise bônus, abra o notebook:

```bash
jupyter notebook analise_lance.ipynb
```

Para acrescentar notícias novas sem apagar as anteriores:

```bash
python pipeline.py --limite 30 --acumular
```

O modo incremental elimina duplicatas usando um identificador calculado a partir da URL. Ele pode ser agendado diariamente pelo `cron`, Agendador de Tarefas ou outro serviço de automação.

## Procedimento de coleta

1. Baixa o sitemap escolhido (`articles-current.xml`, de vários dias, por padrão; ou `news/today.xml`).
2. Obtém URL, data e, quando disponível, título e imagem de cada entrada; nos artigos recentes o título é lido depois, na própria página.
3. Mantém seções de futebol brasileiro, como clubes, Brasileirão, Copa do Brasil e Futebol Nacional.
4. Acessa as matérias em paralelo (até cinco simultâneas), com timeout, repetição em caso de falha e identificação de uso acadêmico.
5. Lê os metadados JSON-LD e o corpo HTML de cada matéria.
6. Remove publicidade, apostas, chamadas de matérias relacionadas e mensagens institucionais.
7. Rejeita páginas com menos de 50 palavras e registra erros sem interromper a coleta inteira.

## Pré-processamento

Para cada notícia, são realizadas as seguintes operações:

1. normalização Unicode NFC e conversão para minúsculas;
2. remoção de URLs, e-mails e emojis;
3. remoção de números e pontuação durante a tokenização;
4. tokenização por palavras;
5. remoção de stopwords em português;
6. stemming com o algoritmo Snowball para português;
7. lematização em português com `simplemma`.

O texto original é preservado para auditoria. A base processada inclui as diferentes representações, permitindo comparar o impacto de cada etapa.

## Bases geradas

- `outputs/noticias_lance.json`: base bruta, metadados da execução e erros.
- `outputs/noticias_lance.jsonl`: uma notícia bruta por linha.
- `outputs/noticias_lance_processadas.json`: base completa pré-processada.
- `outputs/noticias_lance_processadas.jsonl`: uma notícia processada por linha.
- `outputs/noticias_lance_processadas.csv`: formato tabular para análise.
- `outputs/estatisticas.json`: volume, vocabulário, seções e termos frequentes.

Consulte `DICIONARIO_DADOS.md` para a definição e o tipo de cada campo.

## Testes

```bash
python -m unittest discover -s test -p "test_*.py" -v
```

Os testes verificam leitura do sitemap, filtro temático, remoção de ruído, normalização e tokenização.

## Considerações éticas e limitações

- A coleta é moderada e usa somente páginas públicas.
- Os textos permanecem atribuídos ao Lance! por meio da URL e do campo `fonte`.
- O projeto tem finalidade acadêmica; redistribuição e uso comercial devem observar os direitos do veículo.
- O sitemap contém notícias recentes. Para formar uma série histórica, é necessário executar periodicamente com `--acumular`.
- Regras de HTML podem precisar de atualização caso o site altere sua estrutura.
