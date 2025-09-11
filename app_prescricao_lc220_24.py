import streamlit as st
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import time

st.set_page_config(page_title="Prescrição — LC‑RJ 63/1990 (art. 5º‑A)", layout="wide")
st.markdown("<style>.block-container {max-width:780px; padding-left:12px; padding-right:12px;}</style>", unsafe_allow_html=True)

# =============================
# Cabeçalho
# =============================
st.title("Calculadora de Prescrição — LC‑RJ 63/1990 (art. 5º‑A)")
st.caption("Ferramenta de apoio. Ajuste as premissas ao caso concreto e registre a motivação no parecer.")

# =============================
# 1) Natureza e dados básicos
# =============================
colA, colB, colC = st.columns([1.2, 1, 1])
with colA:
    natureza = st.selectbox(
        "Natureza da pretensão",
        ["Punitiva", "Ressarcitória (analogia)"],
        help="""O app sugere com base nas datas e nos marcos.
No teste de **prescrição consumada antes da lei (até 18/07/2024)**, considera-se, em regra, a **data de autuação** como data de **ciência pelo TCE-RJ**; se houver ciência anterior, ajuste pelos **marcos interruptivos** (por analogia) informados acima.""",
)
with colB:
    conduta = st.selectbox(
        "Tipo de conduta",
        ["Instantânea", "Continuada"],
        help=(
            "Instantânea: ato isolado em uma data. Continuada: efeitos que perduram (ex.: execução contratual com pagamentos)."
        ),
    )
with colC:
    data_autuacao = st.date_input(
        "Data de autuação no TCE‑RJ",
        value=date.today(),
        help="Data em que o processo foi autuado/cadastrado no Tribunal.",
    )

# Termo inicial: varia conforme natureza e escolha do usuário
st.subheader("Termo inicial")
if natureza == "Punitiva":
    data_ato = st.date_input(
        "Data do ato (ou da cessação, se continuada)",
        value=date.today(),
        help=(
            "Para punitiva: art. 5º‑A (LC‑RJ 63/1990) adota a data do ato; se a conduta for continuada, considere a cessação."
        ),
    )
    termo_inicial = data_ato
    termo_inicial_label = "Data do ato/cessação (punitiva)"
else:
    st.markdown(
        "Defina o termo inicial **motivado**. "
        "Selecione a base e informe a data correspondente."
    )
    base_ress = st.radio(
        "Como fixar o termo inicial (ressarcitória)?",
        [
            "Evento danoso (data do dano)",
            "Última medição/pagamento (contratos)",
            "Cessação do dano (se continuada)",
        ],
        help="O app usa a data escolhida como termo inicial para fins de cálculo.",
    )
    if base_ress == "Evento danoso (data do dano)":
        data_base = st.date_input("Data do evento danoso", value=date.today())
    elif base_ress == "Última medição/pagamento (contratos)":
        data_base = st.date_input(
            "Data da última medição/pagamento ligada ao sobrepreço/irregularidade", value=date.today()
        )
    else:
        data_base = st.date_input("Data de cessação do dano", value=date.today())
    termo_inicial = data_base
    termo_inicial_label = f"{base_ress}"

colD, colE, colF = st.columns(3)
with colD:
    transitou_pre_lc = st.selectbox(
        "Decisão adm. transitada em julgado antes de 18/07/2024?",
        ["Não", "Sim"],
        help="Se 'Sim', a LC‑RJ 220/2024 não alcança a decisão já transitada.",
    )
with colE:
    aplicar_prazo_penal = st.selectbox(
        "Fato também é crime? (aplicar prazo penal)",
        ["Não", "Sim"],
        help="Se houver tipificação penal, prevalece o prazo penal.",
    )
with colF:
    prazo_penal_anos = None
    if aplicar_prazo_penal == "Sim":
        prazo_penal_anos = st.number_input(
            "Prazo penal (anos)", min_value=1, max_value=40, value=8, step=1, help="Informe o prazo prescricional penal aplicável ao tipo."
        )

# =============================
# 2) Enquadramento intertemporal
# =============================
st.subheader("Enquadramento intertemporal")
# Será sugerido automaticamente após a escolha dos marcos interruptivos (teste pré-lei usa a data de autuação como ciência).

