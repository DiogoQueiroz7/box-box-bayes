import os
import glob
import json
import logging

import numpy as np
import pandas as pd
import requests
import fastf1

TEMPORADAS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
PNEUS_DE_CHUVA = ["INTERMEDIATE", "WET"]
MARCOS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
COLUNAS = ["corrida_id", "ano", "rodada", "gp", "circuito", "data", "piloto", "nome", "equipe",
           "grid", "posicao_final", "venceu", "choveu", "voltas_com_chuva", "total_voltas",
           "volta_meio", "posicao_meio"]


def baixar_corrida(ano, rodada):
    sessao = fastf1.get_session(ano, rodada, "R")
    sessao.load(laps=True, telemetry=False, weather=False, messages=False)

    ev, res = sessao.event, sessao.results
    pilotos = pd.DataFrame({
        "corrida_id": f"{ano}-{rodada:02d}",
        "ano": ano,
        "rodada": rodada,
        "gp": ev["EventName"],
        "circuito": ev["Location"],
        "data": str(ev["EventDate"].date()),
        "piloto": res["Abbreviation"].values,
        "nome": res["FullName"].values,
        "equipe": res["TeamName"].values,
        "grid": res["GridPosition"].values,
        "posicao_final": res["Position"].values,
    })
    if pilotos["grid"].isna().all():
        pilotos["grid"] = pilotos["piloto"].map(grid_da_jolpica(ano, rodada))

    voltas = sessao.laps[["Driver", "LapNumber", "Position", "Compound"]]
    voltas.columns = ["piloto", "volta", "posicao", "pneu"]
    resumo = resumir(pilotos, voltas)
    return resumo, volta_a_volta(sessao.laps, resumo)


def grid_da_jolpica(ano, rodada):
    url = f"https://api.jolpi.ca/ergast/f1/{ano}/{rodada}/results.json"
    resultados = requests.get(url, timeout=30).json()["MRData"]["RaceTable"]["Races"][0]["Results"]
    grid = {}
    for r in resultados:
        grid[r["Driver"]["code"]] = int(r["grid"])
    return grid


def voltas_de_chuva(voltas):
    lista = []
    for numero, volta in voltas.groupby("volta"):
        molhados = volta["pneu"].isin(PNEUS_DE_CHUVA).sum()
        if molhados >= len(volta) / 2:
            lista.append(numero)
    return lista


def resumir(pilotos, voltas):
    voltas = voltas.dropna(subset=["volta"])

    pilotos = pilotos[pilotos["piloto"].isin(voltas["piloto"])].copy()
    pilotos["grid"] = pilotos["grid"].fillna(20)
    pilotos.loc[pilotos["grid"] < 1, "grid"] = 20
    pilotos["grid"] = pilotos["grid"].astype(int)
    pilotos["posicao_final"] = pilotos["posicao_final"].astype(int)
    pilotos["venceu"] = (pilotos["posicao_final"] == 1).astype(int)

    vencedor = pilotos[pilotos["venceu"] == 1]["piloto"].iloc[0]
    total = int(voltas[voltas["piloto"] == vencedor]["volta"].max())

    voltas_com_chuva = len(voltas_de_chuva(voltas))
    pilotos["voltas_com_chuva"] = voltas_com_chuva
    pilotos["choveu"] = int(voltas_com_chuva >= 0.10 * total)

    volta_meio = (total + 1) // 2
    na_metade = voltas[voltas["volta"] == volta_meio].set_index("piloto")["posicao"]
    pilotos["total_voltas"] = total
    pilotos["volta_meio"] = volta_meio
    pilotos["posicao_meio"] = pilotos["piloto"].map(na_metade).astype("Int64")
    return pilotos[COLUNAS]


def volta_a_volta(laps, resumo):
    inicio = laps[laps["LapNumber"] == 1]["LapStartTime"].min()
    tabela = pd.DataFrame({
        "piloto": laps["Driver"],
        "volta": laps["LapNumber"],
        "tempo": (laps["Time"] - inicio).dt.total_seconds().round(3),
        "posicao": laps["Position"],
        "pneu": laps["Compound"],
    }).dropna(subset=["volta", "tempo"])

    largada = tabela[tabela["volta"] == 1].copy()
    largada["volta"] = 0
    largada["tempo"] = 0.0
    largada["posicao"] = largada["piloto"].map(resumo.set_index("piloto")["grid"]).fillna(len(largada))
    tabela = pd.concat([largada, tabela])

    tabela["chuva"] = tabela["volta"].isin(voltas_de_chuva(tabela)).astype(int)
    tabela["volta"] = tabela["volta"].astype(int)
    tabela["posicao"] = tabela["posicao"].astype("Int64")
    return tabela.drop(columns="pneu").sort_values(["piloto", "volta"])


