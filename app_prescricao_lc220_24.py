
import streamlit as st
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Prescrição (LC-RJ 220/2024) — Calculadora", layout="wide")

st.title("Calculadora de Prescrição — LC-RJ 220/2024 (art. 5º-A)")
st.caption("Modelo simplificado para apoio à decisão. Ajuste as premissas conforme o caso.")

# === Entrada básica ===
colA, colB, colC = st.columns(3)
with colA:
    natureza = st.selectbox("Natureza da pretensão", ["Punitiva", "Ressarcitória (analogia)"])
with colB:
    conduta = st.selectbox("Tipo de conduta", ["Instantânea", "Continuada"])
with colC:
    data_ato = st.date_input("Data do ato / cessação", value=date.today())

colD, colE, colF = st.columns(3)
with colD:
    data_autuacao = st.date_input("Data de autuação no TCE-RJ", value=date.today())
with colE:
    transitou_pre_lc = st.selectbox("Decisão adm. transitada em julgado antes de 18/07/2024?", ["Não", "Sim"])
with colF:
    aplicar_prazo_penal = st.selectbox("Fato também é crime? (aplicar prazo penal)", ["Não", "Sim"])

# === Sugerir enquadramento intertemporal (ajustável) ===
sugerido = "Novo regime (art. 5º-A)"
if transitou_pre_lc == "Sim":
    sugerido = "Fora do alcance: decisão anterior a 18/07/2024"
else:
    # Regras sugeridas (ajustáveis ao entendimento interno)
    if (data_ato <= date(2021,7,18)) and (data_autuacao <= date(2024,7,18)):
        sugerido = "Transição 2 anos (LC 220/24)"
    else:
        sugerido = "Novo regime (art. 5º-A)"

enquadramento = st.selectbox(
    "Enquadramento intertemporal (ajuste se necessário)",
    ["Novo regime (art. 5º-A)", "Transição 2 anos (LC 220/24)", "Prescrição consumada antes da lei", "Fora do alcance: decisão anterior a 18/07/2024"],
    index=["Novo regime (art. 5º-A)", "Transição 2 anos (LC 220/24)", "Prescrição consumada antes da lei", "Fora do alcance: decisão anterior a 18/07/2024"].index(sugerido)
)

# === Marcos interruptivos (§3º) ===
st.subheader("Marcos interruptivos (§ 3º)")
st.caption("Informe datas separadas por vírgula (formato AAAA-MM-DD), por exemplo: 2024-09-01, 2025-03-15")
txt_marcos = st.text_input("Datas dos marcos interruptivos", value="")
interrupcoes = []
if txt_marcos.strip():
    for part in txt_marcos.split(","):
        s = part.strip()
        try:
            interrupcoes.append(datetime.strptime(s, "%Y-%m-%d").date())
        except Exception:
            st.warning(f"Data inválida ignorada: {s} (use AAAA-MM-DD)")

# === Prescrição intercorrente (§1º) ===
st.subheader("Prescrição intercorrente (§ 1º)")
check_intercorrente = st.checkbox("Checar intercorrente (paralisação > 3 anos)?", value=False)
data_ultimo_ato = None
data_ato_subsequente = None
if check_intercorrente:
    c1, c2 = st.columns(2)
    with c1:
        data_ultimo_ato = st.date_input("Data do último ato útil (antes da paralisação)", value=date.today())
    with c2:
        use_hoje = st.checkbox("Usar a data de hoje como termo final da paralisação", value=True)
        if use_hoje:
            data_ato_subsequente = date.today()
        else:
            data_ato_subsequente = st.date_input("Data do ato subsequente (que retomou o processo)", value=date.today())

# === Prazo penal (se aplicável) ===
prazo_penal_anos = None
if aplicar_prazo_penal == "Sim":
    prazo_penal_anos = st.number_input("Prazo penal (anos)", min_value=1, max_value=40, value=8, step=1)

# === Funções utilitárias ===
def compute_deadline(regime: str, data_inicio: date, interrupcoes: list, base_anos: int) -> date:
    # Ordena interrupções e ignora as anteriores ao termo inicial
    ints = sorted([d for d in interrupcoes if d and d >= data_inicio])
    start = data_inicio
    for d in ints:
        if d >= start:
            start = d  # reinicia a contagem
    return start + relativedelta(years=base_anos)

# === Cálculo principal ===
resultado = {}
texto_conclusivo = ""

