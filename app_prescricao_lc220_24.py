# app_prescricao_lc220_24.py
import streamlit as st
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from datetime import date as _date_for_prevcheck
import pandas as pd
from io import BytesIO
import re
import zipfile

st.set_page_config(page_title="Prescrição — LC-RJ 63/1990 (art. 5º-A)", layout="wide")
st.markdown("<style>.block-container {max-width:980px; padding-left:12px; padding-right:12px;}</style>", unsafe_allow_html=True)

# ======================================================================================
# Utilitário: gerar DOCX do Roteiro Oficial (sem dependências externas)
# ======================================================================================
def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))

def _build_document_xml(sections):
    def para(text, is_heading=False):
        t = _xml_escape(text)
        if is_heading:
            return f"<w:p><w:r><w:rPr><w:b/><w:sz w:val='28'/></w:rPr><w:t xml:space='preserve'>{t}</w:t></w:r></w:p>"
        else:
            return f"<w:p><w:r><w:t xml:space='preserve'>{t}</w:t></w:r></w:p>"

    body = []
    for text, is_heading in sections:
        body.append(para(text, is_heading))
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:w10="urn:schemas-microsoft-com:office:word" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
        'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
        'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
        'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14">'
        '<w:body>' + "".join(body) +
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
        '</w:body></w:document>'
    )
    return xml

