# Databricks notebook source
# DBTITLE 1,Fontes de referencia
from pyspark.sql import functions as F

# cadastros de apoio da ANAC: aerodromos publicos e empresas aereas
REF = "/Volumes/voebem/bronze/arquivos/referencias"

# caractere que NAO existe no arquivo -> desliga o quoting do leitor de CSV
SEM_ASPAS = chr(0)

# COMMAND ----------

# DBTITLE 1,Cadastro de aerodromos
# so aerodromo publico brasileiro aqui. aeroporto estrangeiro do VRA nao existe
# nesse cadastro - a lacuna e tratada la na gold, com fallback textual
aerodromos = (
    spark.read.format("csv")
    .option("sep", ";")
    .option("header", "true")
    .option("skipRows", 1)
    .option("encoding", "ISO-8859-1")   # latin-1, nao UTF-8
    .option("quote", SEM_ASPAS)         # desliga o quoting: aspas aqui sao "segundos"
    .load(f"{REF}/AerodromosPublicos.csv")
)

aerodromos = aerodromos.select(
    F.col("`Código OACI`").alias("icao"),
    F.col("CIAD").alias("ciad"),
    F.col("Nome").alias("nome"),
    F.col("`Município`").alias("municipio"),
    F.col("UF").alias("uf"),
    F.col("`Município Servido`").alias("municipio_servido"),
    F.col("`UF Servido`").alias("uf_servido"),
    F.col("Latitude").alias("latitude"),
    F.col("Longitude").alias("longitude"),
    F.col("Altitude").alias("altitude"),
    F.col("`Situação`").alias("situacao"),
).withColumn("_ingerido_em", F.current_timestamp())

aerodromos.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable("voebem.bronze.aerodromos")

print(f"bronze.aerodromos: {spark.table('voebem.bronze.aerodromos').count():,} linhas")
display(spark.sql("SELECT icao, nome, municipio, uf FROM voebem.bronze.aerodromos WHERE icao IN ('SBRB','SBGR','SBSP','SBFZ')"))

# COMMAND ----------

# DBTITLE 1,Cadastros de empresas
def ler_empresas(arquivo: str):
    """Le um cadastro de empresas. Sem uniao, sem enriquecimento: uma tabela por arquivo."""
    return (
        spark.read.format("csv")
        .option("sep", ";")
        .option("header", "true")
        .option("skipRows", 1)
        .option("encoding", "UTF-8")
        .option("quote", '"')
        .load(f"{REF}/{arquivo}")
        .select(
            F.col("ICAO").alias("icao"),
            F.col("Estrangeira").alias("sigla_iata"),
            F.col("Razao").alias("razao_social"),
            F.col("Servico").alias("servico"),
            F.col("Cidade").alias("cidade"),
            F.col("UF").alias("uf"),
            F.col("Ativa").alias("situacao"),
        )
        .withColumn("_arquivo_origem", F.lit(arquivo))
        .withColumn("_ingerido_em", F.current_timestamp())
    )


# um arquivo vira uma tabela: nacionais e estrangeiras chegam em cadastros
# separados na origem, e a uniao so acontece na silver
for arquivo, tabela in [
    ("pda_empresas_aereas_nacionais.csv",    "voebem.bronze.empresas_nacionais"),
    ("pda_empresas_aereas_estrangeiros.csv", "voebem.bronze.empresas_estrangeiras"),
]:
    ler_empresas(arquivo).write.format("delta").mode("overwrite").option(
        "overwriteSchema", "true"
    ).saveAsTable(tabela)
    print(f"{tabela}: {spark.table(tabela).count():,} linhas")


# COMMAND ----------

# DBTITLE 1,Conferencia de ICAO
# quase toda estrangeira tem ICAO. no nacional a maioria e operador sem codigo
# (agricola, taxi aereo) - esses nunca vao casar com o VRA, e normal
display(spark.sql("""
    SELECT 'empresas_nacionais' AS tabela, COUNT(*) AS linhas,
           COUNT(CASE WHEN icao IS NOT NULL AND icao <> '' THEN 1 END) AS com_icao
    FROM voebem.bronze.empresas_nacionais
    UNION ALL
    SELECT 'empresas_estrangeiras', COUNT(*),
           COUNT(CASE WHEN icao IS NOT NULL AND icao <> '' THEN 1 END)
    FROM voebem.bronze.empresas_estrangeiras
"""))

