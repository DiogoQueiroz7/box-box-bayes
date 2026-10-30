import math
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import bayes

PASTA_VOLTAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "voltas")
VERMELHO, ASFALTO, BRANCO, CINZA = "#E10600", "#2A2A38", "#F5F5F7", "#8E8EA8"
CORES_DECISAO = {"DEFENDER": "#2BB673", "MANTER O PLANO": "#F2B33D", "ARRISCAR": "#FF5A4F"}
QUADROS_POR_VOLTA = 3
ESPACO_NO_GRID = 0.007


def carregar_voltas(corrida_id):
    return pd.read_csv(os.path.join(PASTA_VOLTAS, f"{corrida_id}.csv"))


def pct(p):
    return f"{p * 100:.1f}%".replace(".", ",")


def tempos_do_piloto(voltas, piloto):
    dele = voltas[voltas["piloto"] == piloto].sort_values("volta")
    return dele["volta"].to_numpy(), dele["tempo"].to_numpy(), dele["posicao"].iloc[0]


def preparar_pista(circuito):
    x, y = circuito["x"], circuito["y"]
    distancia = [0]
    for i in range(1, len(x)):
        trecho = math.hypot(x[i] - x[i - 1], y[i] - y[i - 1])
        distancia.append(distancia[-1] + trecho)
    return x, y, distancia


def ponto_na_pista(fracao, pista):
    x, y, distancia = pista
    metros = fracao * distancia[-1]
    return np.interp(metros, distancia, x), np.interp(metros, distancia, y)


def carros_no_instante(instante, pilotos, fim_da_corrida):
    carros = []
    for piloto, (voltas_feitas, tempos, grid) in pilotos.items():
        abandonou = tempos[-1] < fim_da_corrida
        if abandonou and instante > tempos[-1]:
            continue
        no_desenho = voltas_feitas.astype(float)
        no_desenho[0] = -ESPACO_NO_GRID * (grid - 1)
        carros.append((piloto, np.interp(instante, tempos, no_desenho)))
    return carros


def chance_na_volta(chance_por_volta, volta):
    anteriores = [v for v in chance_por_volta if v <= volta]
    return chance_por_volta[max(anteriores)] if anteriores else None


def camada_de_carros(carros, pista, cores, tamanho, borda, com_nome):
    codigos = [piloto for piloto, _ in carros]
    fracoes = np.array([voltas_andadas % 1 for _, voltas_andadas in carros])
    x, y = ponto_na_pista(fracoes, pista)
    return go.Scatter(
        x=x, y=y, mode="markers+text", hovertext=codigos, hoverinfo="text",
        text=[f"<b>{p}</b>" if p in com_nome else "" for p in codigos], textposition="middle right",
        textfont=dict(color=BRANCO, size=13),
        marker=dict(size=tamanho, color=[cores.get(p, CINZA) for p in codigos], line=dict(color=borda, width=2)))


def nota(texto, x, y, tamanho, cor=BRANCO, lado="left", ancora="top"):
    return dict(text=texto, x=x, y=y, xref="paper", yref="paper", xanchor=lado, yanchor=ancora, align=lado,
                showarrow=False, font=dict(size=tamanho, color=cor))


def anotacoes(volta, total, chance, top5, cores, destaque):
    notas = [nota("<b>Largada</b>" if volta == 0 else f"<b>Volta {volta}</b> / {total}", 0, 1, 22)]
    if chance is not None:
        escolha = bayes.decisao(chance)
        notas.append(nota(f"Chance de vitória do {destaque}:", 1, 1, 13, CINZA, lado="right"))
        notas.append(nota(f"<b>{pct(chance)}</b>", 1, 0.955, 38, lado="right"))
        notas.append(nota(f"<b>{escolha}</b>", 1, 0.86, 15, CORES_DECISAO[escolha], lado="right"))
    linhas = [f"{pos:.0f}º <span style='color:{cores.get(p, CINZA)}'>" + (f"<b>{p}</b>" if p == destaque else p)
              + "</span>" for p, pos in top5]
    titulo = "GRID DE LARGADA" if volta == 0 else "TOP 5"
    notas.append(nota(f"<span style='color:{CINZA}'>{titulo}</span><br>" + "<br>".join(linhas), 0, 0, 14,
                      ancora="bottom"))
    return notas


