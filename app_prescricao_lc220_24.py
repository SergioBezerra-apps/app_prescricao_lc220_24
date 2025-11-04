import streamlit as st
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import io
import csv

st.set_page_config(page_title="Prescrição — LC-RJ 63/1990 (art. 5º-A) — Multi-Gestores", layout="wide")
st.markdown("<style>.block-container {max-width:980px; padding-left:12px; padding-right:12px;}</style>", unsafe_allow_html=True)

# =============================
# Cabeçalho
# =============================
st.title("Calculadora de Prescrição — LC-RJ 63/1990 (art. 5º-A)")
st.caption(
    "Ferramenta de apoio. Ajuste as premissas ao caso concreto, **registre a motivação** no parecer e **anexe documentos** "
    "que comprovem a ciência (quando diversa da autuação) e os marcos interruptivos. "
    "Agora com suporte a **múltiplos gestores** (efeito subjetivo do chamamento qualificado)."
)

# =============================
# 1) Natureza e dados básicos
# =============================
colA, colB, colC = st.columns([1.2, 1, 1])
with colA:
    natureza = st.selectbox(
        "Natureza da pretensão",
        ["Punitiva", "Ressarcitória (analogia)"],
        help=(
            "Selecione **Punitiva** (ex.: multa) ou **Ressarcitória (analogia)**. A LCE 220/2024 (art. 5º-A) rege a prescrição no TCE-RJ; "
            "por consolidação plenária, aplica-se também **por analogia** à pretensão ressarcitória. "
            "O cálculo de prazo e o termo inicial dependem da **chave intertemporal** (itens abaixo)."
        ),
    )
with colB:
    conduta = st.selectbox(
        "Tipo de conduta",
        ["Instantânea", "Continuada"],
        help=(
            "**Instantânea**: ato único em uma data. **Continuada**: efeitos que perduram (p.ex., execução contratual com pagamentos). "
            "Para condutas continuadas, use a **data de cessação** como referência material."
        ),
    )
with colC:
    data_autuacao = st.date_input(
        "Data de autuação no TCE-RJ",
        value=date.today(),
        help=(
            "Data em que o processo foi **autuado/cadastrado** no TCE-RJ. Em regra, funciona como **ciência** institucional do Tribunal "
            "quando não houver comprovação de ciência anterior. **Atenção**: para **fatos anteriores a 18/07/2021**, o regime **anterior** "
            "considera a **ciência** como termo inicial."
        ),
    )

# Ciência explícita (pode coincidir com a autuação)
data_ciencia = st.date_input(
    "Data de ciência pelo TCE-RJ (se diversa da autuação)",
    value=data_autuacao,
    help=(
        "Informe se houve **ciência anterior/posterior** à autuação (ex.: ofício com AR, e-mail institucional com contraditório aberto, "
        "decisão determinando chamamento). Para **fatos anteriores a 18/07/2021**, **esta data** será o **termo inicial** no "
        "**Regime anterior (quinquênio da ciência)**. **Documente** no processo."
    ),
)

# Termo inicial do FATO/EVENTO (para intertemporal)
st.subheader("Termo inicial material (fato/evento)")
if natureza == "Punitiva":
    data_ato = st.date_input(
        "Data do ato (ou da cessação, se continuada)",
        value=date.today(),
        help=(
            "Para o **novo regime** (art. 5º-A), o **termo inicial material** é a **data do ato**; se continuada, a **cessação**. "
            "Essa data também alimenta a **chave intertemporal**:\n"
            "• se **< 18/07/2021** ⇒ o caso **é pretérito**;\n"
            "• se **≥ 18/07/2021** ⇒ o caso **é do novo regime**."
        ),
    )
    termo_inicial_fato = data_ato
    termo_inicial_fato_label = "Data do ato/cessação (punitiva)"
