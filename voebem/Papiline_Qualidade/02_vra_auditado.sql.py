# Databricks notebook source
# DBTITLE 1,Contrato de qualidade
# MAGIC %sql
# MAGIC -- passo 2: os nove checks, todos em modo warn - medem sem descartar linha.
# MAGIC -- NULL aprova: campo opcional nao pode reprovar o registro
# MAGIC CREATE OR REPLACE TEMP VIEW vra_auditado
# MAGIC COMMENT 'Contrato de dados de silver.vra. Nove checks de qualidade em modo warn:
# MAGIC  medem qualidade sem descartar linha. A silver segue com a contagem original.'
# MAGIC AS SELECT
# MAGIC   *
# MAGIC   -- === completude ===
# MAGIC   , (partida_prevista IS NOT NULL AND chegada_prevista IS NOT NULL) AS chk_horarios_previstos_presentes
# MAGIC   , (situacao_voo IN ('REALIZADO', 'CANCELADO'))                      AS chk_situacao_voo_conhecida
# MAGIC   -- === coerencia temporal (NULL aprovado explicitamente) ===
# MAGIC   , (partida_prevista IS NULL OR chegada_prevista IS NULL
# MAGIC       OR chegada_prevista > partida_prevista)                        AS chk_chegada_prevista_depois_partida
# MAGIC   , (partida_real IS NULL OR chegada_real IS NULL
# MAGIC       OR chegada_real > partida_real)                                AS chk_chegada_real_depois_partida
# MAGIC   -- === faixa plausivel: -2h de antecipacao a 24h de atraso ===
# MAGIC   , (atraso_partida_min IS NULL
# MAGIC       OR atraso_partida_min BETWEEN -120 AND 1440)                   AS chk_atraso_partida_plausivel
# MAGIC   , (atraso_chegada_min IS NULL
# MAGIC       OR atraso_chegada_min BETWEEN -120 AND 1440)                   AS chk_atraso_chegada_plausivel
# MAGIC   -- === integridade referencial (a flag vem do passo 1) ===
# MAGIC   , empresa_no_cadastro                                             AS chk_empresa_no_cadastro_anac
# MAGIC   , origem_no_cadastro                                              AS chk_aeroporto_origem_no_cadastro
# MAGIC   , destino_no_cadastro                                             AS chk_aeroporto_destino_no_cadastro
# MAGIC FROM vra_marcado;