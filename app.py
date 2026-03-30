import os
import re
import base64
import json
from collections import deque
from datetime import datetime, timedelta, time, timezone
from io import BytesIO
import requests as http_requests
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
# ==================================================
# CONFIG
# ==================================================
st.set_page_config(
    page_title="Justificativa de Ponto",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)
PRIMARY  = "#0f2942"
ACCENT   = "#1e4a6e"
MUTED    = "#64748b"
SURFACE  = "#f8fafc"
BORDER   = "#e2e8f0"
SECTION  = "#94a3b8"
SUCCESS  = "#166534"
_BRT     = timezone(timedelta(hours=-3))
LOGO_PATH = "imagens/mitri_logo.png"
@st.cache_data(show_spinner=False)
def _cor_dominante_logo(path: str) -> str:
    try:
        from PIL import Image
    except ImportError:
        return ACCENT
    if not os.path.isfile(path):
        return ACCENT
    img = Image.open(path).convert("RGBA")
    img.thumbnail((120, 120))
    px = img.load()
    w, h = img.size
    contagem: dict = {}
    for x in range(w):
        for y in range(h):
            r, g, b, a = px[x, y]
            if a < 30:
                continue
            mx = max(r, g, b)
            mn = min(r, g, b)
            if mx < 30 or (mx > 220 and mn > 200):
                continue
            balde = (r // 24) * 24, (g // 24) * 24, (b // 24) * 24
            contagem[balde] = contagem.get(balde, 0) + 1
    if not contagem:
        return ACCENT
    r, g, b = max(contagem, key=contagem.get)
    return f"#{r:02x}{g:02x}{b:02x}"
LOGO_COLOR = _cor_dominante_logo(LOGO_PATH)
st.markdown(
    f"""
    <style>
        html, body, [class*="css"] {{
            font-family: system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
        .block-container {{
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 700px !important;
        }}
        /* ── Cabeçalho ── */
        .app-header {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 1rem;
            margin-bottom: 1.4rem;
            padding: 0.70rem 0.9rem 0.30rem;
            background: linear-gradient(160deg, {PRIMARY} 0%, {ACCENT} 100%);
            border-radius: 14px;
            box-shadow: 0 6px 18px rgba(15,41,66,.26);
        }}
        .app-header-logo {{
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .app-header-divider {{
            width: min(220px, 72%);
            height: 1.5px;
            background: rgba(255,255,255,.22);
            flex-shrink: 0;
        }}
        .app-header-text {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.35rem;
            text-align: center;
            width: 100%;
        }}
        .app-header-text h1 {{
            font-size: 1.68rem !important;
            font-weight: 800 !important;
            color: #fff !important;
            margin: 0 !important;
            letter-spacing: -0.02em;
            line-height: 1.2;
            text-align: center !important;
            width: 100%;
        }}
        .app-header-text .app-header-sub {{
            margin: 0 !important;
            font-size: 0.86rem;
            font-weight: 400;
            color: rgba(255,255,255,.55);
            letter-spacing: 0.04em;
            text-transform: uppercase;
            text-align: center;
        }}
        /* ── Seções ── */
        .form-section {{
            display: flex;
            align-items: center;
            gap: 0.55rem;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.13em;
            color: {SECTION};
            margin: 1.3rem 0 0.7rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 1.5px solid {BORDER};
        }}
        .form-section::before {{
            content: "";
            display: inline-block;
            width: 3px;
            height: 13px;
            background: {LOGO_COLOR};
            border-radius: 2px;
        }}
        /* ── Cartão do formulário ── */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: #fff !important;
            border-radius: 16px !important;
            border: 1.5px solid {BORDER} !important;
            box-shadow: 0 2px 12px rgba(15,41,66,.07) !important;
            padding: 1.4rem 1.5rem 1.5rem 1.5rem !important;
        }}
        /* ── Botão enviar ── */
        div[data-testid="stFormSubmitButton"] button {{
            width: 100%;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            padding: 0.7rem 1rem !important;
            background: linear-gradient(180deg, {LOGO_COLOR} 0%, {PRIMARY} 100%) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 3px 10px rgba(15,41,66,.28);
            margin-top: 0.5rem;
            letter-spacing: 0.01em;
        }}
        div[data-testid="stFormSubmitButton"] button:hover {{
            filter: brightness(1.07);
            box-shadow: 0 5px 14px rgba(15,41,66,.32);
        }}
        /* ── Botão download ── */
        .stDownloadButton button {{
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            width: 100%;
        }}
        /* ── Rodapé ── */
        .app-foot {{
            text-align: center;
            font-size: 0.76rem;
            color: {MUTED};
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid {BORDER};
        }}
        [data-testid="stImage"] img,
        [data-testid="stImage"] picture img {{
            background: transparent !important;
        }}
        [data-testid="stImage"] {{
            background: transparent !important;
        }}
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] div {{
            border-radius: 8px !important;
        }}
        [data-testid="stDateInput"] input,
        [data-testid="stDateInput"] fieldset,
        div[data-baseweb="datepicker"] input {{
            border-radius: 8px !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)
SETOR_OPCOES = [
    "Clínica Médica - PS",
    "Diarista - Neurologista",
    "Neurocirurgia",
    "UTI",
]
# ==================================================
# UTILITÁRIOS
# ==================================================
@st.cache_data(show_spinner=False)
def logo_transparente_png(path: str) -> bytes | None:
    if not os.path.isfile(path):
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    def _claro(r, g, b, lim):
        return r >= lim and g >= lim and b >= lim
    img  = Image.open(path).convert("RGBA")
    px   = img.load()
    w, h = img.size
    lim  = 245
    visto: set = set()
    fila = deque()
    for x in range(w):
        for y_ in (0, h - 1):
            if (x, y_) not in visto and _claro(*px[x, y_][:3], lim):
                visto.add((x, y_)); fila.append((x, y_))
    for y_ in range(h):
        for x in (0, w - 1):
            if (x, y_) not in visto and _claro(*px[x, y_][:3], lim):
                visto.add((x, y_)); fila.append((x, y_))
    while fila:
        x, y_ = fila.popleft()
        r, g, b, a = px[x, y_]
        px[x, y_] = (r, g, b, 0)
        for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
            nx, ny = x+dx, y_+dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visto:
                if _claro(*px[nx, ny][:3], lim):
                    visto.add((nx, ny)); fila.append((nx, ny))
    out = BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
def quebrar_texto(texto: str, limite: int = 88) -> list[str]:
    linhas: list[str] = []
    for bloco in texto.replace("\r\n", "\n").split("\n"):
        if not bloco.strip():
            linhas.append(""); continue
        palavras = bloco.split(); linha = ""
        for palavra in palavras:
            candidato = (linha + " " + palavra).strip()
            if len(candidato) <= limite:
                linha = candidato
            else:
                if linha: linhas.append(linha)
                linha = palavra
        if linha: linhas.append(linha)
    return linhas if linhas else [""]
def duracao_plantao(d, t_in: time, t_out: time) -> timedelta:
    start = datetime.combine(d, t_in)
    end   = datetime.combine(d, t_out)
    if end <= start:
        end += timedelta(days=1)
    return end - start
def fmt_duracao(td: timedelta) -> str:
    total = int(td.total_seconds())
    h, r  = divmod(total, 3600)
    m, _  = divmod(r, 60)
    return f"{h:02d}h{m:02d}min"
def nome_arquivo_seguro(nome: str, data_fmt: str) -> str:
    base = re.sub(r'[<>:"/\\|?*]', "_", nome).strip() or "documento"
    return f"{base}_{data_fmt.replace('/', '-')}.pdf"
def _nova_pagina(c, W, H, margem, y, min_y):
    if y >= min_y:
        return y
    _rodape_pdf(c, W, H)
    c.showPage()
    _cabecalho_continua(c, W, H)
    return H - margem - 1.0 * cm
def _cabecalho_continua(c, W, H):
    c.setFillColor(colors.white)
    c.rect(0, H - 0.55 * cm, W, 0.55 * cm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.rect(0, H - 0.72 * cm, W, 0.18 * cm, fill=1, stroke=0)
def _rodape_pdf(c, W, H):
    emissao = datetime.now(_BRT).strftime('%d/%m/%Y  %H:%M')
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(0, 0, W, 1.8 * cm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.rect(0, 1.78 * cm, W, 0.04 * cm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawString(2 * cm, 1.12 * cm, "Hospital Regional Sul")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(2 * cm, 0.62 * cm, "Documento gerado eletronicamente · Não requer assinatura física")
    c.drawRightString(W - 2 * cm, 0.87 * cm, f"Emitido em {emissao}")
# ==================================================
# GOOGLE APPS SCRIPT — ENVIO VIA WEB APP
# ==================================================
def enviar_para_google(pdf_buffer: BytesIO, nome_arquivo: str, dados: dict) -> dict:
    """
    Envia o PDF e os dados para o Google Apps Script Web App.
    O script salva o PDF no Drive (subpasta por setor) e
    registra os dados na planilha.
    Retorna o JSON de resposta do Apps Script.
    """
    apps_script_url = st.secrets["apps_script"]["url"]
    pdf_buffer.seek(0)
    pdf_b64 = base64.b64encode(pdf_buffer.read()).decode("utf-8")
    payload = {
        "nome":             dados["nome"],
        "crm":              dados["crm"],
        "setor":            dados["setor"],
        "data_fmt":         dados["data_fmt"],
        "hora_ent":         dados["hora_ent"],
        "hora_sai":         dados["hora_sai"],
        "duracao":          dados["duracao"],
        "motivo":           dados["motivo"],
        "assinatura":       dados["assinatura"],
        "nome_arquivo":     nome_arquivo,
        "pdf_base64":       pdf_b64,
        "titulo_planilha":  dados.get("titulo_planilha", "JUSTIFICATIVA DE PONTO"),
        "logo_base64":      dados.get("logo_base64", ""),
    }
    resp = http_requests.post(
        apps_script_url,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()
# ==================================================
# CABEÇALHO DA PÁGINA (APP)
# ==================================================
_logo_png = logo_transparente_png(LOGO_PATH)
logo_html = ""
if _logo_png:
    import base64
    _b64 = base64.b64encode(_logo_png).decode()
    logo_html = (
        f'<img src="data:image/png;base64,{_b64}" '
        f'style="height:148px;width:auto;filter:brightness(0) invert(1);display:block;" />'
    )
elif os.path.exists(LOGO_PATH):
    logo_html = '<span style="color:rgba(255,255,255,.5);font-size:0.8rem;">Logo</span>'
st.markdown(
    f"""
    <div class="app-header">
        <div class="app-header-logo">{logo_html}</div>
        <div class="app-header-divider"></div>
        <div class="app-header-text">
            <h1>Justificativa de Ponto</h1>
            <p class="app-header-sub">Hospital Regional Sul</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("Preencha todos os campos obrigatórios (*) e clique em **Enviar relatório** para realizar a justificativa.")
# ==================================================
# FORMULÁRIO
# ==================================================
with st.container(border=True):
    with st.form("formulario"):
        st.markdown('<p class="form-section">Identificação</p>', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            nome = st.text_input("Nome do médico *", placeholder="Nome completo")
        with c2:
            crm  = st.text_input("CRM *", placeholder="Ex.: 12345")
        st.markdown('<p class="form-section">Dados do Plantão</p>', unsafe_allow_html=True)
        ca, cb = st.columns([3, 2])
        with ca:
            setor = st.selectbox("Setor *", SETOR_OPCOES)
        with cb:
            data = st.date_input(
                "Data *",
                value=datetime.now(_BRT).date(),
                format="DD/MM/YYYY",
            )
        cd, ce = st.columns(2)
        with cd:
            hora_entrada = st.time_input("Entrada *", value=time(7, 0),  step=timedelta(minutes=15))
        with ce:
            hora_saida   = st.time_input("Saída *",   value=time(19, 0), step=timedelta(minutes=15))
        st.markdown('<p class="form-section">Justificativa</p>', unsafe_allow_html=True)
        motivo = st.text_area(
            "Motivo *",
            height=150,
            placeholder=(
                "Descreva o motivo com objetividade.\n"
                "Ex.: atraso no registro de entrada, plantão não batido, correção de horário..."
            ),
        )
        st.markdown('<p class="form-section">Assinatura</p>', unsafe_allow_html=True)
        cf, cg = st.columns([3, 2])
        with cf:
            assinatura = st.text_input(
                "Nome para assinatura *",
                placeholder="Conforme documento oficial",
            )
        with cg:
            st.markdown(
                f"""
                <div style="
                    margin-top: 1.65rem;
                    padding: 0.5rem 0.75rem;
                    background: {SURFACE};
                    border: 1px solid {BORDER};
                    border-radius: 8px;
                    font-size: 0.78rem;
                    color: {MUTED};
                    line-height: 1.5;
                ">
                    O nome digitado será registrado como assinatura eletrônica no relatório.
                </div>
                """,
                unsafe_allow_html=True,
            )
        enviar = st.form_submit_button("📄  Enviar relatório", use_container_width=True)
st.markdown(
    '<p class="app-foot">Em caso de dúvidas, contate a administração · Hospital Regional Sul</p>',
    unsafe_allow_html=True,
)
# ==================================================
# GERAR PDF  –  layout profissional
# ==================================================
if enviar:
    erros = []
    if not nome.strip():        erros.append("Nome do médico")
    if not crm.strip():         erros.append("CRM")
    if not motivo.strip():      erros.append("Motivo da justificativa")
    if not assinatura.strip():  erros.append("Nome para assinatura")
    if erros:
        st.error(f"Campos obrigatórios não preenchidos: **{', '.join(erros)}**.")
        st.stop()
    if not os.path.exists(LOGO_PATH):
        st.error(f"Logo não encontrada em `{LOGO_PATH}`. Verifique o caminho.")
        st.stop()
    _logo_bytes = logo_transparente_png(LOGO_PATH)
    if _logo_bytes is None:
        with open(LOGO_PATH, "rb") as _lf:
            _logo_bytes = _lf.read()
    data_fmt  = data.strftime("%d/%m/%Y")
    hora_ent  = hora_entrada.strftime("%H:%M")
    hora_sai  = hora_saida.strftime("%H:%M")
    td_dur    = duracao_plantao(data, hora_entrada, hora_saida)
    horas_dur = fmt_duracao(td_dur)
    buffer = BytesIO()
    c      = canvas.Canvas(buffer, pagesize=A4)
    W, H   = A4
    margem = 2.0 * cm
    min_y  = 2.2 * cm
    # ─────────────────────────────────────────────────────────────
    # CABEÇALHO PDF — título/subtítulo abaixo do logo (sem sobreposição)
    # ─────────────────────────────────────────────────────────────
    iw, ih = ImageReader(BytesIO(_logo_bytes)).getSize()
    if iw <= 0 or ih <= 0:
        iw = ih = 1
    logo_w = 4.4 * cm
    logo_h = logo_w * (ih / iw)
    logo_x = (W - logo_w) / 2
    logo_y = H - 1.0 * cm - logo_h
    titulo_y = logo_y - 0.80 * cm
    subtitulo_y = titulo_y - 0.62 * cm
    cabecalho_base_y = subtitulo_y - 0.50 * cm
    hdr_h = H - cabecalho_base_y

    c.setFillColor(colors.white)
    c.rect(0, cabecalho_base_y, W, hdr_h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.rect(0, cabecalho_base_y - 0.20 * cm, W, 0.20 * cm, fill=1, stroke=0)

    c.drawImage(
        ImageReader(BytesIO(_logo_bytes)),
        logo_x,
        logo_y,
        width=logo_w,
        height=logo_h,
        mask="auto",
        preserveAspectRatio=True,
    )

    cx = W / 2
    c.setFont("Helvetica-Bold", 17)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(cx, titulo_y, "JUSTIFICATIVA DE PONTO")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, subtitulo_y, "Hospital Regional Sul")

    y = cabecalho_base_y - 0.20 * cm - 1.0 * cm
    y -= 0.55 * cm
    y -= 0.50 * cm
    # ─────────────────────────────────────────────────────────────
    # HELPERS PDF
    # ─────────────────────────────────────────────────────────────
    def _secao_titulo(cy: float, titulo: str) -> float:
        pill_w = c.stringWidth(titulo.upper(), "Helvetica-Bold", 8) + 0.8 * cm
        c.setFillColor(colors.HexColor(PRIMARY))
        c.roundRect(margem, cy - 0.05 * cm, pill_w, 0.52 * cm, 4, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.white)
        c.drawString(margem + 0.35 * cm, cy + 0.11 * cm, titulo.upper())
        c.setStrokeColor(colors.HexColor(BORDER))
        c.setLineWidth(0.5)
        c.line(margem + pill_w + 0.25 * cm, cy + 0.22 * cm, W - margem, cy + 0.22 * cm)
        return cy - 0.85 * cm
    ROW_H      = 1.02 * cm
    LINE_EXTRA = 0.52 * cm
    LBL_W      = 3.4 * cm
    VAL_X      = margem + LBL_W
    def _campo(cy: float, label: str, valor: str, shade: bool) -> float:
        linhas_v = quebrar_texto(str(valor), limite=42)
        rh = max(ROW_H, 0.44 * cm + max(0, len(linhas_v) - 1) * LINE_EXTRA + 0.20 * cm)
        if shade:
            c.setFillColor(colors.HexColor("#f0f4f8"))
            c.rect(margem, cy - rh + 0.08 * cm, W - 2 * margem, rh, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor(PRIMARY))
        c.drawString(margem + 0.35 * cm, cy - 0.52 * cm, label.upper())
        c.setFont("Helvetica", 11.5)
        c.setFillColor(colors.HexColor("#1e293b"))
        for j, lv in enumerate(linhas_v):
            c.drawString(VAL_X, cy - 0.52 * cm - j * LINE_EXTRA, lv)
        c.setStrokeColor(colors.HexColor(BORDER))
        c.setLineWidth(0.35)
        c.line(margem, cy - rh + 0.08 * cm, W - margem, cy - rh + 0.08 * cm)
        return cy - rh
    def _campo_2col(cy: float, pares: list[tuple]) -> float:
        rh = ROW_H
        col_w = (W - 2 * margem) / 2
        for i, (label, valor, shade) in enumerate(pares):
            ox = margem + i * col_w
            if shade:
                c.setFillColor(colors.HexColor("#f0f4f8"))
                c.rect(ox, cy - rh + 0.08 * cm, col_w, rh, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(colors.HexColor(PRIMARY))
            c.drawString(ox + 0.35 * cm, cy - 0.52 * cm, label.upper())
            c.setFont("Helvetica", 11.5)
            c.setFillColor(colors.HexColor("#1e293b"))
            c.drawString(ox + 3.2 * cm, cy - 0.52 * cm, str(valor))
        c.setStrokeColor(colors.HexColor(BORDER))
        c.setLineWidth(0.35)
        c.line(margem, cy - rh + 0.08 * cm, W - margem, cy - rh + 0.08 * cm)
        return cy - rh
    # ─────────────────────────────────────────────────────────────
    # BLOCO 1 — DADOS DO PLANTÃO
    # ─────────────────────────────────────────────────────────────
    y = _secao_titulo(y, "Dados do Plantão")
    bloco1_top = y + 0.85 * cm
    y = _campo(y, "Médico",  nome,   True)
    y = _campo(y, "CRM",     crm,    False)
    y = _campo(y, "Setor",   setor,  True)
    y = _campo_2col(y, [("Data", data_fmt, False), ("Duração", horas_dur, False)])
    y = _campo_2col(y, [("Entrada", hora_ent, True), ("Saída", hora_sai, True)])
    bloco1_bot = y
    # Fundo sutil do card
    c.setFillColor(colors.HexColor("#f8fafb"))
    c.roundRect(margem, bloco1_bot, W - 2 * margem, bloco1_top - bloco1_bot, 8, fill=1, stroke=0)
    # Borda do card
    c.setStrokeColor(colors.HexColor("#d0d7de"))
    c.setLineWidth(0.8)
    c.roundRect(margem, bloco1_bot, W - 2 * margem, bloco1_top - bloco1_bot, 8, stroke=1, fill=0)
    # Barra lateral accent
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, bloco1_bot + 0.15 * cm, 0.25 * cm, bloco1_top - bloco1_bot - 0.3 * cm, 3, fill=1, stroke=0)
    # Re-desenha os campos por cima do fundo
    y_redraw = bloco1_top - 0.85 * cm
    y_redraw = _campo(y_redraw, "Médico",  nome,   True)
    y_redraw = _campo(y_redraw, "CRM",     crm,    False)
    y_redraw = _campo(y_redraw, "Setor",   setor,  True)
    y_redraw = _campo_2col(y_redraw, [("Data", data_fmt, False), ("Duração", horas_dur, False)])
    y_redraw = _campo_2col(y_redraw, [("Entrada", hora_ent, True), ("Saída", hora_sai, True)])
    # ─────────────────────────────────────────────────────────────
    # BLOCO 2 — JUSTIFICATIVA
    # ─────────────────────────────────────────────────────────────
    y -= 1.25 * cm
    y = _nova_pagina(c, W, H, margem, y, min_y + 3.0 * cm)
    y = _secao_titulo(y, "Justificativa")
    linhas_mot = quebrar_texto(motivo.strip(), limite=78)
    line_h_mot = 19
    pad_top    = 26
    pad_bot    = 22
    box_h      = len(linhas_mot) * line_h_mot + pad_top + pad_bot
    y = _nova_pagina(c, W, H, margem, y, min_y + box_h / 28.35 + 0.5 * cm)
    c.setFillColor(colors.HexColor("#fafbfc"))
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.8)
    c.roundRect(margem, y - box_h, W - 2 * margem, box_h, 6, stroke=1, fill=1)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, y - box_h, 0.22 * cm, box_h, 3, fill=1, stroke=0)
    texto_obj = c.beginText(margem + 0.52 * cm, y - pad_top)
    texto_obj.setFont("Helvetica", 12)
    texto_obj.setLeading(line_h_mot)
    texto_obj.setFillColor(colors.HexColor("#1e293b"))
    for ln in linhas_mot:
        texto_obj.textLine(ln)
    c.drawText(texto_obj)
    y -= box_h
    # ─────────────────────────────────────────────────────────────
    # BLOCO 3 — ASSINATURA
    # ─────────────────────────────────────────────────────────────
    y -= 1.35 * cm
    y = _nova_pagina(c, W, H, margem, y, min_y + 3.5 * cm)
    y = _secao_titulo(y, "Assinatura do Médico")
    sig_h = 3.05 * cm
    sig_w = W - 2 * margem
    cx = W / 2
    # Card de fundo
    c.setFillColor(colors.HexColor("#fafcfd"))
    c.setStrokeColor(colors.HexColor("#d0d7de"))
    c.setLineWidth(0.8)
    c.roundRect(margem, y - sig_h, sig_w, sig_h, 10, stroke=1, fill=1)
    # Barra lateral accent
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, y - sig_h + 0.25 * cm, 0.25 * cm, sig_h - 0.5 * cm, 3, fill=1, stroke=0)
    # Nome da assinatura
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(cx, y - 0.78 * cm, assinatura.upper())
    # Linha decorativa
    line_w = 3.2 * cm
    c.setStrokeColor(colors.HexColor(LOGO_COLOR))
    c.setLineWidth(1.2)
    c.line(cx - line_w, y - 1.08 * cm, cx + line_w, y - 1.08 * cm)
    # CRM e setor
    c.setFont("Helvetica", 10.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 1.48 * cm, f"CRM {crm.upper()}  ·  {setor}")
    # Separador fino
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.4)
    c.line(cx - 4.0 * cm, y - 1.88 * cm, cx + 4.0 * cm, y - 1.88 * cm)
    # Data/hora da assinatura
    horario_ass = datetime.now(_BRT).strftime("%d/%m/%Y  %H:%M")
    c.setFont("Helvetica-Oblique", 9.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 2.38 * cm, f"Assinado eletronicamente em {horario_ass}")
    # Ícone de verificação (pequeno círculo verde)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.circle(cx - 3.8 * cm, y - 2.32 * cm, 0.12 * cm, fill=1, stroke=0)
    y -= sig_h
    # ─────────────────────────────────────────────────────────────
    # RODAPÉ
    # ─────────────────────────────────────────────────────────────
    _rodape_pdf(c, W, H)
    c.save()
    buffer.seek(0)
    # ─────────────────────────────────────────────────────────────
    # UPLOAD PARA GOOGLE DRIVE + REGISTRO NA PLANILHA
    # ─────────────────────────────────────────────────────────────
    arquivo_nome = nome_arquivo_seguro(nome, data_fmt)
    try:
        with st.spinner("Enviando PDF para o Google Drive e registrando na planilha..."):
            resultado = enviar_para_google(
                pdf_buffer=buffer,
                nome_arquivo=arquivo_nome,
                dados={
                    "nome":            nome,
                    "crm":             crm,
                    "setor":           setor,
                    "data_fmt":        data_fmt,
                    "hora_ent":        hora_ent,
                    "hora_sai":        hora_sai,
                    "duracao":         horas_dur,
                    "motivo":          motivo.strip(),
                    "assinatura":      assinatura,
                    "titulo_planilha": "JUSTIFICATIVA DE PONTO",
                    "logo_base64":     base64.b64encode(_logo_bytes).decode("utf-8"),
                },
            )
        if resultado.get("status") == "ok":
            st.success("Relatório enviado com sucesso!")
        else:
            st.warning(
                f"Resposta inesperada do servidor: {resultado.get('message', 'Sem detalhes')}\n\n"
                "Você ainda pode baixar o PDF abaixo."
            )
    except Exception as e:
        st.warning(
            f"O PDF foi gerado, mas houve um erro ao enviá-lo: {e}\n\n"
            "Você ainda pode baixar o PDF abaixo."
        )
    # Sempre disponibiliza o download local
    buffer.seek(0)
    st.download_button(
        label="⬇  Baixar PDF",
        data=buffer,
        file_name=arquivo_nome,
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