def build_roteiro_docx_bytes() -> bytes:
    sections = [
        ("ROTEIRO OFICIAL — Calculadora de Prescrição (LC-RJ 63/1990, art. 5º-A)", True),
        ("1) Finalidade", True),
        ("Padronizar a aplicação do art. 5º-A (LCE 63/1990) com a chave intertemporal consolidada pelo Plenário: "
         "fatos ≥ 18/07/2021 → novo regime (5 anos do fato/cessação); fatos < 18/07/2021 → teste pré-lei e, não consumando até 18/07/2024, transição bienal (18/07/2024 → 18/07/2026).", False),

        ("2) Chave intertemporal — visão executiva", True),
        ("• Fatos ≥ 18/07/2021 → Novo regime (5 anos do fato/cessação).", False),
        ("• Fatos < 18/07/2021 → faça o TESTE PRÉ-LEI: projete 5 anos da ciência (em regra, autuação) com marcos até 18/07/2024. "
         "Se consumou até 18/07/2024 → reconheça prescrição antes da lei. Se NÃO consumou → Transição (18/07/2024 → 18/07/2026), independentemente de a ciência ser posterior.", False),
        ("• Decisão administrativa transitada até 18/07/2024 → fora do alcance da LCE 220/2024.", False),

        ("3) Marcos interruptivos", True),
        ("• Teste pré-lei: apenas marcos entre a ciência e 18/07/2024 (reiniciam o quinquênio do regime anterior).", False),
        ("• Transição: apenas marcos a partir de 18/07/2024.", False),
        ("• Novo regime: marcos a partir do fato/cessação.", False),
        ("• Qualificação: chamamento qualificado é subjetivo e retroage à decisão que o determinou; simples protocolo de TCE não interrompe.", False),

        ("4) Intercorrente e prazo penal", True),
        ("• Intercorrente: paralisação > 3 anos sem julgamento/despacho (art. 5º-A, §1º).", False),
        ("• Prazo penal: prevalece sobre o administrativo quando cabível (art. 5º-A, §2º).", False),

        ("5) Passo a passo no aplicativo", True),
        ("1. Preencha natureza, conduta, data do fato/cessação (ou base motivada na ressarcitória), autuação e ciência (se diversa).", False),
        ("2. Informe os marcos gerais (valem para todos) e, por gestor, os chamamentos qualificados (efeito subjetivo).", False),
        ("3. O app sugere o enquadramento: novo regime / transição / prescrição antes da lei / fora do alcance. Ajuste se necessário.", False),
        ("4. Se habilitar intercorrente, informe último ato e termo final (ou use hoje).", False),
        ("5. Verifique os cartões por gestor e exporte o Excel (Resumo + abas auxiliares).", False),
        ("6) ÍNDICE DE VÍDEOS", True),

        ("01_Novo_Regime_FatoRecente.mp4", True),
        ("Objetivo: Demonstrar fato ≥ 18/07/2021 com contagem quinquenal a partir do fato/cessação.", False),
        ("Inputs-chave: Punitiva; Ato 03/11/2021; Autuação/Ciência 12/12/2024; sem marcos; sem intercorrente.", False),
        ("Resultado esperado: Enquadramento 'Novo regime (art. 5º-A)'; prazo final 03/11/2026.", False),

        ("02_Transicao_CienciaPosterior.mp4", True),
        ("Objetivo: Fato anterior a 18/07/2021 com ciência posterior à lei (aplica transição bienal).", False),
        ("Inputs-chave: Punitiva; Ato 15/06/2016; Ciência 12/12/2024; sem marcos.", False),
        ("Resultado esperado: 'Transição 2 anos (LC 220/24)'; vence 18/07/2026.", False),

        ("03_Prescricao_AntesDaLei.mp4", True),
        ("Objetivo: Reconhecimento de prescrição pré-lei pelo quinquênio da ciência.", False),
        ("Inputs-chave: Ato 10/05/2015; Ciência 10/06/2017; sem marcos até 18/07/2024.", False),
        ("Resultado esperado: 'Prescrição reconhecida (regime anterior)'.", False),

        ("04_Transicao_MarcoGeral.mp4", True),
        ("Objetivo: Mostrar reinício do bienal por ato inequívoco de apuração pós-lei.", False),
        ("Inputs-chave: Ato 20/02/2017; Ciência 01/08/2024; Marco geral 10/09/2025.", False),
        ("Resultado esperado: Novo vencimento 10/09/2027.", False),

        ("05_Transicao_Chamamento_Subjetivo.mp4", True),
        ("Objetivo: Efeito subjetivo do chamamento qualificado (multi-gestores).", False),
        ("Inputs-chave: Fato 2016; Ciência 2024; Gestor A com chamamento 20/06/2026 (decisão em 05/05/2026); Gestor B sem chamamento.", False),
        ("Resultado esperado: Gestor A vence 05/05/2028 (retroação à decisão); Gestor B vence 18/07/2026.", False),

        ("06_Intercorrente.mp4", True),
        ("Objetivo: Prescrição intercorrente (> 3 anos) durante a tramitação.", False),
        ("Inputs-chave: Novo regime; último ato 01/08/2021; ato subsequente 05/09/2024.", False),
        ("Resultado esperado: 'Prescrição intercorrente'.", False),

        ("07_Continuada_Cessacao.mp4", True),
        ("Objetivo: Conduta continuada (termo na cessação).", False),
        ("Inputs-chave: Cessação 31/12/2022; sem marcos; sem intercorrente.", False),
        ("Resultado esperado: Novo regime; prazo final 31/12/2027.", False),

        ("08_Ressarcitoria_UltimaMedicao.mp4", True),
        ("Objetivo: Ressarcitória (analogia) com base 'última medição/pagamento'.", False),
        ("Inputs-chave: Última medição 30/03/2019; ciência 2024; sem marcos.", False),
        ("Resultado esperado: Transição; vence 18/07/2026 (salvo marcos pós-lei).", False),

        ("09_PrazoPenal.mp4", True),
        ("Objetivo: Prevalência do prazo penal (§2º).", False),
        ("Inputs-chave: Ato 10/10/2022; 'Fato também é crime: Sim'; Prazo penal 8 anos.", False),
        ("Resultado esperado: Base = penal (8 anos); vencimento 10/10/2030.", False),

        ("10_Ciencia_Apos_18072026.mp4", True),
        ("Objetivo: Ciência apenas após 18/07/2026 em caso de transição (sem marcos).", False),
        ("Inputs-chave: Fato 2017; Ciência 01/08/2026; sem marcos.", False),
        ("Resultado esperado: Prescrição consumada em 18/07/2026 (ciência tardia não reabre).", False),

        ("11_Multigestores_ExportacaoExcel.mp4", True),
        ("Objetivo: Preencher vários gestores, com marcos gerais e chamamentos específicos, e exportar o Excel.", False),
        ("Inputs-chave: Fato 2016; Marco geral 01/03/2025; Chamamento só do Gestor B 15/05/2025.", False),
        ("Resultado esperado: Planilha com Resumo e abas auxiliares; prazos distintos por gestor.", False),
    
        ]
    document_xml = _build_document_xml(sections)
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )
    word_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.microsoft.com/office/2006/relationships"/>'
    )
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types_xml)
        z.writestr('_rels/.rels', rels_xml)
        z.writestr('word/document.xml', document_xml)
        z.writestr('word/_rels/document.xml.rels', word_rels_xml)
    return buf.getvalue()

# ======================================================================================
# Cabeçalho + botão de download do Roteiro (DOCX)
# ======================================================================================
st.title("Calculadora de Prescrição — LC-RJ 63/1990 (art. 5º-A)")
st.caption("Ferramenta de apoio. Ajuste as premissas ao caso concreto.")

with st.expander("📘 Roteiro Oficial — ver/baixar", expanded=False):
    st.markdown("O Roteiro Oficial consolida as regras, a chave intertemporal e exemplos de uso.")
    roteiro_bytes = build_roteiro_docx_bytes()
    st.download_button(
        "⬇️ Baixar Roteiro Oficial (DOCX)",
        data=roteiro_bytes,
        file_name="Roteiro_Oficial_Calculadora_Prescricao.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True
    )