else:
    st.markdown("Defina e motive o termo inicial **material** (ressarcitória por analogia).")
    base_ress = st.radio(
        "Como fixar o termo inicial (ressarcitória)?",
        [
            "Evento danoso (data do dano)",
            "Última medição/pagamento (contratos)",
            "Cessação do dano (se continuada)",
        ],
        help=(
            "Defina a **base motivada**: (i) **evento danoso**; (ii) **última medição/pagamento** (contratos); ou (iii) **cessação do dano** "
            "(se continuado). Essa escolha abastece a **chave intertemporal** e deve ser **fundamentada** no parecer."
        ),
    )
    if base_ress == "Evento danoso (data do dano)":
        data_base = st.date_input("Data do evento danoso", value=date.today())
    elif base_ress == "Última medição/pagamento (contratos)":
        data_base = st.date_input("Data da última medição/pagamento ligada ao sobrepreço/irregularidade", value=date.today())
    else:
        data_base = st.date_input("Data de cessação do dano", value=date.today())
    termo_inicial_fato = data_base
    termo_inicial_fato_label = f"{base_ress}"

colD, colE, colF = st.columns(3)
with colD:
    transitou_pre_lc = st.selectbox(
        "Decisão adm. transitada em julgado antes de 18/07/2024?",
        ["Não", "Sim"],
        help="Se **‘Sim’**, a LCE 220/2024 **não alcança** o caso (ato **findo**).",
    )
with colE:
    aplicar_prazo_penal = st.selectbox(
        "Fato também é crime? (aplicar prazo penal)",
        ["Não", "Sim"],
        help="Se o fato também constitui crime, **prevalece o prazo penal** (art. 5º-A, § 2º).",
    )
with colF:
    prazo_penal_anos = None
    if aplicar_prazo_penal == "Sim":
        prazo_penal_anos = st.number_input(
            "Prazo penal (anos)",
            min_value=1,
            max_value=40,
            value=8,
            step=1,
            help="Informe o **prazo prescricional penal** aplicável ao tipo."
        )

# =============================
# 2) Enquadramento intertemporal
# =============================
st.subheader("Enquadramento intertemporal")

from datetime import date as _date_for_prevcheck

def _is_prescribed_before_law(ciencia: _date_for_prevcheck, interrupcoes: list[_date_for_prevcheck]) -> bool:
    """
    Verifica prescrição consumada até 18/07/2024 segundo o regime anterior (quinquênio),
    usando a data de ciência (informada ou autuação) e marcos interruptivos até o cutoff.
    """
    cutoff = _date_for_prevcheck(2024, 7, 18)
    if not isinstance(ciencia, _date_for_prevcheck):
        return False
    ints_prev = sorted([d for d in interrupcoes if isinstance(d, _date_for_prevcheck) and ciencia <= d <= cutoff])
    start = ciencia
    for d in ints_prev:
        if d >= start:
            start = d
    return start + relativedelta(years=5) <= cutoff

def _prelaw_prescription_date(ciencia: _date_for_prevcheck, interrupcoes: list[_date_for_prevcheck]) -> _date_for_prevcheck | None:
    """
    Calcula a data de consumação da prescrição no regime anterior (quinquênio),
    considerando ciência e interrupções até 18/07/2024.
    """
    cutoff = _date_for_prevcheck(2024, 7, 18)
    if not isinstance(ciencia, _date_for_prevcheck):
        return None
    ints_prev = sorted([d for d in interrupcoes if isinstance(d, _date_for_prevcheck) and ciencia <= d <= cutoff])
    start = ciencia
    for d in ints_prev:
        if d >= start:
            start = d
    return start + relativedelta(years=5)

# Chave intertemporal: fatos antes/depois de 18/07/2021
fatos_pre_2021 = (termo_inicial_fato < date(2021, 7, 18))

# =============================
# 3) Marcos interruptivos — gerais x subjetivos
# =============================
st.subheader("Marcos interruptivos")
st.caption(
    "Marcos **gerais** (objetivos, valem para todos): ex., **determinação de auditoria** / **instauração** (ato inequívoco de apuração), "
    "**decisão condenatória recorrível**, **tentativa conciliatória**. **Simples protocolo não interrompe**.\n"
    "Marcos **subjetivos** (por gestor): **chamamento qualificado** (com contraditório; efeito subjetivo; retroage à decisão que determinou)."
)

