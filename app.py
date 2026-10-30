import inspect
import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import bayes
import corrida

st.set_page_config(page_title="Box Box Bayes", layout="wide")

VERMELHO, DOURADO, CINZA = "#E10600", "#EDA100", "#4A4A5E"
REGRA = "Regra: abaixo de 10% arriscar, de 10% a 50% manter o plano, a partir de 50% defender"
CORES_EQUIPES = {
    "red bull": "#3671C6", "ferrari": "#E8002D", "mercedes": "#27F4D2", "mclaren": "#FF8000",
    "alpine": "#FF87BC", "renault": "#FFF500", "aston martin": "#229971", "racing point": "#F596C8",
    "force india": "#F596C8", "williams": "#64C4FF", "alphatauri": "#5E8FAA", "toro rosso": "#469BFF",
    "racing bulls": "#6692FF", "rb f1": "#6692FF", "alfa romeo": "#C92D4B", "sauber": "#52E252", "haas": "#B6BABD",
}


def pct(p, casas=1):
    return f"{p * 100:.{casas}f}%".replace(".", ",")


def num(x):
    return f"{x:.4f}".replace(".", ",")


def milhar(n):
    return f"{n:,}".replace(",", ".")


def cor_da_equipe(equipe):
    for nome, cor in CORES_EQUIPES.items():
        if nome in str(equipe).lower():
            return cor
    return "#8E8EA8"


def nome_do_momento(marco):
    return "na largada" if marco == 0 else f"com {marco}% da corrida"


def caixa_de_decisao(chance):
    escolha = bayes.decisao(chance)
    if escolha == "DEFENDER":
        st.success(f"**DEFENDER** ({pct(chance)}): é o favorito, proteger a posição.")
    elif escolha == "MANTER O PLANO":
        st.warning(f"**MANTER O PLANO** ({pct(chance)}): tem chance real, seguir a estratégia.")
    else:
        st.error(f"**ARRISCAR** ({pct(chance)}): pouca chance, tentar algo diferente.")


def comparacao(e):
    if e["p_se_vence"] == 0:
        return "Quem abandona não vence: a chance vai a zero."
    vezes = e["p_se_vence"] / e["p_se_nao_vence"]
    if vezes >= 1:
        return f"Estar assim é {vezes:.1f} vezes mais comum entre quem vence: a chance sobe.".replace(".", ",", 1)
    return f"Estar assim é {1 / vezes:.1f} vezes mais raro entre quem vence: a chance cai.".replace(".", ",", 1)


