# Databricks notebook source
# DBTITLE 1,Fato voos
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE voebem.gold.fato_voos AS
# MAGIC WITH vra_sem_duplicata AS (
# MAGIC   -- o VRA repete linha (41 exatas no periodo); em empate fica a primeira ingerida
# MAGIC   SELECT * FROM (
# MAGIC     SELECT *,
# MAGIC       ROW_NUMBER() OVER (
# MAGIC         PARTITION BY icao_empresa, numero_voo, codigo_di, codigo_tipo_linha,
# MAGIC                      icao_origem, icao_destino, partida_prevista, partida_real,
# MAGIC                      chegada_prevista, chegada_real, situacao_voo
# MAGIC         ORDER BY _ingerido_em
# MAGIC       ) AS _rn
# MAGIC     FROM voebem.silver.vra
# MAGIC   )
# MAGIC   WHERE _rn = 1
# MAGIC ),
# MAGIC empresa AS (
# MAGIC   -- mesmo ICAO em mais de um registro do cadastro: prefere ativa,
# MAGIC   -- depois razao social mais curta
# MAGIC   SELECT icao, razao_social, origem_cadastro
# MAGIC   FROM (
# MAGIC     SELECT *, ROW_NUMBER() OVER (
# MAGIC       PARTITION BY icao
# MAGIC       ORDER BY CASE WHEN situacao = 'ATIVA' THEN 0 ELSE 1 END, razao_social
# MAGIC     ) AS rn
# MAGIC     FROM voebem.silver.empresas
# MAGIC     WHERE icao IS NOT NULL AND icao <> ''
# MAGIC   )
# MAGIC   WHERE rn = 1
# MAGIC ),
# MAGIC di AS (
# MAGIC   SELECT codigo, descricao FROM voebem.silver.codigos_operacao WHERE dominio = 'codigo_di'
# MAGIC ),
# MAGIC tipo_linha AS (
# MAGIC   SELECT codigo, descricao FROM voebem.silver.codigos_operacao WHERE dominio = 'codigo_tipo_linha'
# MAGIC ),
# MAGIC base AS (
# MAGIC   SELECT
# MAGIC     v.*,
# MAGIC     -- decisao (c): metrica fora da faixa plausivel vira NULL, linha fica
# MAGIC     (v.atraso_partida_min IS NOT NULL AND (v.atraso_partida_min < -120 OR v.atraso_partida_min > 1440))
# MAGIC       OR (v.atraso_chegada_min IS NOT NULL AND (v.atraso_chegada_min < -120 OR v.atraso_chegada_min > 1440))
# MAGIC                                                                     AS atraso_fora_de_faixa
# MAGIC   FROM vra_sem_duplicata v
# MAGIC )
# MAGIC SELECT
# MAGIC   -- ===== dimensao degenerada: companhia =====
# MAGIC   b.icao_empresa,
# MAGIC   COALESCE(e.razao_social, concat('COMPANHIA NAO CADASTRADA (', b.icao_empresa, ')'))
# MAGIC                                                                     AS nome_companhia,
# MAGIC   e.origem_cadastro                                                 AS cadastro_companhia,
# MAGIC   b.numero_voo,
# MAGIC
# MAGIC   -- ===== dimensoes degeneradas: codigos de operacao =====
# MAGIC   b.codigo_di,
# MAGIC   COALESCE(d.descricao, concat('Codigo nao catalogado (', b.codigo_di, ')'))
# MAGIC                                                                     AS descricao_di,
# MAGIC   b.codigo_tipo_linha,
# MAGIC   COALESCE(t.descricao, concat('Codigo nao catalogado (', b.codigo_tipo_linha, ')'))
# MAGIC                                                                     AS descricao_tipo_linha,
# MAGIC
# MAGIC   -- ===== REGRA DE NEGOCIO: escopo do voo =====
# MAGIC   CASE
# MAGIC     WHEN b.codigo_tipo_linha IN ('N', 'C') THEN 'Domestico'
# MAGIC     WHEN b.codigo_tipo_linha IN ('I', 'G') THEN 'Internacional'
# MAGIC     ELSE 'Nao classificado'
# MAGIC   END                                                               AS escopo_voo,
# MAGIC
# MAGIC   -- ===== chaves para dim_aeroporto =====
# MAGIC   b.icao_origem,
# MAGIC   b.icao_destino,
# MAGIC   concat(b.icao_origem, ' - ', b.icao_destino)                      AS rota,
# MAGIC
# MAGIC   -- ===== tempo =====
# MAGIC   b.partida_prevista,
# MAGIC   b.partida_prevista_data,
# MAGIC   b.partida_prevista_hora,
# MAGIC   hour(b.partida_prevista)                                          AS hora_partida_prevista,
# MAGIC   CASE dayofweek(b.partida_prevista_data)
# MAGIC     WHEN 1 THEN 'domingo'  WHEN 2 THEN 'segunda' WHEN 3 THEN 'terca'
# MAGIC     WHEN 4 THEN 'quarta'   WHEN 5 THEN 'quinta'  WHEN 6 THEN 'sexta'
# MAGIC     WHEN 7 THEN 'sabado'
# MAGIC   END                                                               AS dia_semana,
# MAGIC   date_trunc('MONTH', b.partida_prevista_data)                      AS mes_referencia,
# MAGIC   b.partida_real,
# MAGIC   b.chegada_prevista,
# MAGIC   b.chegada_real,
# MAGIC
# MAGIC   -- ===== metricas (decisao (c) aplicada) =====
# MAGIC   CASE WHEN b.atraso_fora_de_faixa THEN NULL ELSE b.atraso_partida_min  END AS atraso_partida_min,
# MAGIC   CASE WHEN b.atraso_fora_de_faixa THEN NULL ELSE b.atraso_chegada_min  END AS atraso_chegada_min,
# MAGIC   CASE WHEN b.atraso_fora_de_faixa THEN NULL ELSE b.minutos_recuperados END AS minutos_recuperados,
# MAGIC   b.atraso_fora_de_faixa,
# MAGIC
# MAGIC   -- ===== REGRA DE NEGOCIO: pontualidade a 15 minutos =====
# MAGIC   CASE WHEN b.atraso_fora_de_faixa OR b.atraso_partida_min IS NULL THEN NULL
# MAGIC        ELSE b.atraso_partida_min <= 15 END                          AS partida_pontual,
# MAGIC   CASE WHEN b.atraso_fora_de_faixa OR b.atraso_chegada_min IS NULL THEN NULL
# MAGIC        ELSE b.atraso_chegada_min <= 15 END                          AS chegada_pontual,
# MAGIC
# MAGIC   -- ===== situacao =====
# MAGIC   b.situacao_voo,
# MAGIC   (b.situacao_voo = 'CANCELADO')                                    AS voo_cancelado,
# MAGIC   (b.situacao_voo = 'REALIZADO')                                    AS voo_realizado,
# MAGIC
# MAGIC   current_timestamp()                                               AS _processado_em
# MAGIC FROM base b
# MAGIC LEFT JOIN empresa    e ON b.icao_empresa      = e.icao
# MAGIC LEFT JOIN di         d ON b.codigo_di         = d.codigo
# MAGIC LEFT JOIN tipo_linha t ON b.codigo_tipo_linha = t.codigo