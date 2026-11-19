# Databricks notebook source
# DBTITLE 1,OBT voos
# MAGIC %sql
# MAGIC -- desnormalizacao de proposito: quem consome (agente de IA) nao faz JOIN
# MAGIC CREATE OR REPLACE TABLE voebem.gold.obt_voos AS
# MAGIC SELECT
# MAGIC   -- ===== companhia =====
# MAGIC   f.icao_empresa,
# MAGIC   f.nome_companhia,
# MAGIC   f.numero_voo,
# MAGIC
# MAGIC   -- ===== operacao =====
# MAGIC   f.codigo_di,
# MAGIC   f.descricao_di,
# MAGIC   f.codigo_tipo_linha,
# MAGIC   f.descricao_tipo_linha,
# MAGIC   f.escopo_voo,
# MAGIC
# MAGIC   -- ===== origem =====
# MAGIC   f.icao_origem,
# MAGIC   o.nome_aeroporto        AS nome_aeroporto_origem,
# MAGIC   o.municipio_aeroporto   AS municipio_origem,
# MAGIC   o.uf_aeroporto          AS uf_origem,
# MAGIC   o.pais_aeroporto        AS pais_origem,
# MAGIC
# MAGIC   -- ===== destino =====
# MAGIC   f.icao_destino,
# MAGIC   d.nome_aeroporto        AS nome_aeroporto_destino,
# MAGIC   d.municipio_aeroporto   AS municipio_destino,
# MAGIC   d.uf_aeroporto          AS uf_destino,
# MAGIC   d.pais_aeroporto        AS pais_destino,
# MAGIC
# MAGIC   -- ===== rota, em codigo e por extenso =====
# MAGIC   f.rota                                                            AS rota_icao,
# MAGIC   concat(coalesce(o.municipio_aeroporto, f.icao_origem),  ' - ',
# MAGIC          coalesce(d.municipio_aeroporto, f.icao_destino))           AS rota_municipios,
# MAGIC
# MAGIC   -- ===== tempo =====
# MAGIC   f.partida_prevista,
# MAGIC   f.partida_prevista_data,
# MAGIC   f.partida_prevista_hora,
# MAGIC   f.hora_partida_prevista,
# MAGIC   f.dia_semana,
# MAGIC   f.mes_referencia,
# MAGIC   f.partida_real,
# MAGIC   f.chegada_prevista,
# MAGIC   f.chegada_real,
# MAGIC
# MAGIC   -- ===== metricas =====
# MAGIC   f.atraso_partida_min,
# MAGIC   f.atraso_chegada_min,
# MAGIC   f.minutos_recuperados,
# MAGIC   f.atraso_fora_de_faixa,
# MAGIC   f.partida_pontual,
# MAGIC   f.chegada_pontual,
# MAGIC
# MAGIC   -- ===== situacao =====
# MAGIC   f.situacao_voo,
# MAGIC   f.voo_realizado,
# MAGIC   f.voo_cancelado,
# MAGIC
# MAGIC   f._processado_em
# MAGIC FROM voebem.gold.fato_voos f
# MAGIC -- duas passadas na dimensao: o mesmo aeroporto e origem num voo e destino noutro
# MAGIC LEFT JOIN voebem.gold.dim_aeroporto o ON f.icao_origem  = o.icao_aeroporto
# MAGIC LEFT JOIN voebem.gold.dim_aeroporto d ON f.icao_destino = d.icao_aeroporto