# --- Marcos gerais (valem para todos) ---
st.markdown("#### Marcos gerais (valem para todos)")
def _init_global_state():
    if "g_marco_count" not in st.session_state:
        st.session_state.g_marco_count = 1
    if "g_marco_dates" not in st.session_state:
        st.session_state.g_marco_dates = [None]
_init_global_state()

colG1, colG2 = st.columns([1, 1])
with colG1:
    no_global_inter = st.checkbox("Não houve marco geral", value=False)
with colG2:
    pass

def _g_add(): 
    st.session_state.g_marco_count += 1
    st.session_state.g_marco_dates.append(None)
def _g_rem():
    if st.session_state.g_marco_count > 1:
        st.session_state.g_marco_count -= 1
        st.session_state.g_marco_dates = st.session_state.g_marco_dates[: st.session_state.g_marco_count]
def _g_clr():
    st.session_state.g_marco_count = 1
    st.session_state.g_marco_dates = [None]

global_marcos = []
if not no_global_inter:
    for i in range(st.session_state.g_marco_count):
        default_val = st.session_state.g_marco_dates[i] or date.today()
        picked = st.date_input(f"Data do marco geral #{i+1}", value=default_val, key=f"g_marco_{i}")
        st.session_state.g_marco_dates[i] = picked
    gcolA, gcolB, gcolC = st.columns(3)
    gcolA.button("➕ Adicionar marco geral", use_container_width=True, on_click=_g_add)
    gcolB.button("➖ Remover último", disabled=st.session_state.g_marco_count <= 1, use_container_width=True, on_click=_g_rem)
    gcolC.button("🗑️ Limpar todos", use_container_width=True, on_click=_g_clr)
    global_marcos = [d for d in st.session_state.g_marco_dates if isinstance(d, date)]
else:
    global_marcos = []

st.markdown("---")

# --- Lista de gestores ---
st.markdown("#### Gestores (um por linha)")
gestores_text = st.text_area(
    "Nomes dos gestores",
    value="Gestor A\nGestor B",
    help="Indique um gestor por linha. Para cada gestor, você poderá registrar os **chamamentos qualificados** (efeito subjetivo).",
    height=90
)
gestores = [g.strip() for g in gestores_text.splitlines() if g.strip()]

# --- Marcos subjetivos por gestor (chamamentos qualificados) ---
st.markdown("#### Chamamentos qualificados por gestor (efeito subjetivo)")
if "gestor_marcos" not in st.session_state:
    st.session_state.gestor_marcos = {}  # nome -> [dates]

# garantir chaves
for g in gestores:
    if g not in st.session_state.gestor_marcos:
        st.session_state.gestor_marcos[g] = []

# UI por gestor
for g in gestores:
    with st.expander(f"Chamamentos qualificados — {g}", expanded=False):
        # estado por gestor
        cnt_key = f"{g}__cnt"
        if cnt_key not in st.session_state:
            st.session_state[cnt_key] = 1
            st.session_state.gestor_marcos[g] = [None]
        # render
        no_subj = st.checkbox(f"{g}: não houve chamamento qualificado", value=False, key=f"{g}__none")
        def _add_g(g=g):
            st.session_state[cnt_key] += 1
            st.session_state.gestor_marcos[g].append(None)
        def _rem_g(g=g):
            if st.session_state[cnt_key] > 1:
                st.session_state[cnt_key] -= 1
                st.session_state.gestor_marcos[g] = st.session_state.gestor_marcos[g][: st.session_state[cnt_key]]
        def _clr_g(g=g):
            st.session_state[cnt_key] = 1
            st.session_state.gestor_marcos[g] = [None]

        if not no_subj:
            for i in range(st.session_state[cnt_key]):
                default_val = st.session_state.gestor_marcos[g][i] or date.today()
                picked = st.date_input(f"{g} — data do chamamento #{i+1}", value=default_val, key=f"{g}__marco_{i}")
                st.session_state.gestor_marcos[g][i] = picked
            c1, c2, c3 = st.columns(3)
            c1.button("➕ Adicionar", use_container_width=True, key=f"{g}__add_btn", on_click=_add_g)
            c2.button("➖ Remover última", disabled=st.session_state[cnt_key] <= 1, use_container_width=True, key=f"{g}__rem_btn", on_click=_rem_g)
            c3.button("🗑️ Limpar todas", use_container_width=True, key=f"{g}__clr_btn", on_click=_clr_g)
        else:
            st.session_state[cnt_key] = 1
            st.session_state.gestor_marcos[g] = []