# =============================
# 3) Marcos interruptivos (§3º) — UI dinâmica com calendário
# =============================
st.subheader("Marcos interruptivos (§ 3º)")
st.caption(
    "Use o **checkbox** se não houve interrupção. Caso contrário, adicione as **datas** (calendário) e, se precisar, clique em **+ Adicionar data**."
)

# Estado inicial dos widgets dinâmicos
def _init_interruptions_state():
    if "marco_count" not in st.session_state:
        st.session_state.marco_count = 1
    if "marco_dates" not in st.session_state:
        st.session_state.marco_dates = [None]

_init_interruptions_state()

colNI, colBtns = st.columns([1, 1])
with colNI:
    no_interruptions = st.checkbox(
        "Não houve marco interruptivo",
        value=False,
        help="Marque se não houve citação/notificação, ato inequívoco de apuração, decisão condenatória recorrível ou tentativa conciliatória."
    )

status_ph = st.empty()
interrupcoes = []

if not no_interruptions:
    # Renderiza inputs de datas conforme a contagem atual
    for i in range(st.session_state.marco_count):
        default_val = st.session_state.marco_dates[i] or date.today()
        picked = st.date_input(
            f"Data do marco #{i+1}",
            value=default_val,
            key=f"marco_{i}",
            help="Citação/notificação; ato inequívoco de apuração; decisão condenatória recorrível; tentativa conciliatória.",
        )
        st.session_state.marco_dates[i] = picked

    with colBtns:
        colAdd, colRem, colClr = st.columns([1, 1, 1])
        if colAdd.button("➕ Adicionar data", use_container_width=True):
            status_ph.info("Adicionando campo de data…")
            st.session_state.marco_count += 1
            st.session_state.marco_dates.append(None)
            time.sleep(0.2)
            status_ph.empty()
            st.rerun()
        if colRem.button("➖ Remover última", disabled=st.session_state.marco_count <= 1, use_container_width=True):
            status_ph.info("Removendo…")
            if st.session_state.marco_count > 1:
                st.session_state.marco_count -= 1
                st.session_state.marco_dates = st.session_state.marco_dates[: st.session_state.marco_count]
            time.sleep(0.2)
            status_ph.empty()
            st.rerun()
        if colClr.button("🗑️ Limpar todas", use_container_width=True):
            status_ph.info("Limpando…")
            st.session_state.marco_count = 1
            st.session_state.marco_dates = [None]
            time.sleep(0.2)
            status_ph.empty()
            st.rerun()

    # Coleta as datas válidas
    interrupcoes = [d for d in st.session_state.marco_dates if isinstance(d, date)]
else:
    # Sem marcos interruptivos
    interrupcoes = []

# === Enquadramento (cálculo automático com base nos marcos) ===
from datetime import date as _date_for_prevcheck

def _is_prescribed_before_law(ciencia_autuacao: _date_for_prevcheck, interrupcoes: list[_date_for_prevcheck]) -> bool:
    """Verifica prescrição consumada até 18/07/2024 segundo o regime anterior (quinquênio),
    usando, como regra, a data de autuação como data de ciência, com interrupções por analogia até o cutoff."""
    cutoff = _date_for_prevcheck(2024, 7, 18)
    if not isinstance(ciencia_autuacao, _date_for_prevcheck):
        return False
    ints_prev = sorted([d for d in interrupcoes if isinstance(d, _date_for_prevcheck) and ciencia_autuacao <= d <= cutoff])
    start = ciencia_autuacao
    for d in ints_prev:
        if d >= start:
            start = d
    return start + relativedelta(years=5) <= cutoff

def _prelaw_prescription_date(ciencia_autuacao: _date_for_prevcheck, interrupcoes: list[_date_for_prevcheck]) -> _date_for_prevcheck | None:
    """Calcula a data de consumação da prescrição no regime anterior (quinquênio),
    considerando ciência = autuação e interrupções até 18/07/2024."""
    cutoff = _date_for_prevcheck(2024, 7, 18)
    if not isinstance(ciencia_autuacao, _date_for_prevcheck):
        return None
    ints_prev = sorted([d for d in interrupcoes if isinstance(d, _date_for_prevcheck) and ciencia_autuacao <= d <= cutoff])
    start = ciencia_autuacao
    for d in ints_prev:
        if d >= start:
            start = d
    return start + relativedelta(years=5)

presc_antes_lei_auto = _is_prescribed_before_law(data_autuacao, interrupcoes)

