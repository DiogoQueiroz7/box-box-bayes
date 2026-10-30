import os

import pandas as pd

ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "marcos.csv")

MARCOS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
SITUACOES = ["1º", "2º", "3º", "4º", "5º", "6º", "7º", "8º", "9º", "10º", "11º ou pior", "Abandonou"]


def situacao(posicao):
    if pd.isna(posicao):
        return "Abandonou"
    if posicao <= 10:
        return f"{int(posicao)}º"
    return "11º ou pior"


def carregar(arquivo=ARQUIVO):
    marcos = pd.read_csv(arquivo)
    marcos["situacao"] = marcos["posicao"].apply(situacao)
    return marcos


def teorema_de_bayes(anterior, p_se_vence, p_se_nao_vence):
    numerador = p_se_vence * anterior
    denominador = numerador + p_se_nao_vence * (1 - anterior)
    return numerador / denominador


def proporcao(casos, total):
    return (casos + 1) / (total + 2)


def taxa_base(marcos):
    largada = marcos[marcos["marco"] == 0]
    return largada["venceu"].sum() / len(largada)


def evidencia(marcos, marco, situacao_agora):
    agora = marcos[marcos["marco"] == marco]
    vencedores = agora[agora["venceu"] == 1]
    nao_vencedores = agora[agora["venceu"] == 0]
    casos_v = int((vencedores["situacao"] == situacao_agora).sum())
    casos_n = int((nao_vencedores["situacao"] == situacao_agora).sum())
    p_se_vence = proporcao(casos_v, len(vencedores))
    if situacao_agora == "Abandonou":
        p_se_vence = 0.0
    return {"p_se_vence": p_se_vence, "p_se_nao_vence": proporcao(casos_n, len(nao_vencedores)),
            "casos_vencedores": casos_v, "total_vencedores": len(vencedores),
            "casos_nao_vencedores": casos_n, "total_nao_vencedores": len(nao_vencedores)}


def chance(marcos, marco, situacao_agora, anterior=None):
    if anterior is None:
        anterior = taxa_base(marcos)
    e = evidencia(marcos, marco, situacao_agora)
    return teorema_de_bayes(anterior, e["p_se_vence"], e["p_se_nao_vence"])


def tabela_de_chances(marcos, anterior=None):
    tabela = {}
    for marco in MARCOS:
        for s in SITUACOES:
            tabela[(marco, s)] = chance(marcos, marco, s, anterior)
    return tabela


def marco_da_volta(volta, total):
    return min(round(volta / total * 10), 9) * 10


def chances_do_piloto(voltas, piloto, total, tabela):
    dele = voltas[voltas["piloto"] == piloto].dropna(subset=["posicao"])
    chances = {}
    for volta, posicao in zip(dele["volta"], dele["posicao"]):
        chances[int(volta)] = tabela[(marco_da_volta(volta, total), situacao(posicao))]
    ultima = int(dele["volta"].max())
    if ultima < total:
        chances[ultima + 1] = 0.0
    return chances


def decisao(chance_agora):
    if chance_agora >= 0.5:
        return "DEFENDER"
    if chance_agora >= 0.10:
        return "MANTER O PLANO"
    return "ARRISCAR"


def avaliar(marcos, anos_treino, anos_teste, marco=50):
    tabela = tabela_de_chances(marcos[marcos["ano"].isin(anos_treino)])
    teste = marcos[marcos["ano"].isin(anos_teste) & (marcos["marco"] == marco)]
    resultado = {}
    for nome in ["ARRISCAR", "MANTER O PLANO", "DEFENDER"]:
        resultado[nome] = {"pilotos": 0, "venceram": 0}
    for _, linha in teste.iterrows():
        nome = decisao(tabela[(marco, linha["situacao"])])
        resultado[nome]["pilotos"] += 1
        resultado[nome]["venceram"] += int(linha["venceu"])
    return resultado, teste["corrida_id"].nunique()