display(spark.sql("""
    SELECT icao, razao_social, servico, uf, situacao
    FROM voebem.bronze.empresas_nacionais
    WHERE icao IN ('GLO','TAM','AZU','PAM')
    ORDER BY icao
"""))

display(spark.sql("""
    SELECT icao, razao_social, servico, situacao
    FROM voebem.bronze.empresas_estrangeiras
    WHERE icao IN ('AAL','TAP','AVA','ARG')
    ORDER BY icao
"""))


# COMMAND ----------

# DBTITLE 1,Seed de codigos de operacao
# decodificadores transcritos do dicionario de variaveis da ANAC -
# nao existe CSV disso, e o unico seed manual do projeto
CODIGOS = [
    ("codigo_di", "0", "Etapa Regular"),
    ("codigo_di", "2", "Etapa Extra"),
    ("codigo_di", "3", "Etapa de Retorno"),
    ("codigo_di", "4", "Inclusão de Etapa"),
    ("codigo_di", "6", "Etapa Não Remunerada Sem Transporte de Objetos"),
    ("codigo_di", "7", "Etapa de Voo de Fretamento"),
    ("codigo_di", "9", "Etapa de Voo Charter"),
    ("codigo_di", "D", "Etapa de Voo Duplicada"),
    ("codigo_di", "E", "Etapa Não Remunerada Com Transporte de Objetos"),
    ("codigo_tipo_linha", "N", "Doméstica Mista"),
    ("codigo_tipo_linha", "C", "Doméstica Cargueira"),
    ("codigo_tipo_linha", "I", "Internacional Mista"),
    ("codigo_tipo_linha", "G", "Internacional Cargueira"),
]

codigos = spark.createDataFrame(CODIGOS, "dominio string, codigo string, descricao string")
codigos.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable("voebem.bronze.codigos_operacao")

print(f"bronze.codigos_operacao: {spark.table('voebem.bronze.codigos_operacao').count()} linhas")
display(spark.table("voebem.bronze.codigos_operacao"))

# COMMAND ----------

# DBTITLE 1,Inventario do bronze
# inventario da camada bronze no fim da carga
display(spark.sql("SHOW TABLES IN voebem.bronze"))

# COMMAND ----------

# DBTITLE 1,Historico delta
# historico delta da tabela principal: toda execucao e um CREATE OR REPLACE
display(spark.sql("""
    SELECT version, timestamp, operation,
           operationMetrics.numOutputRows AS linhas_escritas
    FROM (DESCRIBE HISTORY voebem.bronze.vra)
    ORDER BY version
"""))


# COMMAND ----------

# DBTITLE 1,Time travel
# time travel: a primeira versao tem que ter a mesma contagem da atual
# - e a prova de que a carga nao duplicou linha
display(spark.sql("""
    SELECT 'versao 0 (1a carga)'   AS versao,
           COUNT(*)                AS linhas,
           MIN(_ingerido_em)       AS ingerido_em
    FROM voebem.bronze.vra VERSION AS OF 0
    UNION ALL
    SELECT 'versao atual', COUNT(*), MIN(_ingerido_em)
    FROM voebem.bronze.vra
"""))

# COMMAND ----------

# DBTITLE 1,Comentarios de tabela
# comentario de cada tabela: o que e, de onde veio e como se liga
for tabela, comentario in [
    ("voebem.bronze.aerodromos",
     "Bronze - cadastro de aerodromos publicos da ANAC, como chegou. Chave: codigo ICAO (OACI). "
     "Cobre apenas aerodromos brasileiros - aeroportos estrangeiros do VRA nao estao aqui."),
    ("voebem.bronze.empresas_nacionais",
     "Bronze - cadastro de empresas aereas NACIONAIS da ANAC, como chegou. Chave: codigo ICAO. "
     "Nao unir com empresas_estrangeiras nesta camada: a uniao e feita na silver."),
    ("voebem.bronze.empresas_estrangeiras",
     "Bronze - cadastro de empresas aereas ESTRANGEIRAS autorizadas a operar no Brasil, como chegou. "
     "Chave: codigo ICAO. Cadastro separado do nacional na origem, mantido separado no bronze."),
    ("voebem.bronze.codigos_operacao",
     "Bronze - seed table curada a partir da pagina de descricao de variaveis da ANAC. "
     "Traduz codigo_di e codigo_tipo_linha para descricao em portugues."),
]:
    spark.sql(f"COMMENT ON TABLE {tabela} IS '{comentario}'")

print("comentarios aplicados")