# =============================
# 4) Definição do enquadramento (global)
# =============================
# Pré-teste: prescrição consumada antes da lei (com ciência explícita)
presc_antes_lei_auto = _is_prescribed_before_law(data_ciencia, global_marcos)

if transitou_pre_lc == "Sim":
    sugerido = "Fora do alcance: decisão anterior a 18/07/2024"
elif presc_antes_lei_auto:
    sugerido = "Prescrição consumada antes da lei"
elif fatos_pre_2021:
    sugerido = "Regime anterior (quinquênio da ciência)"
else:
    sugerido = "Novo regime (art. 5º-A)"

enquadramento = st.selectbox(
    "Selecione o enquadramento (global para o caso; ajuste se necessário)",
    [
        "Novo regime (art. 5º-A)",
        "Regime anterior (quinquênio da ciência)",
        "Transição 2 anos (LC 220/24)",
        "Prescrição consumada antes da lei",
        "Fora do alcance: decisão anterior a 18/07/2024",
    ],
    index=[
        "Novo regime (art. 5º-A)",
        "Regime anterior (quinquênio da ciência)",
        "Transição 2 anos (LC 220/24)",
        "Prescrição consumada antes da lei",
        "Fora do alcance: decisão anterior a 18/07/2024",
    ].index(sugerido),
    help=(
        "**Chave intertemporal – regras operativas**\n"
        "1) **Fatos < 18/07/2021** ⇒ priorize **Regime anterior (quinquênio da ciência)**:\n"
        "   • **Termo inicial** = **ciência pelo TCE-RJ** (em regra, autuação, salvo prova de ciência diversa).\n"
        "   • **Prazo** = 5 anos, com marcos (gerais + chamamentos qualificados).\n"
        "   • **Caso-limite**: ciência **após** 18/07/2024 (p.ex., 12/12/2024) → **quinquênio da ciência** (12/12/2024 → 12/12/2029).\n"
        "2) **Fatos ≥ 18/07/2021** ⇒ **Novo regime (art. 5º-A)**: termo = fato/cessação; prazo = 5 anos.\n"
        "3) **Transição 2 anos**: opção **manual** e excepcional, quando estritamente cabível.\n"
        "4) **Fora do alcance**: processos transitados administrativamente antes de 18/07/2024."
    ),
)

# =============================
# 5) Prescrição intercorrente (§1º) — global
# =============================
st.subheader("Prescrição intercorrente (§ 1º)")
st.caption("Há **paralisação > 3 anos** sem julgamento/ despacho? Se **sim**, marque a verificação e informe **data do último ato útil** e **data subsequente** (ou ‘hoje’).")
check_intercorrente = st.checkbox("Checar intercorrente?", value=False)

data_ultimo_ato = None
idata_subseq = None
if check_intercorrente:
    c1, c2 = st.columns(2)
    with c1:
        data_ultimo_ato = st.date_input("Data do último ato útil", value=date.today())
    with c2:
        use_hoje = st.checkbox("Usar a data de hoje como termo final", value=True)
        if use_hoje:
            idata_subseq = date.today()
        else:
            idata_subseq = st.date_input("Data do ato subsequente", value=date.today())

# =============================
# 6) Motor de cálculo
# =============================
def compute_deadline(data_inicio: date, interrupcoes: list[date], base_anos: int) -> tuple[date, bool]:
    """Retorna (data_final, houve_interrupcao_valida). Ignora marcos anteriores ao termo inicial."""
    ints = sorted([d for d in interrupcoes if d and d >= data_inicio])
    start = data_inicio
    for d in ints:
        if d >= start:
            start = d  # reinicia a contagem a partir do marco
    return start + relativedelta(years=base_anos), (len(ints) > 0)