sugerido = "Novo regime (art. 5º‑A)"
if transitou_pre_lc == "Sim":
    sugerido = "Fora do alcance: decisão anterior a 18/07/2024"
elif presc_antes_lei_auto:
    sugerido = "Prescrição consumada antes da lei"
elif termo_inicial < date(2021, 7, 18):
    sugerido = "Transição 2 anos (LC 220/24)"
else:
    sugerido = "Novo regime (art. 5º‑A)"

enquadramento = st.selectbox(
    "Selecione o enquadramento (ajuste se necessário)",
    [
        "Novo regime (art. 5º‑A)",
        "Transição 2 anos (LC 220/24)",
        "Prescrição consumada antes da lei",
        "Fora do alcance: decisão anterior a 18/07/2024",
    ],
    index=[
        "Novo regime (art. 5º‑A)",
        "Transição 2 anos (LC 220/24)",
        "Prescrição consumada antes da lei",
        "Fora do alcance: decisão anterior a 18/07/2024",
    ].index(sugerido),
    help="""O app sugere com base nas datas e nos marcos.
No teste de **prescrição consumada antes da lei (até 18/07/2024)**, considera-se, em regra, a **data de autuação** como data de **ciência pelo TCE-RJ**; se houver ciência anterior, ajuste pelos **marcos interruptivos** (por analogia) informados acima.""",
)


# =============================
# 4) Intercorrente (§1º)
# =============================
st.subheader("Prescrição intercorrente (§ 1º)")
st.caption("Configura-se com **paralisação > 3 anos** sem julgamento ou despacho.")
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
# 5) Cálculo
# =============================
def compute_deadline(data_inicio: date, interrupcoes: list[date], base_anos: int) -> tuple[date, bool]:
    """Retorna (data_final, houve_interrupcao_valida). Ignora marcos anteriores ao termo inicial."""
    ints = sorted([d for d in interrupcoes if d and d >= data_inicio])
    start = data_inicio
    for d in ints:
        if d >= start:
            start = d  # reinicia a contagem a partir do marco
    return start + relativedelta(years=base_anos), (len(ints) > 0)

resultado: dict = {}
auto_option = None
option_text = None

if enquadramento == "Fora do alcance: decisão anterior a 18/07/2024":
    resultado["sit"] = "Fora do alcance da LC‑RJ 220/2024"
    resultado["detalhe"] = "Decisão administrativa transitada em julgado anterior a 18/07/2024."
elif enquadramento == "Prescrição consumada antes da lei":
    cutoff = date(2024, 7, 18)
    ciencia = data_autuacao if isinstance(data_autuacao, date) else None
    data_prelaw = _prelaw_prescription_date(ciencia, interrupcoes)

    resultado["sit"] = "Prescrição reconhecida (regime anterior)"
    if isinstance(data_prelaw, date):
        resultado["detalhe"] = (
            f"Com base nos dados inseridos, a prescrição consumou-se em {data_prelaw.strftime('%d/%m/%Y')}, antes de 18/07/2024."
        )
    else:
        resultado["detalhe"] = (
            "Com base nos dados inseridos, a prescrição consumou-se integralmente antes de 18/07/2024 (regime anterior)."
        )

    auto_option = "B"
    if isinstance(data_prelaw, date):
        option_text = (
            "Com base nos dados inseridos (considerando a autuação como ciência e os marcos interruptivos informados), "
            f"a prescrição consumou-se em {data_prelaw.strftime('%d/%m/%Y')}, antes de 18/07/2024, "
            "impondo o reconhecimento da prescrição por segurança jurídica e irretroatividade da nova lei."
        )
    else:
        option_text = (
            "Com base nos dados inseridos, a prescrição consumou-se integralmente antes de 18/07/2024, sob o regime então vigente, "
            "impondo o reconhecimento da prescrição por segurança jurídica e irretroatividade da nova lei."
        )

    # Preencher campos para o cartão de resultado
    resultado["termo_inicial"] = ciencia
    resultado["termo_inicial_label"] = "Ciência (autuação) — regime anterior"
    resultado["base"] = "quinquenal (regime anterior)"
    resultado["prazo_final"] = data_prelaw
    resultado["interrupcoes"] = sorted([d for d in interrupcoes if isinstance(d, date) and d <= cutoff])