# ======================================================================================
# 1) Natureza e dados básicos
# ======================================================================================
colA, colB, colC = st.columns([1.2, 1, 1])
with colA:
    natureza = st.selectbox(
        "Natureza da pretensão",
        ["Punitiva", "Ressarcitória (analogia)"],
        help=("Selecione Punitiva (ex.: multa) ou Ressarcitória (analogia). "
              "A LCE 220/2024 (art. 5º-A) rege a prescrição no TCE-RJ, aplicando-se por consolidação também por analogia à ressarcitória."),
    )
with colB:
    conduta = st.selectbox(
        "Tipo de conduta",
        ["Instantânea", "Continuada"],
        help="Instantânea: ato único. Continuada: efeitos que perduram (use a data de cessação).",
    )
with colC:
    data_autuacao = st.date_input(
        "Data de autuação no TCE-RJ",
        value=date.today(),
        help="Em regra, funciona como ciência institucional quando não houver prova de ciência diversa.",
    )

data_ciencia = st.date_input(
    "Data de ciência pelo TCE-RJ (se diversa da autuação)",
    value=data_autuacao,
    help=("Para fatos anteriores a 18/07/2021, a prescrição do regime anterior corre da ciência pelo TCE-RJ "
          "(paradigma histórico: autuação, salvo prova de ciência anterior)."),
)

# Termo material (fato/cessação ou base ressarcitória)
st.subheader("Termo inicial material (fato/evento)")
if natureza == "Punitiva":
    data_ato = st.date_input(
        "Data do ato (ou da cessação, se continuada)",
        value=date.today(),
        help=("No novo regime (art. 5º-A), o termo é o fato/cessação. "
              "Também aciona a chave intertemporal: < 18/07/2021 (passivo antigo); ≥ 18/07/2021 (novo regime)."),
    )
    termo_inicial_fato = data_ato
    termo_inicial_fato_label = "Data do ato/cessação (punitiva)"
else:
    st.markdown("**Ressarcitória (analogia)** — motive a base do termo inicial.")
    base_ress = st.radio(
        "Base do termo (ressarcitória)",
        ["Evento danoso (data do dano)", "Última medição/pagamento (contratos)", "Cessação do dano (se continuada)"],
        help="A base escolhida deve ser fundamentada no parecer.",
    )
    if base_ress == "Evento danoso (data do dano)":
        data_base = st.date_input("Data do evento danoso", value=date.today())
    elif base_ress == "Última medição/pagamento (contratos)":
        data_base = st.date_input("Data da última medição/pagamento ligada ao sobrepreço/irregularidade", value=date.today())
    else:
        data_base = st.date_input("Data de cessação do dano", value=date.today())
    termo_inicial_fato = data_base
    termo_inicial_fato_label = base_ress

colD, colE, colF = st.columns(3)
with colD:
    transitou_pre_lc = st.selectbox(
        "Decisão adm. transitada em julgado antes de 18/07/2024?",
        ["Não", "Sim"],
        help="Se 'Sim', a LCE 220/2024 não alcança (ato findo).",
    )
with colE:
    aplicar_prazo_penal = st.selectbox(
        "Fato também é crime? (aplica prazo penal)",
        ["Não", "Sim"],
        help="Se houver tipificação penal aplicável, prevalece o prazo penal (art. 5º-A, § 2º).",
    )
with colF:
    prazo_penal_anos = None
    if aplicar_prazo_penal == "Sim":
        prazo_penal_anos = st.number_input("Prazo penal (anos)", min_value=1, max_value=40, value=8, step=1)

# ======================================================================================
# 2) Funções auxiliares — teste pré-lei e deadline
# ======================================================================================
def _prelaw_consumou_ate_cutoff(ciencia: _date_for_prevcheck, marcos: list[_date_for_prevcheck]) -> bool:
    """Verifica se o quinquênio do regime anterior (ciência) consumou até 18/07/2024,
    considerando apenas marcos entre ciência e cutoff."""
    cutoff = _date_for_prevcheck(2024, 7, 18)
    if not isinstance(ciencia, _date_for_prevcheck):
        return False
    ints_prev = sorted([d for d in marcos if isinstance(d, _date_for_prevcheck) and ciencia <= d <= cutoff])
    start = ciencia
    for d in ints_prev:
        if d >= start:
            start = d
    return start + relativedelta(years=5) <= cutoff

def compute_deadline(data_inicio: date, interrupcoes: list[date], base_anos: int) -> tuple[date, bool]:
    """Retorna (data_final, houve_interrupcao_valida). Ignora marcos anteriores ao termo inicial."""
    ints = sorted([d for d in interrupcoes if d and d >= data_inicio])
    start = data_inicio
    for d in ints:
        if d >= start:
            start = d  # reinicia a contagem a partir do marco
    return start + relativedelta(years=base_anos), (len(ints) > 0)

