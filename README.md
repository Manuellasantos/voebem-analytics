# Pontualidade de Voos ANAC — voebem 2026

Análise de pontualidade de voos a partir de dados públicos da ANAC (VRA — microdados de voos regulares), desenvolvida integralmente na plataforma **Databricks**.

## Contexto dos dados

A base analisada é o **VRA (microdados de voos)** publicado pela ANAC: cada linha é uma etapa de voo com partida/chegada prevista e realizada, ICAO da empresa, origem, destino e situação (realizado, cancelado etc.). Foram processadas **mais de 1 milhão de etapas de voo**, enriquecidas com os cadastros de referência da própria ANAC:

* **Aeródromos** — nome, município, UF, país (derivado do prefixo ICAO)
* **Empresas aéreas** — razão social, situação no cadastro
* **Códigos de operação** — DI (tipo de operação) e tipo de linha

## Tecnologias

Projeto 100% desenvolvido no Databricks:

* **Notebooks** com Python e SQL (`%sql`) sobre Spark
* **Unity Catalog** com catálogo `voebem` e arquitetura **medalhão** (bronze → silver → gold)
* **AI/BI Dashboard** (arquivo `.lvdash.json` versionado neste repo)
* **IA do Databricks (Assistant/Genie)** com **prompts estruturados** — contexto dos dados, regras de negócio e saída esperada declarados explicitamente em cada prompt — usada na geração e revisão do SQL/PySpark do pipeline e na construção do dashboard
* **Git/GitHub** para versionamento

## Estrutura do pipeline

| Camada | Notebooks | O que faz |
| --- | --- | --- |
| Bronze | `bronze_vra`, `bronze_referencias` | Ingestão bruta do VRA e dos cadastros ANAC |
| Silver | `silver_espelho` | Espelho tipado do bronze: string `'null'` vira NULL, timestamps, atrasos em minutos (partida, chegada e minutos recuperados) |
| Gold | `gold_governaça`, `gold_sql/01_dim_aeroporto`, `02_fato_voos`, `03_obt_voos` | Dimensão de aeroportos, fato de voos com regras de negócio e OBT desnormalizada de consumo (`voebem.gold.obt_voos`) |
| Qualidade | `Papiline_Qualidade/01_vra_marcado`, `02_vra_auditado`, `03_vra_quarentena` | Marcação, auditoria e quarentena de linhas |
| Perguntas | `Perguntas_sql/P1.sql` | Perguntas de negócio que originaram o dashboard |

## Regras de negócio

* **Pontualidade**: voo pontual = atraso de partida **≤ 15 minutos**
* **Faixa plausível**: atrasos < -120 min ou > 1440 min viram NULL (a linha fica, a métrica não distorce a média)
* **Deduplicação**: o VRA repete linhas; empate mantém a primeira ingerida
* **Escopo do voo**: tipos N/C = doméstico, I/G = internacional
* **Cortes de volume**: rankings só consideram aeroportos com 5.000+ voos, rotas com 2.000+ e companhias com 10.000+ (evita distorção de amostras pequenas)

## Dashboard

![Dashboard — Pontualidade de Voos ANAC](dashboard.png)

O dashboard (`Pontualidade de Voos ANAC - voebem 2026.lvdash.json`, abrível como dashboard no Databricks) responde às perguntas de negócio do projeto. O que cada visualização mostra:

### KPIs (linha de cima)

| Indicador | O que mostra |
| --- | --- |
| Voos no período | Total de etapas de voo analisadas |
| Partida pontual (≤ 15 min) — % | % de voos que decolaram com atraso de até 15 minutos |
| Voos cancelados — % | % de voos cancelados sobre o total |
| Atraso médio de partida (min) | Atraso médio na decolagem, em minutos |

### Gráficos

* **Aeroportos com maior % de atraso na partida (≥ 5.000 voos)** — ranking dos aeroportos brasileiros de origem que mais atrasam a decolagem, com corte de volume para não penalizar aeroportos pequenos (P1)
* **Atraso médio de partida: doméstico x internacional** — compara o atraso médio entre os dois escopos de voo (P4)
* **Atraso médio por hora prevista de partida (efeito cascata)** — linha do tempo do dia: mostra o atraso acumulando ao longo das horas, evidência do efeito cascata em que o atraso de um voo contamina os seguintes (P2)
* **Piores rotas domésticas por atraso médio de partida (≥ 2.000 voos)** — rotas domésticas com pior atraso médio na decolagem (P1b)
* **Rotas sem recuperação de atraso (perdem tempo no ar)** — rotas em que o atraso de saída não é recuperado em voo, ou seja, o atraso de chegada é ainda maior (P5b)
* **Minutos recuperados em voo por companhia (≥ 10.000 voos)** — quanto atraso de saída cada companhia consegue compensar no ar (P5)

### Tabela

* **Pontualidade x cancelamento por companhia (≥ 10.000 voos)** — para cada companhia: nº de voos, % de partidas pontuais, % de cancelados e atraso médio (P3)

## Como visualizar

O arquivo `.lvdash.json` é o código-fonte do dashboard: aberto no Databricks, ele é renderizado com todos os gráficos e filtros. Os notebooks do pipeline estão na pasta `voebem/` e rodam na ordem bronze → silver → gold.