else:
    # Base de anos (penal prevalece)
    if aplicar_prazo_penal == "Sim" and prazo_penal_anos:
        base_anos = prazo_penal_anos
        base_label = f"prazo penal ({prazo_penal_anos} anos)"
    else:
        base_anos = 5 if enquadramento == "Novo regime (art. 5º‑A)" else 2
        base_label = "quinquenal" if base_anos == 5 else "bienal (transição)"

    # Termo inicial efetivo (transição conta de 18/07/2024)
    termo_inicial_efetivo = termo_inicial if enquadramento == "Novo regime (art. 5º‑A)" else date(2024, 7, 18)

    prazo_final, has_valid_interruptions = compute_deadline(termo_inicial_efetivo, interrupcoes, base_anos)

    # Intercorrente
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
        auto_option = "E"
        de = data_ultimo_ato.strftime("%d/%m/%Y") if data_ultimo_ato else "N/A"
        ate = (idata_subseq or date.today()).strftime("%d/%m/%Y")
        option_text = (
            f"Verificada paralisação processual por período superior a 3 anos (de {de} a {ate}), "
            "reconhece-se a prescrição intercorrente, com arquivamento, sem prejuízo de apuração funcional."
        )
    else:
        if hoje >= prazo_final:
            resultado["sit"] = "Prescrição consumada"
            resultado["detalhe"] = f"Esgotado o prazo {base_label}: {prazo_final.strftime('%d/%m/%Y')}."
            if (
                enquadramento == "Transição 2 anos (LC 220/24)"
                and prazo_final == date(2026, 7, 18)
                and not has_valid_interruptions
            ):
                auto_option = "C"
                option_text = (
                    "Tratando-se de ato anterior a 18/07/2021 e não prescrita a pretensão até 18/07/2024, "
                    "aplica-se o prazo bienal de transição. Inexistentes marcos interruptivos hábeis, "
                    "consumou-se a prescrição em 18/07/2026."
                )
            elif enquadramento == "Novo regime (art. 5º‑A)" and not has_valid_interruptions:
                auto_option = "D"
                option_text = (
                    f"Enquadrado no novo regime, escoado o prazo quinquenal contado de "
                    f"{termo_inicial.strftime('%d/%m/%Y')}, "
                    "sem marcos interruptivos válidos, impõe-se o reconhecimento da prescrição."
                )
        else:
            resultado["sit"] = "Não prescrito"
            resultado["detalhe"] = f"Data-alvo projetada ({base_label}): {prazo_final.strftime('%d/%m/%Y')}."
            auto_option = "A"
            mi_text = (
                f"dos marcos interruptivos em [{interrupcoes_str}]" if interrupcoes_consideradas else "sem marcos interruptivos identificados"
            )
            option_text = (
                f"À vista do termo inicial em "
                f"{(termo_inicial if enquadramento=='Novo regime (art. 5º‑A)' else date(2024,7,18)).strftime('%d/%m/%Y')}, "
                f"{mi_text} e da ausência de paralisação superior a 3 anos, "
                "não se verifica prescrição, devendo o feito prosseguir para exame de mérito."
            )

    # Extras
    resultado["natureza"] = natureza
    resultado["conduta"] = conduta
    resultado["termo_inicial"] = termo_inicial_efetivo
    resultado["termo_inicial_label"] = (
        "Transição (18/07/2024)" if enquadramento != "Novo regime (art. 5º‑A)" else "Termo inicial informado"
    )
    resultado["prazo_final"] = prazo_final if "prazo_final" in locals() else None
    resultado["base"] = base_label if "base_label" in locals() else None
    resultado["interrupcoes"] = interrupcoes_consideradas

# =============================
# 6) Saída e texto para o parecer
# =============================
st.markdown("### Resultado")

# Bloco visual único para facilitar print e colagem em Word
# (cores condicionais, destaque em vermelho para situações de prescrição)
_sit = resultado.get('sit', '—')

def _color_for_status(s: str) -> str:
    s = (s or '').lower()
    if 'prescrição consumada' in s or 'intercorrente' in s or 'prescrição reconhecida' in s:
        return '#D93025'  # vermelho
    elif 'não prescrito' in s:
        return '#1E8E3E'  # verde
    else:
        return '#1A73E8'  # azul

_status_color = _color_for_status(_sit)

_termo_inicial = resultado.get('termo_inicial')
_prazo_final = resultado.get('prazo_final')
_interrupcoes = resultado.get('interrupcoes', [])
_interrupcoes_str = ", ".join([d.strftime('%d/%m/%Y') for d in _interrupcoes]) if _interrupcoes else '—'