def calcular_por_gestor(nome_gestor: str,
                        enquadramento: str,
                        termo_inicial_fato: date,
                        data_ciencia: date,
                        global_marcos: list[date],
                        subj_marcos: list[date],
                        aplicar_prazo_penal: str,
                        prazo_penal_anos: int | None,
                        check_intercorrente: bool,
                        data_ultimo_ato: date | None,
                        idata_subseq: date | None) -> dict:
    """
    Retorna um dict com o resultado individual do gestor (situação, base, termo, prazo, marcos usados, etc.)
    """
    resultado = {}
    option_text = None

    # Conjunto de marcos aplicáveis ao gestor = globais + subjetivos (chamamentos do gestor)
    interrupcoes = sorted([d for d in (global_marcos + subj_marcos) if isinstance(d, date)])

    # Enquadramento especial "Prescrição consumada antes da lei"
    if enquadramento == "Prescrição consumada antes da lei":
        cutoff = date(2024, 7, 18)
        ciencia = data_ciencia if isinstance(data_ciencia, date) else None
        # Só marcos até o cutoff importam no pré-lei
        ints_prev = [d for d in interrupcoes if d <= cutoff]
        # data de consumação (pré-lei)
        def _prelaw(ciencia, ints):
            if not ciencia:
                return None
            ints_prev_sorted = sorted([d for d in ints if d >= ciencia])
            start = ciencia
            for d in ints_prev_sorted:
                if d >= start:
                    start = d
            return start + relativedelta(years=5)
        data_prelaw = _prelaw(ciencia, ints_prev)
        resultado["sit"] = "Prescrição reconhecida (regime anterior)"
        if isinstance(data_prelaw, date):
            resultado["detalhe"] = f"Consumação em {data_prelaw.strftime('%d/%m/%Y')} (antes de 18/07/2024)."
            option_text = (
                f"[{nome_gestor}] Consumação em {data_prelaw.strftime('%d/%m/%Y')}, antes de 18/07/2024 — "
                "reconhecimento por segurança jurídica e irretroatividade."
            )
        else:
            resultado["detalhe"] = "Consumação integral antes de 18/07/2024 (regime anterior)."
            option_text = f"[{nome_gestor}] Consumação integral antes de 18/07/2024 (regime anterior)."
        resultado["termo_inicial"] = ciencia
        resultado["termo_inicial_label"] = "Ciência (TCE-RJ) — regime anterior"
        resultado["base"] = "quinquenal (regime anterior)"
        resultado["prazo_final"] = data_prelaw
        resultado["interrupcoes"] = sorted(ints_prev)
        resultado["option_text"] = option_text
        return resultado

    # Base (penal prevalece)
    if aplicar_prazo_penal == "Sim" and prazo_penal_anos:
        base_anos = prazo_penal_anos
        base_label = f"prazo penal ({prazo_penal_anos} anos)"
    else:
        if enquadramento == "Novo regime (art. 5º-A)":
            base_anos = 5
            base_label = "quinquenal"
        elif enquadramento == "Regime anterior (quinquênio da ciência)":
            base_anos = 5
            base_label = "quinquenal (ciência)"
        else:
            base_anos = 2
            base_label = "bienal (transição)"

    # Termo inicial efetivo
    if enquadramento == "Novo regime (art. 5º-A)":
        termo_inicial_efetivo = termo_inicial_fato
        termo_inicial_label_calc = "Termo inicial informado (fato/cessação)"
    elif enquadramento == "Regime anterior (quinquênio da ciência)":
        termo_inicial_efetivo = data_ciencia
        termo_inicial_label_calc = "Ciência (TCE-RJ)"
    else:  # Transição
        termo_inicial_efetivo = date(2024, 7, 18)
        termo_inicial_label_calc = "Transição (18/07/2024)"

    prazo_final, has_valid_interruptions = compute_deadline(termo_inicial_efetivo, interrupcoes, base_anos)

    # Intercorrente (global, mas relatada no cartão individual para transparência)
    intercorrente = False
    periodo_intercorrente = None
    if check_intercorrente and data_ultimo_ato and idata_subseq:
        dias = (idata_subseq - data_ultimo_ato).days
        if dias >= 365 * 3:
            intercorrente = True
            periodo_intercorrente = dias

    hoje = date.today()
    interrupcoes_consideradas = sorted([d for d in interrupcoes if d and d >= termo_inicial_efetivo])
    interrupcoes_str = ", ".join([d.strftime("%d/%m/%Y") for d in interrupcoes_consideradas])

    if intercorrente:
        resultado["sit"] = "Prescrição intercorrente"
        resultado["detalhe"] = f"Paralisação superior a 3 anos ({periodo_intercorrente} dias)."
        option_text = (
            f"[{nome_gestor}] Verificada paralisação > 3 anos; reconhecer prescrição intercorrente, com arquivamento, "
            "sem prejuízo de apuração funcional."
        )
    else:
        if hoje >= prazo_final:
            resultado["sit"] = "Prescrição consumada"
            resultado["detalhe"] = f"Esgotado o prazo {base_label}: {prazo_final.strftime('%d/%m/%Y')}."
            base_txt = "novo regime" if enquadramento == "Novo regime (art. 5º-A)" else (
                "regime anterior (ciência)" if enquadramento == "Regime anterior (quinquênio da ciência)" else "transição bienal"
            )
            option_text = (
                f"[{nome_gestor}] Enquadrado no {base_txt}, escoado o prazo {base_label} contado de "
                f"{termo_inicial_efetivo.strftime('%d/%m/%Y')}, "
                "sem marcos interruptivos válidos, impõe-se o reconhecimento da prescrição."
            )
        else:
            resultado["sit"] = "Não prescrito"
            resultado["detalhe"] = f"Data-alvo projetada ({base_label}): {prazo_final.strftime('%d/%m/%Y')}."
            mi_text = f"dos marcos interruptivos em [{interrupcoes_str}]" if interrupcoes_consideradas else "sem marcos interruptivos identificados"
            option_text = (
                f"[{nome_gestor}] À vista do termo inicial em {termo_inicial_efetivo.strftime('%d/%m/%Y')}, "
                f"{mi_text} e da ausência de paralisação superior a 3 anos, não se verifica prescrição; "
                "prossiga-se para exame de mérito."
            )

    resultado["natureza"] = natureza
    resultado["conduta"] = conduta
    resultado["termo_inicial"] = termo_inicial_efetivo
    resultado["termo_inicial_label"] = termo_inicial_label_calc
    resultado["prazo_final"] = prazo_final
    resultado["base"] = base_label
    resultado["interrupcoes"] = interrupcoes_consideradas
    resultado["option_text"] = option_text
    return resultado