def grade(dourados, cinzas):
    cores = [DOURADO] * dourados + [CINZA] * cinzas
    x = [i % 50 for i in range(len(cores))]
    y = [-(i // 50) for i in range(len(cores))]
    fig = go.Figure(go.Scatter(x=x, y=y, mode="markers", marker=dict(size=9, color=cores)))
    fig.update_layout(height=270, margin=dict(l=0, r=0, t=0, b=0),
                      xaxis=dict(visible=False, range=[-1, 50]), yaxis=dict(visible=False, range=[-20, 1]))
    return fig


def faixas_de_decisao(fig):
    fig.add_hrect(y0=0, y1=10, fillcolor=corrida.CORES_DECISAO["ARRISCAR"], opacity=0.10, line_width=0,
                  annotation_text="arriscar", annotation_position="top left")
    fig.add_hrect(y0=10, y1=50, fillcolor=corrida.CORES_DECISAO["MANTER O PLANO"], opacity=0.10, line_width=0,
                  annotation_text="manter o plano", annotation_position="top left")
    fig.add_hrect(y0=50, y1=100, fillcolor=corrida.CORES_DECISAO["DEFENDER"], opacity=0.10, line_width=0,
                  annotation_text="defender", annotation_position="top left")


@st.cache_data
def carregar_dados():
    marcos = bayes.carregar()
    largadas = pd.read_csv("data/largadas.csv")
    with open("data/circuitos.json", encoding="utf-8") as arquivo:
        circuitos = json.load(arquivo)
    return marcos, largadas, circuitos


@st.cache_data
def tabela(anterior):
    return bayes.tabela_de_chances(marcos, anterior)


@st.cache_data(show_spinner="Preparando a corrida...")
def animacao(corrida_id, piloto, chances):
    resultado = largadas[largadas["corrida_id"] == corrida_id]
    circuito = circuitos[resultado["circuito"].iloc[0]]
    cores = {}
    for p, equipe in zip(resultado["piloto"], resultado["equipe"]):
        cores[p] = cor_da_equipe(equipe)
    return corrida.figura_corrida(corrida.carregar_voltas(corrida_id), circuito, cores, piloto, chances)


@st.cache_data
def avaliacao():
    return bayes.avaliar(marcos, [2018, 2019, 2020, 2021, 2022], [2024, 2025])


if not os.path.exists(bayes.ARQUIVO):
    st.error("Dados não encontrados. Rode antes: python coletar_dados.py")
    st.stop()
marcos, largadas, circuitos = carregar_dados()
taxa = bayes.taxa_base(marcos)
tabela_real = tabela(taxa)

st.title("Box Box Bayes")
st.caption("Qual é a chance de vitória deste piloto agora? O Teorema de Bayes responde a cada volta, com dados reais "
           "da Fórmula 1. Estatística aplicada a ADS, Grupo 1: Diogo e João Vitor")

aba_corrida, aba_bayes, aba_dados = st.tabs(["1 - Corrida ao vivo", "2 - Como o Bayes calcula", "3 - Dados e validação"])

with aba_corrida:
    st.markdown("#### 1 - Entrada: escolha a corrida e o piloto")
    corridas = largadas.groupby("corrida_id").first().sort_values(["ano", "rodada"])
    c1, c2, c3 = st.columns([1, 2, 2])
    anos = sorted(corridas["ano"].unique())
    ano = c1.selectbox("Temporada", anos, index=anos.index(2024))
    ids = list(corridas[corridas["ano"] == ano].index)
    cid = c2.selectbox("Grande Prêmio", ids, index=ids.index("2024-21") if "2024-21" in ids else 0,
                       format_func=lambda i: corridas.loc[i, "gp"])
    resultado = largadas[largadas["corrida_id"] == cid].sort_values("posicao_final").set_index("piloto")
    piloto = c3.selectbox("Piloto", list(resultado.index),
                          format_func=lambda p: f"{resultado.loc[p, 'nome']} (largou em {resultado.loc[p, 'grid']}º)")
    info = corridas.loc[cid]
    linha = resultado.loc[piloto]
    total = int(info["total_voltas"])
    voltas = corrida.carregar_voltas(cid)
    chances = bayes.chances_do_piloto(voltas, piloto, total, tabela_real)

    st.markdown("#### 2 - A corrida: a chance muda a cada volta")
    col_pista, col_piloto = st.columns([5, 2])
    with col_pista:
        st.plotly_chart(animacao(cid, piloto, chances), config={"displayModeBar": False}, key=f"animacao_{cid}_{piloto}")
        st.caption("Aperte Iniciar. A cada volta o sistema olha a posição do piloto e recalcula a chance com o "
                   "Teorema de Bayes.")
    with col_piloto:
        with st.container(border=True):
            st.markdown(f"### {linha['nome']}")
            st.caption(f"{linha['equipe']}, {info['gp']} {info['ano']}")
            a, b = st.columns(2)
            a.metric("Largou", f"{linha['grid']}º")
            b.metric("Terminou", f"{linha['posicao_final']}º")
            maior = max(chances, key=chances.get)
            a.metric("Chance na largada", pct(chances[0]))
            b.metric("Maior chance", pct(chances[maior]))
            b.caption(f"na volta {maior}")
        st.caption(REGRA)

    st.markdown("#### 3 - Resultado: a chance volta a volta")
    outros = [p for p in resultado.index if p != piloto]
    comparar = st.multiselect("Comparar com", outros, default=outros[:1],
                              format_func=lambda p: resultado.loc[p, "nome"])
    fig = go.Figure()
    faixas_de_decisao(fig)
    for p in comparar:
        dele = bayes.chances_do_piloto(voltas, p, total, tabela_real)
        fig.add_trace(go.Scatter(x=list(dele), y=[c * 100 for c in dele.values()], name=p, line_shape="hv",
                                 line=dict(color=cor_da_equipe(resultado.loc[p, "equipe"]), width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=list(chances), y=[c * 100 for c in chances.values()], name=piloto, line_shape="hv",
                             line=dict(color=VERMELHO, width=4)))
    posicoes = voltas[voltas["piloto"] == piloto].dropna(subset=["posicao"]).set_index("volta")["posicao"]
    voltas_do_piloto = sorted(chances)
    saltos = []
    for antes, depois in zip(voltas_do_piloto, voltas_do_piloto[1:]):
        saltos.append((abs(chances[depois] - chances[antes]), depois))
    for diferenca, volta in sorted(saltos, reverse=True)[:2]:
        if diferenca >= 0.10:
            texto = f"volta {volta}: abandonou"
            if volta in posicoes.index and volta - 1 in posicoes.index and posicoes[volta] == posicoes[volta - 1]:
                texto = f"volta {volta}: segue em {int(posicoes[volta])}º, mais perto do fim"
            elif volta in posicoes.index:
                texto = f"volta {volta}: foi para {int(posicoes[volta])}º"
            fig.add_annotation(x=volta, y=chances[volta] * 100, text=texto, ax=-70, ay=-35, arrowcolor="#8E8EA8")
    fig.update_layout(height=400, margin=dict(t=30), xaxis_title="volta", yaxis_title="chance de vitória (%)",
                      yaxis_range=[0, 100], legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig, config={"displayModeBar": False})

    st.markdown("#### 4 - Interpretação e decisão: escolha uma volta")
    volta = st.slider("Volta", 0, total, value=total // 2, key=f"volta_{cid}_{piloto}")
    marco = bayes.marco_da_volta(volta, total)
    agora = "Abandonou"
    if volta <= posicoes.index.max():
        agora = bayes.situacao(posicoes[posicoes.index <= volta].iloc[-1])
    e = bayes.evidencia(marcos, marco, agora)
    depois = bayes.teorema_de_bayes(taxa, e["p_se_vence"], e["p_se_nao_vence"])
    k1, k2, k3 = st.columns(3, border=True)
    k1.metric("Chance antes (taxa-base)", pct(taxa))
    k1.caption(f"{int(largadas['venceu'].sum())} vencedores em {milhar(len(largadas))} largadas: "
               "1 em cada 20 pilotos.")
    k2.metric(f"Evidência na volta {volta}", agora)
    k2.caption(f"Posição {nome_do_momento(marco)}. Dos {e['total_vencedores']} vencedores, {e['casos_vencedores']} "
               f"estavam assim; dos {milhar(e['total_nao_vencedores'])} que não venceram, {e['casos_nao_vencedores']}.")
    k3.metric("Chance depois", pct(depois))
    k3.caption(comparacao(e))
    caixa_de_decisao(depois)
    st.caption("A conta completa, com a fórmula, está na aba 2.")

with aba_bayes:
    st.markdown("#### Monte uma situação")
    s1, s2, s3 = st.columns(3)
    escolhida = s1.selectbox("Posição do piloto", bayes.SITUACOES, index=1)
    marco_escolhido = s2.select_slider("Momento da corrida", bayes.MARCOS, value=50, format_func=nome_do_momento)
    anterior = s3.number_input("Chance antes (%)", min_value=0.1, max_value=99.0, value=taxa * 100, step=1.0,
                               format="%.1f") / 100
    s3.caption(f"A taxa-base real é {pct(taxa)}.")
    e = bayes.evidencia(marcos, marco_escolhido, escolhida)
    pv, pn = e["p_se_vence"], e["p_se_nao_vence"]
    depois = bayes.teorema_de_bayes(anterior, pv, pn)

    st.markdown("#### Contando: imagine 1.000 pilotos")
    g1, g2 = st.columns([3, 2])
    aplicar = g2.toggle(f"Ficar só com quem estava em {escolhida} {nome_do_momento(marco_escolhido)}")
    venc = round(1000 * anterior)
    venc_e = round(venc * pv)
    outros_e = round((1000 - venc) * pn)
    if aplicar:
        g1.plotly_chart(grade(venc_e, outros_e), config={"staticPlot": True})
        g2.metric("Chance depois", pct(venc_e / max(venc_e + outros_e, 1)))
        g2.write(f"Sobram só **{venc_e + outros_e}** pilotos. Deles, **{venc_e}** venceram: "
                 f"{venc_e} / {venc_e + outros_e}.")
    else:
        g1.plotly_chart(grade(venc, 1000 - venc), config={"staticPlot": True})
        g2.metric("Chance antes", pct(venc / 1000))
        g2.write(f"De 1.000 pilotos, **{venc}** vencem. Ligue a evidência acima.")
    st.caption("Dourado = venceu, cinza = não venceu. Números arredondados para 1.000 pilotos.")

    st.markdown("#### A fórmula faz a mesma conta")
    st.latex(r"P(V \mid E) = \frac{P(E \mid V)\times P(V)}{P(E \mid V)\times P(V) + P(E \mid \text{não }V)\times P(\text{não }V)}")
    f1, f2, f3, f4 = st.columns(4, border=True)
    f1.metric("P(V)", pct(anterior))
    f1.caption("chance antes")
    f2.metric("P(E | V)", pct(pv))
    f2.caption(f"{e['casos_vencedores']} dos {e['total_vencedores']} vencedores estavam em {escolhida}")
    f3.metric("P(E | não V)", pct(pn))
    f3.caption(f"{e['casos_nao_vencedores']} dos {milhar(e['total_nao_vencedores'])} que não venceram")
    f4.metric("P(V | E)", pct(depois))
    f4.caption("chance depois")
    st.write(f"P(V | E) = ({num(pv)} x {num(anterior)}) / ({num(pv)} x {num(anterior)} + {num(pn)} x "
             f"{num(1 - anterior)}) = **{pct(depois)}**")
    st.caption('V = vencer, E = a evidência (a posição naquele momento) e "|" quer dizer "dado que". As proporções '
               'usam (casos + 1) / (total + 2), para nunca dar 0% só por falta de exemplos.')

    st.markdown("#### E se a chance antes fosse outra?")
    st.caption(f"Mesma evidência ({escolhida} {nome_do_momento(marco_escolhido)}), chance antes diferente: a "
               "decisão muda. A barra vermelha é a taxa-base real.")
    cenarios = sorted({0.01, taxa, 0.10, 0.20, 0.40})
    finais = []
    for c in cenarios:
        finais.append(bayes.teorema_de_bayes(c, pv, pn))
    fig = go.Figure(go.Bar(
        x=[pct(c) for c in cenarios], y=[f * 100 for f in finais], textposition="outside",
        text=[f"{pct(f)}<br>{bayes.decisao(f).lower()}" for f in finais],
        marker_color=[VERMELHO if c == taxa else CINZA for c in cenarios]))
    fig.update_layout(height=340, margin=dict(t=30), xaxis_title="chance antes", yaxis_title="chance depois (%)",
                      yaxis_range=[0, 125], xaxis_type="category")
    st.plotly_chart(fig, config={"displayModeBar": False})

    st.markdown("#### O mapa completo: a chance para cada posição e momento")
    linhas_mapa = bayes.SITUACOES[:-1]
    valores = []
    for s in linhas_mapa:
        valores.append([tabela_real[(m, s)] * 100 for m in bayes.MARCOS])
    fig = go.Figure(go.Heatmap(
        z=valores, x=["largada"] + [f"{m}%" for m in bayes.MARCOS[1:]], y=linhas_mapa, showscale=False,
        text=[[pct(v / 100, 0) for v in linha_mapa] for linha_mapa in valores], texttemplate="%{text}",
        textfont=dict(color="white"), colorscale=[[0, "#1B1B26"], [1, VERMELHO]]))
    fig.update_layout(height=460, margin=dict(t=10), xaxis_title="momento da corrida", xaxis_type="category",
                      yaxis_autorange="reversed")
    st.plotly_chart(fig, config={"displayModeBar": False})
    st.caption(f"Cada quadrado é uma conta de Bayes: chance antes de {pct(taxa)} e a posição naquele momento como "
               "evidência. Liderar no fim vale muito mais do que liderar no começo.")

with aba_dados:
    a, b, c, d = st.columns(4, border=True)
    a.metric("Corridas reais", largadas["corrida_id"].nunique())
    b.metric("Largadas (piloto em uma corrida)", milhar(len(largadas)))
    c.metric("Vencedores", int(largadas["venceu"].sum()))
    d.metric("Temporadas", "7 (sem 2023)")
    st.caption("Temporadas de 2018 a 2022 e de 2024 a 2025. A de 2023 ficou de fora (o servidor da F1 bloqueou o "
               "acesso durante a coleta) e faltam mais 7 corridas, 5 delas de 2020.")

    st.markdown("#### De onde vêm os números")
    st.markdown("**coletar_dados.py** baixa as corridas com a biblioteca FastF1 -> **data/voltas/** (a posição de cada "
                "piloto em cada volta) -> **data/marcos.csv** (a posição a cada 10% da corrida) -> **bayes.py** conta "
                "os casos e aplica a fórmula -> **app.py** mostra na tela (Streamlit)")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown(f"**Os dados de {linha['nome']} em {info['gp']} {info['ano']}** (a corrida da aba 1)")
        dados_dele = marcos[(marcos["corrida_id"] == cid) & (marcos["piloto"] == piloto)]
        st.dataframe(pd.DataFrame({
            "Momento": [nome_do_momento(m) for m in dados_dele["marco"]],
            "Volta": dados_dele["volta"],
            "Posição": dados_dele["situacao"],
            "Chance": [pct(tabela_real[(m, s)]) for m, s in zip(dados_dele["marco"], dados_dele["situacao"])],
        }), hide_index=True)
    with t2:
        st.markdown("**A fórmula em Python (bayes.py)**")
        st.code(inspect.getsource(bayes.teorema_de_bayes), language="python")

    st.markdown("#### O modelo acerta?")
    teste, n = avaliacao()
    nomes = list(teste)
    fig = go.Figure(go.Bar(
        x=nomes, y=[teste[k]["venceram"] / teste[k]["pilotos"] * 100 for k in nomes], textposition="outside",
        text=[f"{pct(teste[k]['venceram'] / teste[k]['pilotos'])}<br>{teste[k]['venceram']} de {teste[k]['pilotos']} "
              "pilotos" for k in nomes],
        marker_color=[corrida.CORES_DECISAO[k] for k in nomes]))
    fig.update_layout(height=340, margin=dict(t=30), xaxis_title="o que o sistema recomendou na metade da corrida",
                      yaxis_title="pilotos que venceram (%)", yaxis_range=[0, 100])
    st.plotly_chart(fig, config={"displayModeBar": False})
    defender = teste["DEFENDER"]["venceram"] / teste["DEFENDER"]["pilotos"]
    st.info(f"O modelo aprendeu só com 2018 a 2022 e foi testado nas {n} corridas de 2024 e 2025, que ele nunca viu. "
            f"Quando recomendou defender, o piloto venceu {pct(defender, 0)} das vezes; quando recomendou arriscar, "
            "quase nunca.")

    st.markdown("#### Limitações")
    st.markdown("""
- **Só olha a posição:** não sabe o carro, os pneus, os pit stops, a chuva nem o safety car.
- **A chance antes é igual para todos (5%):** um carro dominante começa com mais chance. Veja "E se a chance antes fosse outra?" na aba 2.
- **Usa só a posição de agora:** ela já resume o que aconteceu antes; somar as posições antigas contaria a mesma informação duas vezes.
- **Cada piloto é calculado sozinho:** as chances de uma corrida não somam exatamente 100%.
- **Momentos de 10 em 10% da corrida** e poucos exemplos de vitórias vindas de trás.
- **Faltam dados:** a temporada 2023 e mais 7 corridas.
""")
    st.caption("Fontes: FastF1 (cronometragem oficial da F1) e projeto aberto f1-circuits (desenho dos circuitos, "
               "licença MIT).")
