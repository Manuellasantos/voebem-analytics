# Databricks notebook source
# DBTITLE 1,Quarentena
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMP VIEW vra_quarentena
# MAGIC COMMENT 'Silver quarentena - espelho DIAGNOSTICO dos registros de silver.vra que
# MAGIC  reprovaram em alguma expectation do contrato de dados, com o motivo por registro.
# MAGIC  NAO e filtro: silver.vra permanece com a contagem original. A decisao de excluir
# MAGIC  ou nao cada categoria e de negocio e acontece na gold.'
# MAGIC AS
# MAGIC -- repete marcado + auditado aqui dentro: a quarentena tem que ser autonoma
# MAGIC WITH vra_marcado AS (
# MAGIC   WITH aerodromo AS (
# MAGIC     SELECT DISTINCT icao FROM voebem.silver.aerodromos
# MAGIC     WHERE icao IS NOT NULL AND icao <> ''
# MAGIC   ),
# MAGIC   empresa AS (
# MAGIC     SELECT DISTINCT icao FROM voebem.silver.empresas
# MAGIC     WHERE icao IS NOT NULL AND icao <> ''
# MAGIC   )
# MAGIC   SELECT
# MAGIC     v.*,
# MAGIC     (ao.icao IS NOT NULL) AS origem_no_cadastro,
# MAGIC     (ad.icao IS NOT NULL) AS destino_no_cadastro,
# MAGIC     (em.icao IS NOT NULL) AS empresa_no_cadastro
# MAGIC   FROM voebem.silver.vra v
# MAGIC   LEFT JOIN aerodromo ao ON v.icao_origem  = ao.icao
# MAGIC   LEFT JOIN aerodromo ad ON v.icao_destino = ad.icao
# MAGIC   LEFT JOIN empresa   em ON v.icao_empresa = em.icao
# MAGIC ),
# MAGIC vra_auditado AS (
# MAGIC   SELECT
# MAGIC     *
# MAGIC     , (partida_prevista IS NOT NULL AND chegada_prevista IS NOT NULL) AS chk_horarios_previstos_presentes
# MAGIC     , (situacao_voo IN ('REALIZADO', 'CANCELADO'))                      AS chk_situacao_voo_conhecida
# MAGIC     , (partida_prevista IS NULL OR chegada_prevista IS NULL
# MAGIC         OR chegada_prevista > partida_prevista)                        AS chk_chegada_prevista_depois_partida
# MAGIC     , (partida_real IS NULL OR chegada_real IS NULL
# MAGIC         OR chegada_real > partida_real)                                AS chk_chegada_real_depois_partida
# MAGIC     , (atraso_partida_min IS NULL
# MAGIC         OR atraso_partida_min BETWEEN -120 AND 1440)                   AS chk_atraso_partida_plausivel
# MAGIC     , (atraso_chegada_min IS NULL
# MAGIC         OR atraso_chegada_min BETWEEN -120 AND 1440)                   AS chk_atraso_chegada_plausivel
# MAGIC     , empresa_no_cadastro                                             AS chk_empresa_no_cadastro_anac
# MAGIC     , origem_no_cadastro                                              AS chk_aeroporto_origem_no_cadastro
# MAGIC     , destino_no_cadastro                                             AS chk_aeroporto_destino_no_cadastro
# MAGIC   FROM vra_marcado
# MAGIC )
# MAGIC SELECT
# MAGIC   -- motivo por categoria: um registro pode reprovar em mais de um check
# MAGIC   *,
# MAGIC   concat_ws(' | ',
# MAGIC     CASE WHEN partida_prevista IS NULL OR chegada_prevista IS NULL
# MAGIC          THEN 'horarios_previstos_presentes' END,
# MAGIC     CASE WHEN situacao_voo NOT IN ('REALIZADO', 'CANCELADO') OR situacao_voo IS NULL
# MAGIC          THEN 'situacao_voo_conhecida' END,
# MAGIC     CASE WHEN partida_prevista IS NOT NULL AND chegada_prevista IS NOT NULL
# MAGIC               AND chegada_prevista <= partida_prevista
# MAGIC          THEN 'chegada_prevista_depois_da_partida_prevista' END,
# MAGIC     CASE WHEN partida_real IS NOT NULL AND chegada_real IS NOT NULL
# MAGIC               AND chegada_real <= partida_real
# MAGIC          THEN 'chegada_real_depois_da_partida_real' END,
# MAGIC     CASE WHEN atraso_partida_min IS NOT NULL
# MAGIC               AND (atraso_partida_min < -120 OR atraso_partida_min > 1440)
# MAGIC          THEN 'atraso_partida_plausivel' END,
# MAGIC     CASE WHEN atraso_chegada_min IS NOT NULL
# MAGIC               AND (atraso_chegada_min < -120 OR atraso_chegada_min > 1440)
# MAGIC          THEN 'atraso_chegada_plausivel' END,
# MAGIC     CASE WHEN NOT empresa_no_cadastro THEN 'empresa_no_cadastro_anac' END,
# MAGIC     CASE WHEN NOT origem_no_cadastro THEN 'aeroporto_origem_no_cadastro_anac' END,
# MAGIC     CASE WHEN NOT destino_no_cadastro THEN 'aeroporto_destino_no_cadastro_anac' END
# MAGIC   ) AS motivos_quarentena,
# MAGIC   current_timestamp() AS _quarentenado_em
# MAGIC FROM vra_auditado
# MAGIC -- espelho diagnostico: nenhuma linha sai da silver; excluir ou nao cada
# MAGIC -- motivo e decisao de negocio, tomada la na gold
# MAGIC WHERE NOT (
# MAGIC       partida_prevista IS NOT NULL AND chegada_prevista IS NOT NULL
# MAGIC   AND situacao_voo IN ('REALIZADO', 'CANCELADO')
# MAGIC   AND (partida_prevista IS NULL OR chegada_prevista IS NULL OR chegada_prevista > partida_prevista)
# MAGIC   AND (partida_real IS NULL OR chegada_real IS NULL OR chegada_real > partida_real)
# MAGIC   AND (atraso_partida_min IS NULL OR atraso_partida_min BETWEEN -120 AND 1440)
# MAGIC   AND (atraso_chegada_min IS NULL OR atraso_chegada_min BETWEEN -120 AND 1440)
# MAGIC   AND empresa_no_cadastro
# MAGIC   AND origem_no_cadastro
# MAGIC   AND destino_no_cadastro
# MAGIC );