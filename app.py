import os
import re
from collections import deque
from datetime import datetime, timedelta, time
from io import BytesIO

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

LOGO_PATH = "imagens/mitri_logo.png"


@st.cache_data(show_spinner=False)
def _cor_dominante_logo(path: str) -> str:
    try:
        from PIL import Image
        import colorsys
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
            align-items: center;
            gap: 1.4rem;
            margin-bottom: 1.6rem;
            padding: 1.35rem 1.6rem;
            background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%);
            border-radius: 16px;
            box-shadow: 0 6px 20px rgba(15,41,66,.26);
        }}
        .app-header-logo {{
            flex-shrink: 0;
            display: flex;
            align-items: center;
        }}
        .app-header-divider {{
            width: 1.5px;
            height: 52px;
            background: rgba(255,255,255,.22);
            flex-shrink: 0;
        }}
        .app-header-text {{
            flex: 1;
        }}
        .app-header-text h1 {{
            font-size: 1.3rem !important;
            font-weight: 700 !important;
            color: #fff !important;
            margin: 0 0 0.22rem 0 !important;
            letter-spacing: -0.025em;
            line-height: 1.2;
        }}
        .app-header-text .app-header-sub {{
            margin: 0 !important;
            font-size: 0.88rem;
            font-weight: 400;
            color: rgba(255,255,255,.6);
            letter-spacing: 0.01em;
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

        /* ── Nota de rodapé ── */
        .app-foot {{
            text-align: center;
            font-size: 0.76rem;
            color: {MUTED};
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid {BORDER};
        }}

        /* logo transparente */
        [data-testid="stImage"] img,
        [data-testid="stImage"] picture img {{
            background: transparent !important;
        }}
        [data-testid="stImage"] {{
            background: transparent !important;
        }}

        /* inputs - borda mais suave */
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] div {{
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
    total  = int(td.total_seconds())
    h, r   = divmod(total, 3600)
    m, _   = divmod(r, 60)
    return f"{h:02d}h{m:02d}min"


def nome_arquivo_seguro(nome: str, data_fmt: str) -> str:
    base = re.sub(r'[<>:"/\\|?*]', "_", nome).strip() or "documento"
    return f"justificativa_{base}_{data_fmt.replace('/', '-')}.pdf"


def _nova_pagina(c, W, H, margem, y, min_y):
    if y >= min_y:
        return y
    _rodape_pdf(c, W)
    c.showPage()
    _cabecalho_continua(c, W, H)
    return H - margem - 1.2 * cm


def _cabecalho_continua(c, W, H):
    c.setFillColor(colors.HexColor(PRIMARY))
    c.rect(0, H - 0.42 * cm, W, 0.42 * cm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(ACCENT))
    c.rect(0, H - 0.72 * cm, W, 0.30 * cm, fill=1, stroke=0)


def _rodape_pdf(c, W):
    emissao = datetime.now().strftime('%d/%m/%Y  %H:%M')
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.5)
    c.line(2 * cm, 1.55 * cm, W - 2 * cm, 1.55 * cm)
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(2 * cm, 1.1 * cm, "Hospital Regional Sul")
    c.drawRightString(W - 2 * cm, 1.1 * cm, f"Emitido em {emissao}")


# ==================================================
# CABEÇALHO DA PÁGINA
# ==================================================
_logo_png = logo_transparente_png(LOGO_PATH)

logo_html = ""
if _logo_png:
    import base64
    _b64 = base64.b64encode(_logo_png).decode()
    logo_html = f'<img src="data:image/png;base64,{_b64}" style="height:68px;width:auto;filter:brightness(0) invert(1);display:block;" />'
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

st.caption("Preencha todos os campos obrigatórios (*) e clique em **Gerar PDF** para baixar o documento.")

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
            crm  = st.text_input("CRM *", placeholder="Ex.: 12345 / SP")

        st.markdown('<p class="form-section">Dados do Plantão</p>', unsafe_allow_html=True)
        ca, cb = st.columns([3, 2])
        with ca:
            setor = st.selectbox("Setor *", SETOR_OPCOES)
        with cb:
            data  = st.date_input("Data *", format="DD/MM/YYYY")

        cc, cd = st.columns(2)
        with cc:
            hora_entrada = st.time_input("Entrada *", value=time(7, 0),  step=timedelta(minutes=15))
        with cd:
            hora_saida   = st.time_input("Saída *",   value=time(19, 0), step=timedelta(minutes=15))

        st.markdown('<p class="form-section">Justificativa</p>', unsafe_allow_html=True)
        motivo = st.text_area(
            "Motivo *",
            height=130,
            placeholder=(
                "Descreva o motivo com objetividade.\n"
                "Ex.: atraso no registro de entrada, plantão não batido, correção de horário..."
            ),
        )

        st.markdown('<p class="form-section">Assinatura</p>', unsafe_allow_html=True)
        assinatura = st.text_input(
            "Nome para assinatura *",
            placeholder="Conforme documento oficial / CRM",
        )

        enviar = st.form_submit_button("⬇  Gerar PDF", use_container_width=True)

st.markdown(
    '<p class="app-foot">Em caso de dúvidas, contate a administração · Hospital Regional Sul</p>',
    unsafe_allow_html=True,
)

# ==================================================
# GERAR PDF
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

    # ── Métricas ──
    data_fmt  = data.strftime("%d/%m/%Y")
    hora_ent  = hora_entrada.strftime("%H:%M")
    hora_sai  = hora_saida.strftime("%H:%M")
    td_dur    = duracao_plantao(data, hora_entrada, hora_saida)
    horas_dur = fmt_duracao(td_dur)

    # ── Canvas ──
    buffer = BytesIO()
    c      = canvas.Canvas(buffer, pagesize=A4)
    W, H   = A4
    margem = 2.1 * cm
    min_y  = 2.8 * cm

    # ─────────────────────────────────────────────
    # CABEÇALHO PDF
    # ─────────────────────────────────────────────
    logo_area_h = 3.8 * cm

    # Área cinza clara para o logo
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(0, H - logo_area_h, W, logo_area_h, fill=1, stroke=0)

    # Logo centralizado
    _ir    = ImageReader(BytesIO(_logo_bytes))
    iw, ih = _ir.getSize()
    if iw <= 0 or ih <= 0: iw = ih = 1
    logo_w = 4.8 * cm
    logo_h = logo_w * (ih / iw)
    logo_x = (W - logo_w) / 2
    logo_y = H - logo_area_h + (logo_area_h - logo_h) / 2
    c.drawImage(_ir, logo_x, logo_y, width=logo_w, height=logo_h, mask="auto")

    # Título centralizado abaixo da área cinza
    titulo_y = H - logo_area_h - 0.7 * cm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(W / 2, titulo_y, "JUSTIFICATIVA DE PONTO")

    subtitulo_y = titulo_y - 0.58 * cm
    c.setFont("Helvetica", 9.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(W / 2, subtitulo_y, "Hospital Regional Sul")

    # Linha divisória
    y = subtitulo_y - 0.7 * cm
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.8)
    c.line(margem, y, W - margem, y)

    y -= 1.1 * cm

    # ─────────────────────────────────────────────
    # SEÇÃO: DADOS DO PLANTÃO
    # ─────────────────────────────────────────────
    def _secao(cy, titulo):
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor(MUTED))
        c.drawString(margem, cy, titulo.upper())
        c.setStrokeColor(colors.HexColor(BORDER))
        c.setLineWidth(0.6)
        lbl_w = c.stringWidth(titulo.upper(), "Helvetica-Bold", 8)
        c.line(margem + lbl_w + 0.3 * cm, cy + 0.22 * cm, W - margem, cy + 0.22 * cm)
        c.setFillColor(colors.black)
        return cy - 0.7 * cm

    y = _secao(y, "Dados do Plantão")

    campos = [
        ("Médico",  nome,      True),
        ("CRM",     crm,       False),
        ("Setor",   setor,     True),
        ("Data",    data_fmt,  False),
        ("Entrada", hora_ent,  True),
        ("Saída",   hora_sai,  False),
        ("Duração", horas_dur, True),
    ]

    label_col_w = 2.6 * cm
    value_x     = margem + label_col_w + 0.2 * cm
    row_h       = 0.68 * cm
    line_extra  = 0.38 * cm

    def _campo_linha(cy, titulo_c, valor_c, shade):
        linhas_v = quebrar_texto(str(valor_c), limite=34)
        rh = max(row_h, 0.42 * cm + max(0, len(linhas_v) - 1) * line_extra + 0.18 * cm)
        if shade:
            c.setFillColor(colors.HexColor("#f8fafc"))
            c.setStrokeColor(colors.HexColor(BORDER))
            c.setLineWidth(0.4)
            c.rect(margem, cy - rh + 0.1 * cm, W - 2 * margem, rh, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor(PRIMARY))
        c.drawString(margem + 0.3 * cm, cy - 0.44 * cm, titulo_c)
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)
        for j, lv in enumerate(linhas_v):
            c.drawString(value_x, cy - 0.44 * cm - j * line_extra, lv)
        return cy - rh

    for i, (lbl, val, shade) in enumerate(campos):
        y = _nova_pagina(c, W, H, margem, y, min_y + row_h + 0.5 * cm)
        y = _campo_linha(y, lbl, val, shade)

    # ─────────────────────────────────────────────
    # SEÇÃO: JUSTIFICATIVA
    # ─────────────────────────────────────────────
    y -= 0.85 * cm
    y = _nova_pagina(c, W, H, margem, y, min_y + 2.5 * cm)
    y = _secao(y, "Justificativa")

    linhas_mot = quebrar_texto(motivo.strip(), limite=86)
    line_h_mot = 15
    pad_mot    = 18
    box_h      = len(linhas_mot) * line_h_mot + pad_mot * 2

    y = _nova_pagina(c, W, H, margem, y, min_y + box_h / 72 * 2.54 * cm + 0.5 * cm)

    c.setFillColor(colors.HexColor("#fafbfc"))
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.8)
    c.roundRect(margem, y - box_h, W - 2 * margem, box_h, 7, stroke=1, fill=1)

    # Borda lateral colorida
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.rect(margem, y - box_h, 0.18 * cm, box_h, fill=1, stroke=0)

    texto_obj = c.beginText(margem + 0.45 * cm, y - pad_mot)
    texto_obj.setFont("Helvetica", 11)
    texto_obj.setLeading(line_h_mot)
    texto_obj.setFillColor(colors.HexColor("#1e293b"))
    for ln in linhas_mot:
        texto_obj.textLine(ln)
    c.drawText(texto_obj)

    y -= box_h

    # ─────────────────────────────────────────────
    # SEÇÃO: ASSINATURA
    # ─────────────────────────────────────────────
    y -= 1.2 * cm
    y = _nova_pagina(c, W, H, margem, y, min_y + 4.5 * cm)
    y = _secao(y, "Assinatura do Médico")

    sig_h    = 2.4 * cm
    sig_left = margem
    sig_w    = W - 2 * margem

    # Caixa com fundo sutil e borda leve
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.9)
    c.roundRect(sig_left, y - sig_h, sig_w, sig_h, 9, stroke=1, fill=1)

    # Barra lateral colorida (cor do logo)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.rect(sig_left, y - sig_h + 0.4 * cm, 0.15 * cm, sig_h - 0.8 * cm, fill=1, stroke=0)

    cx = W / 2

    # Linha 1: ASSINATURA: [nome] - CRM [crm]
    linha1 = f"ASSINATURA: {assinatura.upper()} - CRM {crm.upper()}"
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(cx, y - 0.78 * cm, linha1)

    # Linha 2: horário da assinatura
    horario_ass = datetime.now().strftime("%d/%m/%Y  %H:%M")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 1.42 * cm, horario_ass)

    # ─────────────────────────────────────────────
    # RODAPÉ
    # ─────────────────────────────────────────────
    _rodape_pdf(c, W)
    c.save()
    buffer.seek(0)

    st.success("PDF gerado com sucesso.")
    st.download_button(
        label="⬇  Baixar PDF",
        data=buffer,
        file_name=nome_arquivo_seguro(nome, data_fmt),
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