def coletar(anos):
    os.makedirs("data/corridas", exist_ok=True)
    os.makedirs("data/voltas", exist_ok=True)
    for ano in anos:
        calendario = fastf1.get_event_schedule(ano, include_testing=False)
        ja_aconteceu = calendario[calendario["EventDate"] < pd.Timestamp.now()]
        for rodada in ja_aconteceu["RoundNumber"]:
            corrida_id = f"{ano}-{rodada:02d}"
            arquivo = f"data/corridas/{corrida_id}.csv"
            if os.path.exists(arquivo):
                continue
            try:
                resumo, voltas = baixar_corrida(ano, int(rodada))
                resumo.to_csv(arquivo, index=False)
                voltas.to_csv(f"data/voltas/{corrida_id}.csv", index=False)
                print(corrida_id, resumo["gp"].iloc[0], "ok")
            except Exception as erro:
                print(corrida_id, "FALHOU:", erro)


def juntar():
    arquivos = sorted(glob.glob("data/corridas/*.csv"))
    largadas = pd.concat([pd.read_csv(a) for a in arquivos], ignore_index=True)
    largadas.to_csv("data/largadas.csv", index=False)
    print("data/largadas.csv:", largadas["corrida_id"].nunique(), "corridas,", len(largadas), "largadas")


def gerar_marcos():
    largadas = pd.read_csv("data/largadas.csv")
    linhas = []
    for corrida_id, corrida in largadas.groupby("corrida_id"):
        voltas = pd.read_csv(f"data/voltas/{corrida_id}.csv").dropna(subset=["posicao"])
        total = int(corrida["total_voltas"].iloc[0])
        for _, p in corrida.iterrows():
            dele = voltas[voltas["piloto"] == p["piloto"]].set_index("volta")["posicao"]
            for marco in MARCOS:
                volta = round(marco / 100 * total)
                posicao = None
                if len(dele) > 0 and volta <= dele.index.max():
                    posicao = dele[dele.index <= volta].iloc[-1]
                linhas.append({"corrida_id": corrida_id, "ano": p["ano"], "piloto": p["piloto"],
                               "venceu": p["venceu"], "marco": marco, "volta": volta, "posicao": posicao})
    marcos = pd.DataFrame(linhas)
    marcos["posicao"] = marcos["posicao"].astype("Int64")
    marcos.to_csv("data/marcos.csv", index=False)
    print("data/marcos.csv:", len(marcos), "linhas")


URL_CIRCUITOS = "https://raw.githubusercontent.com/bacinger/f1-circuits/master/f1-circuits.geojson"

ID_DO_CIRCUITO = {
    "Austin": "us-2012", "Baku": "az-2016", "Barcelona": "es-1991", "Budapest": "hu-1986",
    "Hockenheim": "de-1932", "Imola": "it-1953", "Istanbul": "tr-2005", "Jeddah": "sa-2021",
    "Las Vegas": "us-2023", "Le Castellet": "fr-1969", "Lusail": "qa-2004", "Marina Bay": "sg-2008",
    "Singapore": "sg-2008", "Melbourne": "au-1953", "Mexico City": "mx-1962", "Miami": "us-2022",
    "Miami Gardens": "us-2022", "Monaco": "mc-1929", "Monte Carlo": "mc-1929", "Montréal": "ca-1978",
    "Monza": "it-1922", "Mugello": "it-1914", "Nürburgring": "de-1927", "Portimão": "pt-2008",
    "Sakhir": "bh-2002", "Shanghai": "cn-2004", "Silverstone": "gb-1948", "Sochi": "ru-2014",
    "Spa-Francorchamps": "be-1925", "Spielberg": "at-1969", "Suzuka": "jp-1962", "São Paulo": "br-1940",
    "Yas Island": "ae-2009", "Yas Marina": "ae-2009", "Zandvoort": "nl-1948",
}


def coletar_circuitos():
    geojson = requests.get(URL_CIRCUITOS, timeout=60).json()
    tracados = {}
    for f in geojson["features"]:
        tracados[f["properties"]["id"]] = f
    circuitos = {}
    for local, id_circuito in ID_DO_CIRCUITO.items():
        tracado = tracados[id_circuito]
        pontos = tracado["geometry"]["coordinates"]
        lon = np.array([p[0] for p in pontos])
        lat = np.array([p[1] for p in pontos])
        x = (lon - lon.mean()) * 111320 * np.cos(np.radians(lat.mean()))
        y = (lat - lat.mean()) * 110540
        circuitos[local] = {"nome": tracado["properties"]["Name"], "x": x.round(1).tolist(), "y": y.round(1).tolist()}
    with open("data/circuitos.json", "w", encoding="utf-8") as arquivo:
        json.dump(circuitos, arquivo, ensure_ascii=False)
    print("data/circuitos.json:", len(circuitos), "circuitos")


if __name__ == "__main__":
    os.makedirs("cache", exist_ok=True)
    fastf1.Cache.enable_cache("cache")
    logging.getLogger("fastf1").setLevel(logging.ERROR)
    coletar(TEMPORADAS)
    juntar()
    gerar_marcos()
    coletar_circuitos()