_html = f"""
<div style='border:1px solid {_status_color}; padding:16px; border-radius:12px; margin-bottom:8px;'>
  <div style='font-weight:700; font-size:1.1rem; color:{_status_color};'>Situação: {resultado.get('sit','—')}</div>
  <div style='margin-top:6px;'>{resultado.get('detalhe','—')}</div>
  <hr style='border:none; border-top:1px dashed #ddd; margin:12px 0;'>
  <div style='display:grid; grid-template-columns: 1fr 1fr; gap:8px;'>
    <div><b>Enquadramento:</b> {enquadramento}</div>
    <div><b>Base:</b> {resultado.get('base','—')}</div>
    <div><b>Natureza:</b> {resultado.get('natureza','—')}</div>
    <div><b>Conduta:</b> {resultado.get('conduta','—')}</div>
    <div><b>Termo inicial:</b> {(_termo_inicial.strftime('%d/%m/%Y') if isinstance(_termo_inicial, date) else '—')} ({resultado.get('termo_inicial_label','')})</div>
    <div><b>Data atual de prescrição:</b> {(_prazo_final.strftime('%d/%m/%Y') if isinstance(_prazo_final, date) else '—')}</div>
    <div style='grid-column: 1 / -1;'><b>Interrupções consideradas:</b> {_interrupcoes_str}</div>
  </div>
  {f"<div style='margin-top:12px; padding:12px; background:#fff5f5; border-left:4px solid {_status_color}; border-radius:8px;'><div style='font-weight:600;'>Conclusão sugerida:</div><div>{option_text}</div></div>" if option_text else ""}
  <div style='margin-top:12px; font-size:0.9rem; color:#666; text-align:right;'>Calculadora de Prescrição da SGE</div>
</div>
"""

st.markdown(_html, unsafe_allow_html=True)

# ===== Linha do tempo (opcional) =====
show_timeline = st.checkbox(
    "Mostrar linha do tempo (regime anterior e regime aplicável)", value=False,
    help=(
        "Visualização dos marcos ao longo do tempo. No regime anterior, considera-se, em regra, a autuação como ciência; "
        "marcos até 18/07/2024 reiniciam o quinquênio. No regime aplicável, usa-se o termo inicial efetivo, marcos válidos e a data atual de prescrição."
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

if show_timeline:
    # --- Regime anterior ---
    cutoff = date(2024, 7, 18)
    ciencia = data_autuacao if isinstance(data_autuacao, date) else None
    if ciencia:
        ints_prev = sorted([d for d in interrupcoes if isinstance(d, date) and ciencia <= d <= cutoff])
        start = ciencia
        events_prev = [("Ciência (autuação)", ciencia, 'tab:blue')]
        for dmar in ints_prev:
            if dmar >= start:
                start = dmar
                events_prev.append(("Marco interruptivo", dmar, 'tab:orange'))
        data_prelaw = start + relativedelta(years=5)
        color_end = 'tab:red' if data_prelaw <= cutoff else 'tab:gray'
        events_prev.append(("Consumação (reg. anterior)", data_prelaw, color_end))
        _render_timeline_html("Regime anterior (até 18/07/2024)", events_prev)

    # --- Regime aplicável (novo/transição) ---
    _termo = resultado.get('termo_inicial') if isinstance(resultado.get('termo_inicial'), date) else None
    _prazo = resultado.get('prazo_final') if isinstance(resultado.get('prazo_final'), date) else None
    _ints = resultado.get('interrupcoes', [])
    if _termo and _prazo:
        events_now = [("Termo inicial", _termo, 'tab:blue')]
        for dmar in _ints:
            events_now.append(("Marco interruptivo", dmar, 'tab:orange'))
        color_end_now = '#D93025' if (resultado.get('sit','').lower().startswith('prescrição')) else '#1A73E8'
        events_now.append(("Data atual de prescrição", _prazo, color_end_now))
        _render_timeline_html(f"{enquadramento}", events_now)

st.markdown("---")


st.caption(
    "Observações: (i) Interrupções (§3º) reiniciam a contagem; (ii) intercorrente (§1º): paralisação > 3 anos; "
    "(iii) se houver crime, prevalece o prazo penal; (iv) na ressarcitória, registre a motivação do termo inicial (evento danoso/último pagamento/cessação)."
)