def figura_corrida(voltas, circuito, cores, destaque, chance_por_volta):
    pista = preparar_pista(circuito)
    x, y, _ = pista
    pilotos = {}
    for p in voltas["piloto"].unique():
        pilotos[p] = tempos_do_piloto(voltas, p)
    ultima_volta = voltas[voltas["volta"] == voltas["volta"].max()]
    vencedor = ultima_volta.sort_values("tempo")["piloto"].iloc[0]
    voltas_vencedor, tempos_vencedor, _ = pilotos[vencedor]
    total, fim = int(voltas_vencedor[-1]), tempos_vencedor[-1]
    posicoes = voltas.dropna(subset=["posicao"]).sort_values("posicao")

    quadros = []
    for k in range(total * QUADROS_POR_VOLTA + 1):
        progresso = k / QUADROS_POR_VOLTA
        instante = np.interp(progresso, voltas_vencedor, tempos_vencedor)
        carros = carros_no_instante(instante, pilotos, fim)
        volta = k // QUADROS_POR_VOLTA
        nesta_volta = posicoes[posicoes["volta"] == volta]
        top5 = list(zip(nesta_volta["piloto"], nesta_volta["posicao"]))[:5]
        lider = top5[0][0] if top5 else None
        outros = [c for c in carros if c[0] != destaque]
        dele = [c for c in carros if c[0] == destaque]
        quadros.append(go.Frame(
            name=str(k),
            traces=[3, 4],
            data=[camada_de_carros(outros, pista, cores, 13, "#15151E", [lider]),
                  camada_de_carros(dele, pista, cores, 20, BRANCO, [destaque])],
            layout=dict(annotations=anotacoes(volta, total, chance_na_volta(chance_por_volta, volta), top5, cores,
                                              destaque))))

    fig = go.Figure(frames=quadros, data=[
        go.Scatter(x=x, y=y, mode="lines", line=dict(color=ASFALTO, width=16), hoverinfo="skip"),
        go.Scatter(x=x, y=y, mode="lines", line=dict(color=BRANCO, width=4), hoverinfo="skip"),
        go.Scatter(x=x[:1], y=y[:1], mode="markers", hoverinfo="skip",
                   marker=dict(symbol="square", size=14, color=VERMELHO)),
        quadros[0].data[0], quadros[0].data[1]])

    tocar = dict(frame=dict(duration=70, redraw=True), transition=dict(duration=0), fromcurrent=True)
    parar = dict(frame=dict(duration=0, redraw=True), transition=dict(duration=0), mode="immediate")
    largura = max(x) - min(x)
    fig.update_layout(
        height=560, showlegend=False, annotations=quadros[0].layout.annotations,
        dragmode=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=10, b=60),
        xaxis=dict(visible=False, range=[min(x) - 0.32 * largura, max(x) + 0.32 * largura]),
        yaxis=dict(visible=False, scaleanchor="x"),
        updatemenus=[dict(type="buttons", direction="left", x=0, y=0, showactive=False,
                          bgcolor=BRANCO, font=dict(color="#15151E"), buttons=[
            dict(label="Iniciar", method="animate", args=[None, tocar]),
            dict(label="Pausar", method="animate", args=[[None], parar])])],
        sliders=[dict(x=0.17, len=0.83, y=0, currentvalue=dict(visible=False), font=dict(color=CINZA), steps=[
            dict(method="animate", args=[[str(v * QUADROS_POR_VOLTA)], parar],
                 label=str(v) if v % 10 == 0 else "")
            for v in range(total + 1)])])
    return fig