if enquadramento == "Fora do alcance: decisão anterior a 18/07/2024":
    resultado["sit"] = "Fora do alcance da LC 220/2024"
    resultado["detalhe"] = "Há decisão administrativa transitada em julgado anterior a 18/07/2024."
elif enquadramento == "Prescrição consumada antes da lei":
    resultado["sit"] = "Prescrição reconhecida (regime anterior)"
    resultado["detalhe"] = "A prescrição consumou-se integralmente antes de 18/07/2024, sob o regime precedente."
else:
    # Base de anos
    if prazo_penal_anos:
        base_anos = prazo_penal_anos
        base_label = f"prazo penal ({prazo_penal_anos} anos)"
    else:
        base_anos = 5 if enquadramento == "Novo regime (art. 5º-A)" else 2
        base_label = "quinquenal" if base_anos == 5 else "bienal (transição)"

    # Termo inicial
    if enquadramento == "Novo regime (art. 5º-A)":
        termo_inicial = data_ato
    else:
        termo_inicial = date(2024,7,18)  # transição

    # Prazo final com interrupções
    prazo_final = compute_deadline(enquadramento, termo_inicial, interrupcoes, base_anos)

    # Intercorrente
    intercorrente = False
    periodo_intercorrente = None
    if check_intercorrente and data_ultimo_ato and data_ato_subsequente:
        # Se retomou, mede o intervalo entre último ato e o subsequente; caso contrário, entre último ato e hoje
        dias = (data_ato_subsequente - data_ultimo_ato).days
        if dias >= 365*3:
            intercorrente = True
            periodo_intercorrente = dias

    # Conclusão
    hoje = date.today()
    if intercorrente:
        resultado["sit"] = "Prescrição intercorrente"
        resultado["detalhe"] = f"Paralisação superior a 3 anos ({periodo_intercorrente} dias)."
        texto_conclusivo = (
            f"Verificada paralisação processual superior a 3 anos, reconhece-se a prescrição intercorrente, "
            f"com arquivamento, sem prejuízo de apuração funcional cabível."
        )
    else:
        if hoje >= prazo_final:
            resultado["sit"] = "Prescrição consumada"
            resultado["detalhe"] = f"Esgotado o prazo {base_label}: {prazo_final.strftime('%d/%m/%Y')}."
            texto_conclusivo = (
                f"Esgotado o prazo {base_label}, com data-alvo em {prazo_final.strftime('%d/%m/%Y')}, "
                f"impõe-se o reconhecimento da prescrição."
            )
        else:
            resultado["sit"] = "Não prescrito"
            resultado["detalhe"] = f"Data-alvo projetada ({base_label}): {prazo_final.strftime('%d/%m/%Y')}."
            texto_conclusivo = (
                f"À vista do termo inicial em {termo_inicial.strftime('%d/%m/%Y')} e dos marcos interruptivos informados, "
                f"não se verifica prescrição, projetando-se a data-alvo para {prazo_final.strftime('%d/%m/%Y')}."
            )

    # Armazenar extras
    resultado["termo_inicial"] = termo_inicial
    resultado["prazo_final"] = prazo_final
    resultado["base"] = base_label
    resultado["interrupcoes"] = sorted(interrupcoes)

# === Saída ===
st.markdown("### Resultado")
for k, v in resultado.items():
    if isinstance(v, date):
        st.write(f"**{k}:** {v.strftime('%d/%m/%Y')}")
    else:
        st.write(f"**{k}:** {v}")

# Texto modelo para colar no parecer
st.markdown("### Texto para o parecer (editar conforme o caso)")
bloco = f'''
Enquadramento: {enquadramento}. Natureza: {natureza}. Conduta: {conduta}.
Termo inicial adotado: {resultado.get("termo_inicial").strftime("%d/%m/%Y") if resultado.get("termo_inicial") else "N/A"}.
Interrupções consideradas: {", ".join([d.strftime("%d/%m/%Y") for d in resultado.get("interrupcoes", [])]) or "não informado"}.
Situação: {resultado.get("sit")}. Detalhe: {resultado.get("detalhe")}.
{texto_conclusivo}
'''
st.text_area("Copiar/colar no parecer", value=bloco.strip(), height=220)

st.markdown("---")
st.caption("Notas: (i) Interrupções (§3º) reiniciam a contagem; (ii) intercorrente (§1º) exige paralisação > 3 anos sem julgamento/dispacho; (iii) se o fato também for crime, aplica-se o prazo penal.")