# ======================================================================================
# 3) Marcos interruptivos — gerais x subjetivos
# ======================================================================================
st.subheader("Marcos interruptivos")
st.caption(
    "Marcos gerais (objetivos, valem para todos): p.ex., determinação formal de auditoria/instauração de TCE/TOF, decisão condenatória recorrível, tentativa de conciliação. "
    "Simples protocolo não interrompe.\n"
    "Marcos subjetivos (por gestor): chamamento qualificado (efeito subjetivo; retroação à decisão que o determinou)."
)

# Marcos gerais
st.markdown("#### Marcos gerais (valem para todos)")
def _init_global_state():
    if "g_marco_count" not in st.session_state:
        st.session_state.g_marco_count = 1
    if "g_marco_dates" not in st.session_state:
        st.session_state.g_marco_dates = [None]
_init_global_state()

no_global_inter = st.checkbox("Não houve marco geral", value=False)
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
    colA1, colA2, colA3 = st.columns(3)
    colA1.button("➕ Adicionar marco geral", use_container_width=True, on_click=_g_add)
    colA2.button("➖ Remover último", disabled=st.session_state.g_marco_count <= 1, use_container_width=True, on_click=_g_rem)
    colA3.button("🗑️ Limpar todos", use_container_width=True, on_click=_g_clr)
    global_marcos = [d for d in st.session_state.g_marco_dates if isinstance(d, date)]
else:
    global_marcos = []

st.markdown("---")

# Lista de gestores
st.markdown("#### Gestores (um por linha)")
gestores_text = st.text_area(
    "Nomes dos gestores",
    value="Gestor A\nGestor B",
    height=90,
    help="Indique um gestor por linha. Para cada gestor, informe os chamamentos qualificados (efeito subjetivo).",
)
gestores = [g.strip() for g in gestores_text.splitlines() if g.strip()]

# Chamamentos qualificados por gestor
st.markdown("#### Chamamentos qualificados por gestor (efeito subjetivo)")
if "gestor_marcos" not in st.session_state:
    st.session_state.gestor_marcos = {}  # nome -> [dates]
for g in gestores:
    if g not in st.session_state.gestor_marcos:
        st.session_state.gestor_marcos[g] = []

def _ensure_g_state(g):
    cnt_key = f"{g}__cnt"
    if cnt_key not in st.session_state:
        st.session_state[cnt_key] = 1
        st.session_state.gestor_marcos[g] = [None]
    return cnt_key

for g in gestores:
    with st.expander(f"Chamamentos qualificados — {g}", expanded=False):
        cnt_key = _ensure_g_state(g)
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

# ======================================================================================
# 4) Enquadramento intertemporal (global — SUGESTÃO CORRIGIDA)
# ======================================================================================
fatos_pre_2021 = (termo_inicial_fato < date(2021, 7, 18))
cutoff = date(2024, 7, 18)

if transitou_pre_lc == "Sim":
    sugerido = "Fora do alcance: decisão anterior a 18/07/2024"
elif not fatos_pre_2021:
    # Fatos ≥ 18/07/2021 → novo regime (5 anos do fato/cessação), independentemente da data de ciência/autuação
    sugerido = "Novo regime (art. 5º-A)"
else:
    # Fatos < 18/07/2021 → primeiro TESTE PRÉ-LEI: consumou até 18/07/2024 pelo regime anterior (quinquênio da ciência)?
    if _prelaw_consumou_ate_cutoff(data_ciencia, global_marcos):
        sugerido = "Prescrição consumada antes da lei"
    else:
        # NÃO consumou → Transição bienal (18/07/2024 → 18/07/2026), mesmo que a ciência/autuação seja posterior.
        sugerido = "Transição 2 anos (LC 220/24)"

enquadramento = st.selectbox(
    "Selecione o enquadramento (global; ajuste se necessário)",
    [
        "Novo regime (art. 5º-A)",
        "Transição 2 anos (LC 220/24)",
        "Prescrição consumada antes da lei",
        "Fora do alcance: decisão anterior a 18/07/2024",
    ],
    index=[
        "Novo regime (art. 5º-A)",
        "Transição 2 anos (LC 220/24)",
        "Prescrição consumada antes da lei",
        "Fora do alcance: decisão anterior a 18/07/2024",
    ].index(sugerido),
    help=("Chave intertemporal\n"
          "• Fatos < 18/07/2021 → Teste pré-lei: quinquênio da ciência até 18/07/2024; se não consumou, Transição (18/07/2024 → 18/07/2026).\n"
          "• Fatos ≥ 18/07/2021 → Novo regime (5 anos do fato/cessação).\n"
          "• Fora do alcance → decisão adm. transitada até 18/07/2024."),
)

