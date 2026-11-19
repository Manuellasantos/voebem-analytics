# Databricks notebook source
# DBTITLE 1,Carga bruta do VRA
# MAGIC %md
# MAGIC #Bronze - VRA da ANAC
# MAGIC
# MAGIC Carga bruta dos CSVs mensais do VRA (Voo Regular Ativo) que chegam em
# MAGIC `/Volumes/voebem/bronze/arquivos/vra/`. Tudo entra como string e nenhuma linha e
# MAGIC descartada: decidir o que cada coluna significa e problema da silver.
# MAGIC

# COMMAND ----------

# DBTITLE 1,Caminho e tabela alvo
from pyspark.sql import functions as F

# 12 CSVs mensais do VRA, um por mes, separados por ";"
CAMINHO = "/Volumes/voebem/bronze/arquivos/vra/"
TABELA = "voebem.bronze.vra"


# COMMAND ----------

# DBTITLE 1,Leitura permissiva dos CSVs

# leitura permissiva de proposito: bronze guarda o dado exatamente como chegou.
# se alguma linha tiver que ser descartada, e decisao da silver, nao daqui
bruto = (
    spark.read.format("csv")
    .option("sep", ";")
    .option("header", "true")
    .option("skipRows", 1)          # descarta "Atualizado em: ..." (e o BOM junto)
    .option("quote", '"')
    .option("escape", '"')
    .option("encoding", "UTF-8")
    .option("mode", "PERMISSIVE")   # bronze nao descarta linha nenhuma
    .load(CAMINHO)
)

print("colunas lidas do arquivo:")
for c in bruto.columns:
    print(f"  {c!r}")

# COMMAND ----------

# DBTITLE 1,Renomeacao das colunas
# cabecalho original da ANAC -> snake_case. o assert para a carga na hora se a
# ANAC renomear coluna, em vez de criar tabela errada em silencio
RENOMEAR = {
    "ICAO Empresa Aérea": "icao_empresa",
    "Número Voo": "numero_voo",
    "Código Autorização (DI)": "codigo_di",
    "Código Tipo Linha": "codigo_tipo_linha",
    "ICAO Aeródromo Origem": "icao_origem",
    "ICAO Aeródromo Destino": "icao_destino",
    "Partida Prevista": "partida_prevista",
    "Partida Real": "partida_real",
    "Chegada Prevista": "chegada_prevista",
    "Chegada Real": "chegada_real",
    "Situação Voo": "situacao_voo",
    "Código Justificativa": "codigo_justificativa",
}

faltando = [c for c in RENOMEAR if c not in bruto.columns]
assert not faltando, f"Coluna esperada nao encontrada no CSV: {faltando}"

renomeado = bruto.select(
    *[F.col(f"`{origem}`").cast("string").alias(novo) for origem, novo in RENOMEAR.items()]
)


# COMMAND ----------

# DBTITLE 1,Colunas de auditoria
# auditoria: de qual arquivo cada linha veio e quando entrou
bronze = renomeado.withColumn(
    "_arquivo_origem", F.col("_metadata.file_name")
).withColumn(
    "_ingerido_em", F.current_timestamp()
)

# COMMAND ----------

# DBTITLE 1,Escrita idempotente no bronze
# full refresh idempotente: rodar de novo da no mesmo resultado
(
    bronze.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TABELA)
)

print(f"{TABELA}: {spark.table(TABELA).count():,} linhas")

# COMMAND ----------

spark.sql(f"""
    COMMENT ON TABLE {TABELA} IS
    'Bronze - VRA (Voo Regular Ativo) da ANAC, 12 meses (ago/2025 a jul/2026).
     Dado bruto: todas as colunas string, nenhuma linha descartada.
     Carga full refresh idempotente a partir de /Volumes/voebem/bronze/arquivos/vra/.'
""")


# COMMAND ----------

# DBTITLE 1,Conferencia por arquivo
# conferencia da carga: 12 arquivos, um por mes, nenhum sumido
display(
    spark.sql(f"""
        SELECT _arquivo_origem, COUNT(*) AS linhas, MAX(_ingerido_em) AS ingerido_em
        FROM {TABELA}
        GROUP BY _arquivo_origem
        ORDER BY _arquivo_origem
    """)
)