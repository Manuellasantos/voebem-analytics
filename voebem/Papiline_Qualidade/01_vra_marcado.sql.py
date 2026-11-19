# Databricks notebook source
# DBTITLE 1,Marcacao de integridade
# MAGIC %sql
# MAGIC -- passo 1 do contrato de qualidade: marca integridade referencial, sem julgar.
# MAGIC -- tudo em view temporaria: nada e materializado, a silver nao e tocada
# MAGIC CREATE TEMPORARY VIEW vra_marcado AS
# MAGIC WITH aerodromo AS (
# MAGIC   SELECT DISTINCT icao FROM voebem.silver.aerodromos
# MAGIC   WHERE icao IS NOT NULL AND icao <> ''
# MAGIC ),
# MAGIC empresa AS (
# MAGIC   SELECT DISTINCT icao FROM voebem.silver.empresas
# MAGIC   WHERE icao IS NOT NULL AND icao <> ''
# MAGIC )
# MAGIC SELECT
# MAGIC   v.*,
# MAGIC   (ao.icao IS NOT NULL) AS origem_no_cadastro,
# MAGIC   (ad.icao IS NOT NULL) AS destino_no_cadastro,
# MAGIC   (em.icao IS NOT NULL) AS empresa_no_cadastro
# MAGIC FROM voebem.silver.vra v
# MAGIC LEFT JOIN aerodromo ao ON v.icao_origem  = ao.icao
# MAGIC LEFT JOIN aerodromo ad ON v.icao_destino = ad.icao
# MAGIC LEFT JOIN empresa   em ON v.icao_empresa = em.icao;