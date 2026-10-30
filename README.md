# Box Box Bayes

**A chance de vitória na Fórmula 1, atualizada volta a volta com o Teorema de Bayes.**

Seminário de Estatística Aplicada a ADS (2026), Grupo 1: Diogo e João Vitor
Tema: Teorema de Bayes e atualização de probabilidades. Opção escolhida: Esportes, atualizador da chance de vitória durante uma partida

| | |
|---|---|
| **Objetivo** | Calcular, a cada volta, a chance de um piloto vencer a corrida e transformar essa chance numa recomendação |
| **Usuário e decisão** | Estrategista da equipe: arriscar (abaixo de 10%), manter o plano (10% a 50%) ou defender (50% ou mais) |
| **Como o Bayes entra** | Chance antes (taxa-base): 144 vencedores em 2.867 largadas = 5%. Evidência: a posição do piloto naquele momento da corrida. Chance depois: P(V \| E) = P(E \| V) x P(V) / [P(E \| V) x P(V) + P(E \| não V) x P(não V)] |
| **Tecnologias** | Python 3.10+, Streamlit (interface web), Plotly (gráficos), pandas, FastF1 (coleta) |
| **Fonte dos dados** | Cronometragem oficial da F1 via biblioteca FastF1. Dados reais: 144 corridas de 2018 a 2022 e de 2024 a 2025, 2.867 largadas. A temporada 2023 ficou de fora (o servidor da F1 bloqueou o acesso durante a coleta) e faltam mais 7 corridas, 5 delas de 2020. Desenho dos circuitos: projeto aberto f1-circuits (licença MIT) |
| **Base** | `data/voltas/`: a posição de cada piloto em cada volta. `data/marcos.csv`: a posição de cada piloto a cada 10% da corrida (28.670 linhas). `data/largadas.csv`: uma linha por piloto em cada corrida (grid, resultado, equipe) |
| **Validação** | Treino de 2018 a 2022, teste nas 48 corridas de 2024 e 2025, na metade da prova: quando o sistema recomendou defender, o piloto venceu 77% das vezes (37 de 48); manter o plano, 8% (4 de 48); arriscar, 0,8% (7 de 856) |

## O que vamos demonstrar

Na aba **Corrida ao vivo**, o GP de São Paulo 2024: Max Verstappen largou em 17º e venceu. A chance dele começa em
0,3%, sobe aos poucos enquanto ele ganha posições, está em 19% com metade da corrida (em 2º), pula para 73% na volta 43,
quando ele passa o Ocon, e termina em 89%. Na aba **Como o Bayes calcula**, montamos uma situação (por exemplo, 2º com
metade da corrida) e mudamos a chance antes para mostrar que a conclusão muda com a taxa-base. Na aba **Dados e
validação**, mostramos a origem dos dados, o teste e as limitações.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Rode de dentro desta pasta. O app abre em http://localhost:8501. Os dados já estão em `data/`.

Para baixar os dados de novo (opcional; demora por causa do limite de 500 chamadas por hora da FastF1):

```bash
pip install fastf1
python coletar_dados.py
```

## Arquivos

| Arquivo | O que faz |
|---|---|
| `coletar_dados.py` | Baixa as corridas com a FastF1 e gera `data/largadas.csv`, `data/voltas/`, `data/marcos.csv` e `data/circuitos.json` |
| `bayes.py` | O Teorema de Bayes, as contagens (taxa-base, P(E \| V), P(E \| não V)), a decisão e o teste |
| `app.py` | A interface com 3 abas: Corrida ao vivo, Como o Bayes calcula, Dados e validação |
| `corrida.py` | A corrida animada: os carros andando no circuito e a chance mudando a cada volta |
| `.streamlit/config.toml` | As cores do app (tema escuro com vermelho) |

## Referências

- FastF1 (dados de cronometragem da F1): https://docs.fastf1.dev
- f1-circuits (desenho dos circuitos, licença MIT): https://github.com/bacinger/f1-circuits
- Streamlit: https://docs.streamlit.io
- Plotly: https://plotly.com/python
- História do teorema: MacTutor History of Mathematics, "Thomas Bayes" (Universidade de St Andrews)