# =============================
# 7) Cálculo por gestor + exportação
# =============================
st.markdown("### Resultados por gestor")

def _color_for_status(s: str) -> str:
    s = (s or '').lower()
    if 'prescrição consumada' in s or 'intercorrente' in s or 'prescrição reconhecida' in s:
        return '#D93025'  # vermelho
    elif 'não prescrito' in s:
        return '#1E8E3E'  # verde
    else:
        return '#1A73E8'  # azul

export_rows = []
ciencia_info = data_ciencia.strftime('%d/%m/%Y') if isinstance(data_ciencia, date) else '—'
fato_info = termo_inicial_fato.strftime('%d/%m/%Y') if isinstance(termo_inicial_fato, date) else '—'

for g in gestores:
    subj_list = [d for d in st.session_state.gestor_marcos.get(g, []) if isinstance(d, date)]
    res = calcular_por_gestor(
        nome_gestor=g,
        enquadramento=enquadramento,
        termo_inicial_fato=termo_inicial_fato,
        data_ciencia=data_ciencia,
        global_marcos=global_marcos,
        subj_marcos=subj_list,
        aplicar_prazo_penal=aplicar_prazo_penal,
        prazo_penal_anos=prazo_penal_anos,
        check_intercorrente=check_intercorrente,
        data_ultimo_ato=data_ultimo_ato,
        idata_subseq=idata_subseq
    )

    _sit = res.get('sit', '—')
    _status_color = _color_for_status(_sit)
    _termo = res.get('termo_inicial')
    _prazo = res.get('prazo_final')
    _ints = res.get('interrupcoes', [])
    _ints_str = ", ".join([d.strftime('%d/%m/%Y') for d in _ints]) if _ints else '—'
    _html = f"""
    <div style='border:1px solid {_status_color}; padding:16px; border-radius:12px; margin-bottom:8px;'>
      <div style='font-weight:700; font-size:1.05rem; color:{_status_color};'>[{g}] Situação: {res.get('sit','—')}</div>
      <div style='margin-top:6px;'>{res.get('detalhe','—')}</div>
      <hr style='border:none; border-top:1px dashed #ddd; margin:12px 0;'>
      <div style='display:grid; grid-template-columns: 1fr 1fr; gap:8px;'>
        <div><b>Enquadramento:</b> {enquadramento}</div>
        <div><b>Base:</b> {res.get('base','—')}</div>
        <div><b>Natureza:</b> {res.get('natureza','—')}</div>
        <div><b>Conduta:</b> {res.get('conduta','—')}</div>
        <div><b>Termo inicial (cálculo):</b> {(_termo.strftime('%d/%m/%Y') if isinstance(_termo, date) else '—')} ({res.get('termo_inicial_label','')})</div>
        <div><b>Data atual de prescrição:</b> {(_prazo.strftime('%d/%m/%Y') if isinstance(_prazo, date) else '—')}</div>
        <div><b>Ciência considerada (TCE-RJ):</b> {ciencia_info}</div>
        <div><b>Data do fato/cessação:</b> {fato_info}</div>
        <div style='grid-column: 1 / -1;'><b>Interrupções (gerais + {g}):</b> {_ints_str}</div>
      </div>
      {f"<div style='margin-top:12px; padding:12px; background:#fff5f5; border-left:4px solid {_status_color}; border-radius:8px;'><div style='font-weight:600;'>Conclusão sugerida:</div><div>{res.get('option_text','')}</div></div>" if res.get('option_text') else ""}
    </div>
    """
    st.markdown(_html, unsafe_allow_html=True)

    export_rows.append({
        "gestor": g,
        "enquadramento": enquadramento,
        "situacao": res.get('sit','—'),
        "base": res.get('base','—'),
        "termo_inicial": _termo.strftime('%Y-%m-%d') if isinstance(_termo, date) else '',
        "prazo_final": _prazo.strftime('%Y-%m-%d') if isinstance(_prazo, date) else '',
        "ciencia": ciencia_info,
        "fato_cessacao": fato_info,
        "interrupcoes": _ints_str
    })