# ======================================================================================
# 5) Prescrição intercorrente (§ 1º)
# ======================================================================================
st.subheader("Prescrição intercorrente (§ 1º)")
st.caption("Paralisação > 3 anos sem julgamento/despacho? Caso positivo, informe as datas.")
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

# ======================================================================================
# 6) Motor de cálculo por gestor
# ======================================================================================
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
    resultado = {}
    # Interrupções a considerar dependem do regime efetivo
    if enquadramento == "Transição 2 anos (LC 220/24)":
        # Apenas marcos a partir de 18/07/2024
        interrupcoes = sorted([d for d in (global_marcos + subj_marcos) if isinstance(d, date) and d >= date(2024, 7, 18)])
    elif enquadramento == "Novo regime (art. 5º-A)":
        # Marcos a partir do fato/cessação
        interrupcoes = sorted([d for d in (global_marcos + subj_marcos) if isinstance(d, date) and d >= termo_inicial_fato])
    else:
        # 'Prescrição consumada antes da lei' não chega aqui; 'Fora do alcance' idem.
        interrupcoes = sorted([d for d in (global_marcos + subj_marcos) if isinstance(d, date)])

    # Prescrição antes da lei — bloco exclusivo
    if enquadramento == "Prescrição consumada antes da lei":
        cutoff = date(2024, 7, 18)
        ciencia = data_ciencia if isinstance(data_ciencia, date) else None
        ints_prev = [d for d in (global_marcos + subj_marcos) if isinstance(d, date) and d <= cutoff and (ciencia is None or d >= ciencia)]

        def _prelaw_date(ciencia, ints):
            if not ciencia:
                return None
            ints_prev_sorted = sorted(ints)
            start = ciencia
            for d in ints_prev_sorted:
                if d >= start:
                    start = d
            return start + relativedelta(years=5)

        data_prelaw = _prelaw_date(ciencia, ints_prev)
        resultado["sit"] = "Prescrição reconhecida (regime anterior)"
        resultado["detalhe"] = (f"Consumação em {data_prelaw.strftime('%d/%m/%Y')} (antes de 18/07/2024)."
                                if isinstance(data_prelaw, date) else
                                "Consumação integral antes de 18/07/2024 (regime anterior).")
        resultado["natureza"] = natureza
        resultado["conduta"] = conduta
        resultado["termo_inicial"] = ciencia
        resultado["termo_inicial_label"] = "Ciência (TCE-RJ) — regime anterior"
        resultado["base"] = "quinquenal (regime anterior)"
        resultado["prazo_final"] = data_prelaw
        resultado["interrupcoes"] = sorted(ints_prev)
        return resultado

    # Base de prazo
    if aplicar_prazo_penal == "Sim" and prazo_penal_anos:
        base_anos = prazo_penal_anos
        base_label = f"prazo penal ({prazo_penal_anos} anos)"
    else:
        if enquadramento == "Novo regime (art. 5º-A)":
            base_anos = 5
            base_label = "quinquenal"
        elif enquadramento == "Transição 2 anos (LC 220/24)":
            base_anos = 2
            base_label = "bienal (transição)"
        else:
            # Não deveria ocorrer aqui, mas deixamos seguro
            base_anos = 5
            base_label = "quinquenal"

    # Termo inicial de cálculo por regime
    if enquadramento == "Novo regime (art. 5º-A)":
        termo_inicial_efetivo = termo_inicial_fato
        termo_inicial_label = "Termo inicial (fato/cessação)"
    elif enquadramento == "Transição 2 anos (LC 220/24)":
        termo_inicial_efetivo = date(2024, 7, 18)
        termo_inicial_label = "Transição (18/07/2024)"
    else:
        # fallback defensivo
        termo_inicial_efetivo = data_ciencia
        termo_inicial_label = "Ciência (TCE-RJ)"

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

    if intercorrente:
        resultado["sit"] = "Prescrição intercorrente"
        resultado["detalhe"] = f"Paralisação superior a 3 anos ({periodo_intercorrente} dias)."
    else:
        if hoje >= prazo_final:
            resultado["sit"] = "Prescrição consumada"
            resultado["detalhe"] = f"Esgotado o prazo {base_label}: {prazo_final.strftime('%d/%m/%Y')}."
        else:
            resultado["sit"] = "Não prescrito"
            resultado["detalhe"] = f"Data-alvo projetada ({base_label}): {prazo_final.strftime('%d/%m/%Y')}."

    resultado["natureza"] = natureza
    resultado["conduta"] = conduta
    resultado["termo_inicial"] = termo_inicial_efetivo
    resultado["termo_inicial_label"] = termo_inicial_label
    resultado["prazo_final"] = prazo_final
    resultado["base"] = base_label
    resultado["interrupcoes"] = interrupcoes_consideradas
    return resultado

