# Databricks notebook source
# DBTITLE 1,P1 aeroportos com mais atraso
# MAGIC %sql
# MAGIC -- P1 — Quais rotas e aeroportos concentram os maiores atrasos de partida no Brasil?
# MAGIC -- Recorte: aeroportos de origem no Brasil, com volume relevante (>= 5.000 voos).
# MAGIC -- abaixo disso o atraso medio oscila demais e nao diz nada
# MAGIC SELECT
# MAGIC   nome_aeroporto_origem,
# MAGIC   municipio_origem,
# MAGIC   uf_origem,
# MAGIC   COUNT(*)                                                                   AS voos,
# MAGIC   ROUND(AVG(atraso_partida_min), 2)                                          AS atraso_medio_min,
# MAGIC   -- pct sobre quem tem metrica: voo cancelado sai do denominador
# MAGIC ROUND(100.0 * try_divide(SUM(CASE WHEN partida_pontual = false THEN 1 ELSE 0 END),
# MAGIC                            SUM(CASE WHEN partida_pontual IS NOT NULL THEN 1 ELSE 0 END)), 2) AS pct_atrasados
# MAGIC FROM voebem.gold.obt_voos
# MAGIC WHERE pais_origem = 'Brasil'
# MAGIC GROUP BY 1, 2, 3
# MAGIC HAVING COUNT(*) >= 5000
# MAGIC ORDER BY pct_atrasados DESC
# MAGIC LIMIT 10

# COMMAND ----------

# DBTITLE 1,P1b piores rotas
# MAGIC %sql
# MAGIC -- P1b — as piores ROTAS domesticas por atraso de partida (>= 2.000 voos).
# MAGIC -- ordenado pelo atraso medio: aqui interessa o tamanho do problema, nao a frequencia
# MAGIC SELECT
# MAGIC   rota_municipios,
# MAGIC   rota_icao,
# MAGIC   COUNT(*)                                                                   AS voos,
# MAGIC   ROUND(AVG(atraso_partida_min), 2)                                          AS atraso_medio_min,
# MAGIC   ROUND(100.0 * try_divide(SUM(CASE WHEN partida_pontual = false THEN 1 ELSE 0 END),
# MAGIC                            SUM(CASE WHEN partida_pontual IS NOT NULL THEN 1 ELSE 0 END)), 2) AS pct_atrasados
# MAGIC FROM voebem.gold.obt_voos
# MAGIC -- so domestico pra manter a rota com dois municipios brasileiros no nome
# MAGIC WHERE escopo_voo = 'Domestico'
# MAGIC GROUP BY 1, 2
# MAGIC HAVING COUNT(*) >= 2000
# MAGIC ORDER BY atraso_medio_min DESC
# MAGIC LIMIT 10

# COMMAND ----------

# DBTITLE 1,P2 atraso por hora do dia
# MAGIC %sql
# MAGIC -- P2 — Como o atraso evolui ao longo do dia (efeito cascata).
# MAGIC -- a expectativa e ver o atraso medio subir conforme o dia avanca: atraso de manha
# MAGIC -- contagia o resto da operacao da aeronave
# MAGIC SELECT
# MAGIC   hora_partida_prevista                                                      AS hora,
# MAGIC   COUNT(*)                                                                   AS voos,
# MAGIC   ROUND(AVG(atraso_partida_min), 2)                                          AS atraso_medio_min,
# MAGIC   ROUND(100.0 * try_divide(SUM(CASE WHEN partida_pontual = false THEN 1 ELSE 0 END),
# MAGIC                            SUM(CASE WHEN partida_pontual IS NOT NULL THEN 1 ELSE 0 END)), 2) AS pct_atrasados
# MAGIC FROM voebem.gold.obt_voos
# MAGIC -- voos sem horario previsto (a companhia nao informou) nao tem hora do dia
# MAGIC WHERE hora_partida_prevista IS NOT NULL
# MAGIC GROUP BY 1
# MAGIC ORDER BY 1

# COMMAND ----------

# DBTITLE 1,P3 pontualidade por companhia
# MAGIC %sql
# MAGIC -- P3 — Companhia: pontualidade x cancelamento, controlando por porte (>= 10.000 voos).
# MAGIC -- cancelamento entra de proposito: uma companhia pode melhorar a pontualidade
# MAGIC -- simplesmente cancelando em vez de atrasar
# MAGIC SELECT
# MAGIC   nome_companhia,
# MAGIC   COUNT(*)                                                                   AS voos,
# MAGIC   -- cancelado e sobre o total de etapas: toda linha tem situacao, nao precisa try_divide
# MAGIC   ROUND(100.0 * SUM(CASE WHEN voo_cancelado THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_cancelados,
# MAGIC   ROUND(100.0 * try_divide(SUM(CASE WHEN partida_pontual = true THEN 1 ELSE 0 END),
# MAGIC                            SUM(CASE WHEN partida_pontual IS NOT NULL THEN 1 ELSE 0 END)), 2) AS pct_pontuais,
# MAGIC   ROUND(AVG(atraso_partida_min), 2)                                          AS atraso_medio_min
# MAGIC FROM voebem.gold.obt_voos
# MAGIC GROUP BY 1
# MAGIC HAVING COUNT(*) >= 10000
# MAGIC ORDER BY pct_pontuais DESC