# =============================
# 8) Exportar CSV (resumo por gestor)
# =============================
st.markdown("#### Exportação")
if export_rows:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["gestor","enquadramento","situacao","base","termo_inicial","prazo_final","ciencia","fato_cessacao","interrupcoes"])
    writer.writeheader()
    writer.writerows(export_rows)
    csv_bytes = output.getvalue().encode("utf-8")
    st.download_button(
        "⬇️ Baixar resumo (CSV)",
        data=csv_bytes,
        file_name="prescricao_resultados_por_gestor.csv",
        mime="text/csv",
        use_container_width=True
    )

# =============================
# 9) Linha do tempo (opcional)
# =============================
st.markdown("----")
show_timeline = st.checkbox(
    "Mostrar linha do tempo (regime anterior e regime aplicável)",
    value=False,
    help=(
        "Mostra, em duas faixas: (i) **Regime anterior (ciência)** até 18/07/2024, com marcos gerais e consumação projetada; "
        "e (ii) o **regime aplicável** escolhido (novo/transição/ciência), com termo efetivo, marcos (gerais + subjetivos do gestor selecionado) e **data-alvo**."
    ),
)

def _render_timeline_html(title: str, events: list[tuple[str, date, str]]):
    if not events or len(events) < 2:
        st.info("Eventos insuficientes para montar a linha do tempo.")
        return
    evs = sorted(events, key=lambda e: e[1])
    d0 = evs[0][1]
    d1 = evs[-1][1]
    span = (d1 - d0).days or 1
    color_map = {
        'tab:blue': '#1A73E8',
        'tab:orange': '#FB8C00',
        'tab:red': '#D93025',
        'tab:gray': '#9AA0A6',
        '#D93025': '#D93025',
        '#1A73E8': '#1A73E8'
    }
    html = []
    html.append("<div style='margin-top:8px;margin-bottom:16px'>")
    html.append(f"<div style='font-weight:600;margin-bottom:6px'>{title}</div>")
    html.append("<div style='position:relative;height:76px;border-top:2px solid #ddd;'>")
    for lbl, d, col in evs:
        left = int(((d - d0).days / span) * 100)
        c = color_map.get(col, col)
        html.append(f"<div style='position:absolute;left:{left}%;top:-6px;transform:translateX(-50%);text-align:center;'>"
                    "<div style='width:10px;height:10px;border-radius:50%;background:"+c+";margin-bottom:4px;'></div>"
                    f"<div style='font-size:11px;white-space:nowrap'>{lbl}</div>"
                    f"<div style='font-size:11px;color:#555'>{d.strftime('%d/%m/%Y')}</div>"
                    "</div>")
    html.append("</div></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

if show_timeline and gestores:
    # Seletor para qual gestor exibir marcos subjetivos na linha do tempo 2
    g_select = st.selectbox("Gestor para linha do tempo (aplica marcos subjetivos deste gestor)", gestores)
    subj_list = [d for d in st.session_state.gestor_marcos.get(g_select, []) if isinstance(d, date)]

    # --- Regime anterior (ciência) até 18/07/2024 ---
    cutoff = date(2024, 7, 18)
    ciencia = data_ciencia if isinstance(data_ciencia, date) else None
    if ciencia:
        ints_prev = sorted([d for d in global_marcos if isinstance(d, date) and ciencia <= d <= cutoff])
        start = ciencia
        events_prev = [("Ciência (TCE-RJ)", ciencia, 'tab:blue')]
        for dmar in ints_prev:
            if dmar >= start:
                start = dmar
                events_prev.append(("Marco geral", dmar, 'tab:orange'))
        data_prelaw = start + relativedelta(years=5)
        color_end = 'tab:red' if data_prelaw <= cutoff else 'tab:gray'
        events_prev.append(("Consumação (reg. anterior)", data_prelaw, color_end))
        _render_timeline_html("Regime anterior (até 18/07/2024)", events_prev)

    # --- Regime aplicável (global + subjetivos do gestor selecionado) ---
    # Reaproveita o motor de cálculo para pegar prazo e marcos considerados
    res_demo = calcular_por_gestor(
        nome_gestor=g_select,
        enquadramento=enquadramento,
        termo_inicial_fato=termo_inicial_fato,
        data_ciencia=data_ciencia,
        global_marcos=global_marcos,
        subj_marcos=subj_list,
        aplicar_prazo_penal=aplicar_prazo_penal,
        prazo_penal_anos=prazo_penal_anos,
        check_intercorrente=False,
        data_ultimo_ato=None,
        idata_subseq=None
    )
    _termo = res_demo.get('termo_inicial')
    _prazo = res_demo.get('prazo_final')
    _ints = res_demo.get('interrupcoes', [])
    if isinstance(_termo, date) and isinstance(_prazo, date):
        events_now = [("Termo inicial (cálculo)", _termo, 'tab:blue')]
        for dmar in _ints:
            events_now.append(("Marco (geral/subjetivo)", dmar, 'tab:orange'))
        color_end_now = '#D93025' if (res_demo.get('sit','').lower().startswith('prescrição')) else '#1A73E8'
        events_now.append(("Data atual de prescrição", _prazo, color_end_now))
        _render_timeline_html(f"{enquadramento} — {g_select}", events_now)

st.markdown("---")
st.caption(
    "Observações: (i) Interrupções gerais (+ chamamentos do gestor) reiniciam a contagem; "
    "(ii) intercorrente (§1º): paralisação > 3 anos; "
    "(iii) fatos < 18/07/2021: termo = ciência (TCE-RJ); "
    "(iv) fatos ≥ 18/07/2021: termo = fato/cessação; "
    "(v) na ressarcitória (analogia), registre a motivação do termo."
)