# ======================================================================================
# 7) Resultados por gestor
# ======================================================================================
st.markdown("### Resultados por gestor")

def _color_for_status(s: str) -> str:
    s = (s or '').lower()
    if 'prescrição consumada' in s or 'intercorrente' in s or 'prescrição reconhecida' in s:
        return '#D93025'
    elif 'não prescrito' in s:
        return '#1E8E3E'
    else:
        return '#1A73E8'

export_rows = []
rows_marcos_gerais = [{"marco_geral_data": d.strftime("%Y-%m-%d")} for d in global_marcos]

rows_marcos_subj = []
ciencia_info_hum = data_ciencia.strftime('%d/%m/%Y') if isinstance(data_ciencia, date) else '—'
fato_info_hum = termo_inicial_fato.strftime('%d/%m/%Y') if isinstance(termo_inicial_fato, date) else '—'

for g in gestores:
    subj_list = [d for d in st.session_state.gestor_marcos.get(g, []) if isinstance(d, date)]
    for d in subj_list:
        rows_marcos_subj.append({"gestor": g, "chamamento_data": d.strftime("%Y-%m-%d")})

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
        <div><b>Data-alvo de prescrição:</b> {(_prazo.strftime('%d/%m/%Y') if isinstance(_prazo, date) else '—')}</div>
        <div><b>Ciência considerada (TCE-RJ):</b> {ciencia_info_hum}</div>
        <div><b>Data do fato/cessação:</b> {fato_info_hum}</div>
        <div style='grid-column: 1 / -1;'><b>Interrupções (gerais + {g}):</b> {_ints_str}</div>
      </div>
    </div>
    """
    st.markdown(_html, unsafe_allow_html=True)

    export_rows.append({
        "gestor": g,
        "situacao": res.get('sit','—'),
        "enquadramento": enquadramento,
        "base": res.get('base','—'),
        "termo_inicial": _termo.strftime('%Y-%m-%d') if isinstance(_termo, date) else '',
        "prazo_final": _prazo.strftime('%Y-%m-%d') if isinstance(_prazo, date) else '',
        "ciencia": data_ciencia.strftime('%Y-%m-%d') if isinstance(data_ciencia, date) else '',
        "fato_cessacao": termo_inicial_fato.strftime('%Y-%m-%d') if isinstance(termo_inicial_fato, date) else '',
        "interrupcoes": "; ".join([d.strftime('%Y-%m-%d') for d in _ints]) if _ints else ''
    })

# ======================================================================================
# 8) Exportação Excel (somente .xlsx) — com fallback de engine
# ======================================================================================
def sanitize_sheet_name(name: str) -> str:
    name = re.sub(r'[:\\/?*\[\]]', '_', name).strip()
    return name[:31] if len(name) > 31 else name

def make_excel_bytes_expanded(rows_resumo: list[dict],
                              rows_marcos_gerais: list[dict],
                              rows_marcos_subj: list[dict],
                              parametros: dict,
                              por_gestor_details: dict) -> bytes:
    """
    Gera .xlsx com fallback automático:
    - Se 'xlsxwriter' estiver disponível → usa formatações/condicional.
    - Caso contrário → usa 'openpyxl' (sem formatações avançadas).
    """
    engine = "openpyxl"
    try:
        import xlsxwriter  # noqa: F401
        engine = "xlsxwriter"
    except Exception:
        engine = "openpyxl"

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine=engine, datetime_format="yyyy-mm-dd", date_format="yyyy-mm-dd") as writer:
        # Resumo
        df_resumo = pd.DataFrame(rows_resumo) if rows_resumo else pd.DataFrame(columns=[
            "gestor","situacao","enquadramento","base","termo_inicial","prazo_final","ciencia","fato_cessacao","interrupcoes"
        ])
        df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
        ws_resumo = writer.sheets["Resumo"]

        if engine == "xlsxwriter":
            wb = writer.book
            widths = [26, 20, 28, 22, 15, 15, 15, 15, 40]
            for i, w in enumerate(widths):
                ws_resumo.set_column(i, i, w)
            ws_resumo.freeze_panes(1, 0)

            red_fmt = wb.add_format({"font_color": "#D93025"})
            green_fmt = wb.add_format({"font_color": "#1E8E3E"})
            blue_fmt = wb.add_format({"font_color": "#1A73E8"})
            last_row = len(df_resumo) + 1
            ws_resumo.conditional_format(f"B2:B{last_row}", {"type": "text", "criteria": "containing", "value": "Prescrição consumada", "format": red_fmt})
            ws_resumo.conditional_format(f"B2:B{last_row}", {"type": "text", "criteria": "containing", "value": "intercorrente", "format": red_fmt})
            ws_resumo.conditional_format(f"B2:B{last_row}", {"type": "text", "criteria": "containing", "value": "Não prescrito", "format": green_fmt})
            ws_resumo.conditional_format(f"B2:B{last_row}", {"type": "no_blanks", "format": blue_fmt})
        else:
            from openpyxl.utils import get_column_letter
            widths = [26, 20, 28, 22, 15, 15, 15, 15, 40]
            for idx, w in enumerate(widths, start=1):
                ws_resumo.column_dimensions[get_column_letter(idx)].width = w
            ws_resumo.freeze_panes = "A2"

        # Marcos_Gerais
        df_g = pd.DataFrame(rows_marcos_gerais) if rows_marcos_gerais else pd.DataFrame(columns=["marco_geral_data"])
        df_g.to_excel(writer, sheet_name="Marcos_Gerais", index=False)
        ws_g = writer.sheets["Marcos_Gerais"]
        if engine == "xlsxwriter":
            ws_g.set_column("A:A", 18)
            ws_g.freeze_panes(1, 0)
        else:
            from openpyxl.utils import get_column_letter
            ws_g.column_dimensions[get_column_letter(1)].width = 18
            ws_g.freeze_panes = "A2"

        # Marcos_Subjetivos
        df_s = pd.DataFrame(rows_marcos_subj) if rows_marcos_subj else pd.DataFrame(columns=["gestor","chamamento_data"])
        df_s.to_excel(writer, sheet_name="Marcos_Subjetivos", index=False)
        ws_s = writer.sheets["Marcos_Subjetivos"]
        if engine == "xlsxwriter":
            ws_s.set_column("A:A", 26)
            ws_s.set_column("B:B", 18)
            ws_s.freeze_panes(1, 0)
        else:
            from openpyxl.utils import get_column_letter
            ws_s.column_dimensions[get_column_letter(1)].width = 26
            ws_s.column_dimensions[get_column_letter(2)].width = 18
            ws_s.freeze_panes = "A2"

        # Parametros_do_Caso
        p_rows = [(k, v) for k, v in parametros.items()]
        df_p = pd.DataFrame(p_rows, columns=["parametro", "valor"])
        df_p.to_excel(writer, sheet_name="Parametros_do_Caso", index=False)
        ws_p = writer.sheets["Parametros_do_Caso"]
        if engine == "xlsxwriter":
            ws_p.set_column("A:A", 36)
            ws_p.set_column("B:B", 60)
            ws_p.freeze_panes(1, 0)
        else:
            from openpyxl.utils import get_column_letter
            ws_p.column_dimensions[get_column_letter(1)].width = 36
            ws_p.column_dimensions[get_column_letter(2)].width = 60
            ws_p.freeze_panes = "A2"

        # Dicionario
        dic_data = [
            ("gestor", "Nome do gestor (uma linha por gestor)."),
            ("situacao", "Não prescrito / Prescrição consumada / Prescrição intercorrente / Prescrição reconhecida (regime anterior)."),
            ("enquadramento", "Novo regime / Transição 2 anos / Prescrição antes da lei / Fora do alcance."),
            ("base", "quinquenal / penal (X anos) / bienal (transição)."),
            ("termo_inicial", "Data usada no cálculo, conforme enquadramento."),
            ("prazo_final", "Data-alvo projetada, após interrupções consideradas."),
            ("ciencia", "Data de ciência considerada (TCE-RJ)."),
            ("fato_cessacao", "Data do fato/cessação (transparência)."),
            ("interrupcoes", "Lista das interrupções (marcos gerais + chamamentos do gestor) usadas no cálculo."),
            ("marco_geral_data", "Data de ato inequívoco de apuração / decisão recorrível / tentativa conciliatória (valem para todos)."),
            ("chamamento_data", "Data de chamamento qualificado (efeito subjetivo, por gestor)."),
            ("parametro/valor", "Parâmetros do caso — contexto global da execução."),
        ]
        df_dic = pd.DataFrame(dic_data, columns=["coluna", "descrição"])
        df_dic.to_excel(writer, sheet_name="Dicionario", index=False)
        ws_d = writer.sheets["Dicionario"]
        if engine == "xlsxwriter":
            ws_d.set_column("A:A", 30)
            ws_d.set_column("B:B", 90)
            ws_d.freeze_panes(1, 0)
        else:
            from openpyxl.utils import get_column_letter
            ws_d.column_dimensions[get_column_letter(1)].width = 30
            ws_d.column_dimensions[get_column_letter(2)].width = 90
            ws_d.freeze_panes = "A2"

        # Abas individuais por gestor
        for g, detail in por_gestor_details.items():
            sheet = sanitize_sheet_name(f"G - {g}")
            df_det = pd.DataFrame(detail["linhas"])
            if df_det.empty:
                df_det = pd.DataFrame(columns=["campo", "valor"])
            df_det.to_excel(writer, sheet_name=sheet, index=False)
            ws_x = writer.sheets[sheet]
            if engine == "xlsxwriter":
                ws_x.set_column("A:A", 34)
                ws_x.set_column("B:B", 70)
                ws_x.freeze_panes(1, 0)
            else:
                from openpyxl.utils import get_column_letter
                ws_x.column_dimensions[get_column_letter(1)].width = 34
                ws_x.column_dimensions[get_column_letter(2)].width = 70
                ws_x.freeze_panes = "A2"

    return buf.getvalue()

# Parâmetros globais do caso (para aba "Parametros_do_Caso")
parametros_do_caso = {
    "natureza": natureza,
    "conduta": conduta,
    "data_autuacao": data_autuacao.strftime("%Y-%m-%d") if isinstance(data_autuacao, date) else "",
    "data_ciencia": data_ciencia.strftime("%Y-%m-%d") if isinstance(data_ciencia, date) else "",
    "termo_inicial_material_label": ( "Data do ato/cessação (punitiva)" if natureza=="Punitiva" else termo_inicial_fato_label ),
    "termo_inicial_material_data": termo_inicial_fato.strftime("%Y-%m-%d") if isinstance(termo_inicial_fato, date) else "",
    "transitou_pre_lc_220_2024": transitou_pre_lc,
    "aplicar_prazo_penal": aplicar_prazo_penal,
    "prazo_penal_anos": prazo_penal_anos if prazo_penal_anos else "",
    "enquadramento_global": enquadramento,
    "check_intercorrente": "Sim" if check_intercorrente else "Não",
    "intercorrente_ultimo_ato": data_ultimo_ato.strftime("%Y-%m-%d") if isinstance(data_ultimo_ato, date) else "",
    "intercorrente_ato_subseq_ou_hoje": idata_subseq.strftime("%Y-%m-%d") if isinstance(idata_subseq, date) else "",
}

# Detalhes por gestor (para abas individuais)
por_gestor_details = {}
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
    ints_cons = res.get("interrupcoes", [])
    linhas = [
        {"campo": "Gestor", "valor": g},
        {"campo": "Situação", "valor": res.get("sit","—")},
        {"campo": "Enquadramento (global)", "valor": enquadramento},
        {"campo": "Base", "valor": res.get("base","—")},
        {"campo": "Termo inicial (cálculo)", "valor": res.get("termo_inicial").strftime("%Y-%m-%d") if isinstance(res.get("termo_inicial"), date) else ""},
        {"campo": "Label do termo", "valor": res.get("termo_inicial_label","")},
        {"campo": "Data-alvo de prescrição", "valor": res.get("prazo_final").strftime("%Y-%m-%d") if isinstance(res.get("prazo_final"), date) else ""},
        {"campo": "Ciência considerada (TCE-RJ)", "valor": data_ciencia.strftime("%Y-%m-%d") if isinstance(data_ciencia, date) else ""},
        {"campo": "Fato/Cessação (transparência)", "valor": termo_inicial_fato.strftime("%Y-%m-%d") if isinstance(termo_inicial_fato, date) else ""},
        {"campo": "Marcos gerais (datas)", "valor": ", ".join(sorted({d.strftime('%Y-%m-%d') for d in global_marcos})) if global_marcos else ""},
        {"campo": f"Chamamentos qualificados de {g}", "valor": ", ".join(sorted({d.strftime('%Y-%m-%d') for d in subj_list})) if subj_list else ""},
        {"campo": "Interrupções consideradas (após o termo)", "valor": ", ".join([d.strftime('%Y-%m-%d') for d in ints_cons]) if ints_cons else ""},
    ]
    por_gestor_details[g] = {"linhas": linhas}

# ======================================================================================
# 9) Exportação — botão Excel
# ======================================================================================
st.markdown("#### Exportação (Excel)")
if export_rows:
    xlsx_bytes = make_excel_bytes_expanded(
        rows_resumo=export_rows,
        rows_marcos_gerais=rows_marcos_gerais,
        rows_marcos_subj=rows_marcos_subj,
        parametros=parametros_do_caso,
        por_gestor_details=por_gestor_details
    )
    st.download_button(
        "⬇️ Baixar resumo (Excel)",
        data=xlsx_bytes,
        file_name="prescricao_resultados_gestores.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.info("Preencha os dados e calcule ao menos um gestor para habilitar a exportação.")
