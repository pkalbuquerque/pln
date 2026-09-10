# Dicionário de dados

## Base bruta - `outputs/noticias_lance.json`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | texto | Identificador determinístico, calculado a partir da URL. |
| `titulo` | texto | Título da matéria. |
| `subtitulo` | texto ou nulo | Linha fina/descrição informada pelo site. |
| `texto` | texto | Corpo limpo da matéria, com parágrafos separados por linha em branco. |
| `paragrafos` | lista de textos | Corpo segmentado em parágrafos. |
| `quantidade_palavras` | inteiro | Contagem simples de palavras no texto bruto limpo. |
| `autor` | texto ou nulo | Autor ou autores informados nos metadados. |
| `publicado_em` | data ISO 8601 | Data e hora de publicação convertida para UTC. |
| `modificado_em` | data ISO 8601 ou nulo | Última alteração informada pelo site. |
| `secao` | texto ou nulo | Editoria ou clube associado à matéria. |
| `imagem` | URL ou nulo | Endereço da imagem principal. |
| `url` | URL | Endereço canônico da matéria. |
| `fonte` | texto | Nome do veículo, neste recorte sempre `Lance!`. |

O objeto principal também registra fonte do sitemap, instante da coleta, filtro, totais e erros. O formato JSONL contém uma notícia por linha.

## Base processada - `outputs/noticias_lance_processadas.json`

| Campo | Tipo | Descrição |
|---|---|---|
| `id`, `titulo`, `secao`, `publicado_em`, `url` | variados | Metadados preservados para rastreabilidade. |
| `texto_original` | texto | Texto antes do pré-processamento linguístico. |
| `texto_normalizado` | texto | Texto em minúsculas, Unicode NFC, sem URLs, e-mails e emojis. |
| `tokens` | lista de textos | Palavras após remoção de números e pontuação. |
| `tokens_sem_stopwords` | lista de textos | Tokens sem palavras funcionais frequentes do português. |
| `stems` | lista de textos | Radicais gerados pelo algoritmo Snowball para português. |
| `lemas` | lista de textos | Formas canônicas estimadas pela biblioteca `simplemma`. |
| `quantidade_tokens` | inteiro | Número de tokens antes da remoção de stopwords. |
| `quantidade_tokens_limpos` | inteiro | Número de tokens disponíveis para análise após a limpeza. |

As listas são mantidas no JSON/JSONL. No CSV, elas são serializadas como termos separados por espaço.