# COMMAND ----------

# DBTITLE 1,P4 domestico x internacional
# MAGIC %sql
# MAGIC -- P4 — Voos internacionais atrasam mais que domesticos? Quanto?
# MAGIC -- comparacao direta pelo escopo_voo, classificacao de negocio criada na gold
# MAGIC SELECT
# MAGIC   escopo_voo,
# MAGIC   COUNT(*)                                                                   AS voos,
# MAGIC   ROUND(AVG(atraso_partida_min), 2)                                          AS atraso_medio_min,
# MAGIC   ROUND(100.0 * try_divide(SUM(CASE WHEN partida_pontual = false THEN 1 ELSE 0 END),
# MAGIC                            SUM(CASE WHEN partida_pontual IS NOT NULL THEN 1 ELSE 0 END)), 2) AS pct_atrasados
# MAGIC FROM voebem.gold.obt_voos
# MAGIC GROUP BY 1
# MAGIC ORDER BY voos DESC

# COMMAND ----------

# DBTITLE 1,P4b diferenca por aeroporto
# MAGIC %sql
# MAGIC -- P4b — E em quais aeroportos brasileiros a diferenca internacional x domestico e maior?
# MAGIC -- so entra aeroporto com os dois escopos acima de 2.000 voos: sem isso, a diferenca
# MAGIC -- pode vir de amostra pequena de um dos lados
# MAGIC SELECT
# MAGIC   nome_aeroporto_origem,
# MAGIC   municipio_origem,
# MAGIC   SUM(CASE WHEN escopo_voo = 'Domestico'     THEN 1 ELSE 0 END)              AS voos_domesticos,
# MAGIC   SUM(CASE WHEN escopo_voo = 'Internacional' THEN 1 ELSE 0 END)              AS voos_internacionais,
# MAGIC   ROUND(AVG(CASE WHEN escopo_voo = 'Domestico'     THEN atraso_partida_min END), 2) AS atraso_domestico,
# MAGIC   ROUND(AVG(CASE WHEN escopo_voo = 'Internacional' THEN atraso_partida_min END), 2) AS atraso_internacional,
# MAGIC   ROUND(AVG(CASE WHEN escopo_voo = 'Internacional' THEN atraso_partida_min END)
# MAGIC       - AVG(CASE WHEN escopo_voo = 'Domestico'     THEN atraso_partida_min END), 2) AS diferenca_min
# MAGIC FROM voebem.gold.obt_voos
# MAGIC WHERE pais_origem = 'Brasil'
# MAGIC GROUP BY 1, 2
# MAGIC HAVING SUM(CASE WHEN escopo_voo = 'Internacional' THEN 1 ELSE 0 END) >= 2000
# MAGIC    AND SUM(CASE WHEN escopo_voo = 'Domestico'     THEN 1 ELSE 0 END) >= 2000
# MAGIC ORDER BY diferenca_min DESC
# MAGIC LIMIT 10

# COMMAND ----------

# DBTITLE 1,P5 recuperacao em voo
# MAGIC %sql
# MAGIC -- P5 — Quanto atraso as companhias recuperam em voo? (>= 10.000 voos)
# MAGIC -- minutos_recuperados: quanto do atraso de saida sumiu ate a chegada
# MAGIC SELECT
# MAGIC   nome_companhia,
# MAGIC   COUNT(*)                                                                   AS voos,
# MAGIC   ROUND(AVG(atraso_partida_min), 2)                                          AS atraso_saida_min,
# MAGIC   ROUND(AVG(atraso_chegada_min), 2)                                          AS atraso_chegada_min,
# MAGIC   ROUND(AVG(minutos_recuperados), 2)                                         AS recuperados_medio_min
# MAGIC FROM voebem.gold.obt_voos
# MAGIC -- sem a metrica (cancelado, fora de faixa) nao ha recuperacao pra medir
# MAGIC WHERE minutos_recuperados IS NOT NULL
# MAGIC GROUP BY 1
# MAGIC HAVING COUNT(*) >= 10000
# MAGIC ORDER BY recuperados_medio_min DESC

# COMMAND ----------

# DBTITLE 1,P5b rotas sem recuperacao
# MAGIC %sql
# MAGIC -- P5b — Em que rotas a recuperacao NAO acontece (perde tempo no ar)? (>= 2.000 voos)
# MAGIC -- rota curta tem pouco espaco pra devolver atraso; ordenado pelo pior saldo
# MAGIC SELECT
# MAGIC   rota_municipios,
# MAGIC   rota_icao,
# MAGIC   COUNT(*)                                                                   AS voos,
# MAGIC   ROUND(AVG(atraso_partida_min), 2)                                          AS atraso_saida_min,
# MAGIC   ROUND(AVG(atraso_chegada_min), 2)                                          AS atraso_chegada_min,
# MAGIC   ROUND(AVG(minutos_recuperados), 2)                                         AS recuperados_medio_min
# MAGIC FROM voebem.gold.obt_voos
# MAGIC WHERE minutos_recuperados IS NOT NULL
# MAGIC GROUP BY 1, 2
# MAGIC HAVING COUNT(*) >= 2000
# MAGIC ORDER BY recuperados_medio_min ASC
# MAGIC LIMIT 10