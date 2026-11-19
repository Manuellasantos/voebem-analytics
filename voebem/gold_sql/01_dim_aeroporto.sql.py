# Databricks notebook source
# DBTITLE 1,Dimensao aeroporto
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE voebem.gold.dim_aeroporto AS
# MAGIC WITH aeroportos_do_fato AS (
# MAGIC   -- a dimensao nasce do fato: so entra aeroporto que apareceu em alguma etapa;
# MAGIC   -- aerodromo do cadastro que nao movimentou voo nenhum fica de fora
# MAGIC   SELECT DISTINCT icao_origem  AS icao FROM voebem.silver.vra WHERE icao_origem  IS NOT NULL AND icao_origem  <> ''
# MAGIC   UNION
# MAGIC   SELECT DISTINCT icao_destino AS icao FROM voebem.silver.vra WHERE icao_destino IS NOT NULL AND icao_destino <> ''
# MAGIC ),
# MAGIC -- defesa: se a ANAC republicar o cadastro com ICAO repetido, o join
# MAGIC -- multiplicaria linhas do fato sem dar erro nenhum. Hoje sao 496/496.
# MAGIC cadastro AS (
# MAGIC   SELECT icao, nome, municipio, uf_nome, municipio_servido, uf_servido_nome
# MAGIC   FROM (
# MAGIC     SELECT *, ROW_NUMBER() OVER (PARTITION BY icao ORDER BY nome) AS rn
# MAGIC     FROM voebem.silver.aerodromos
# MAGIC     WHERE icao IS NOT NULL AND icao <> ''
# MAGIC   )
# MAGIC   WHERE rn = 1
# MAGIC )
# MAGIC SELECT
# MAGIC   a.icao                                                              AS icao_aeroporto,
# MAGIC   -- fallback textual obrigatorio: coluna que a IA vai ler nao pode vir NULL
# MAGIC   COALESCE(c.nome, concat('AEROPORTO FORA DO CADASTRO ANAC (', a.icao, ')'))
# MAGIC                                                                       AS nome_aeroporto,
# MAGIC   c.municipio                                                         AS municipio_aeroporto,
# MAGIC   c.uf_nome                                                           AS uf_aeroporto,
# MAGIC   -- Brasil por prefixo ICAO: S seguido de B, D, I, J, N, S ou W
# MAGIC   CASE WHEN a.icao RLIKE '^S[BDIJNSW]' THEN 'Brasil' ELSE 'Exterior' END
# MAGIC                                                                       AS pais_aeroporto,
# MAGIC   (c.icao IS NOT NULL)                                                AS no_cadastro_anac,
# MAGIC   current_timestamp()                                                 AS _processado_em
# MAGIC FROM aeroportos_do_fato a
# MAGIC LEFT JOIN cadastro c ON a.icao = c.icao