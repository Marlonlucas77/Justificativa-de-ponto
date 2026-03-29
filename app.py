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

PRIMARY = "#0f2942"
ACCENT = "#1e4a6e"
MUTED = "#64748b"
SURFACE = "#f8fafc"
BORDER = "#e2e8f0"
SECTION = "#94a3b8"

st.markdown(
    f"""
    <style>
        html, body, [class*="css"] {{
            font-family: system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
        .block-container {{
            padding-top: 1.5rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 680px !important;
        }}
        .app-header-row {{
            margin-bottom: 1.35rem;
        }}
        .app-header-text {{
            padding: 0.15rem 0 0 0.25rem;
        }}
        .app-header-text .app-header-label {{
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: {ACCENT};
            margin: 0 0 0.35rem 0;
        }}
        .app-header-text h1 {{
            font-size: 1.35rem !important;
            font-weight: 700 !important;
            color: {PRIMARY} !important;
            margin: 0 0 0.4rem 0 !important;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }}
        .app-header-text .app-header-hospital {{
            margin: 0 !important;
            font-size: 0.95rem;
            font-weight: 500;
            color: {MUTED};
            line-height: 1.35;
        }}
        .form-section {{
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.11em;
            color: {SECTION};
            margin: 1.1rem 0 0.65rem 0;
            padding-bottom: 0.35rem;
            border-bottom: 1px solid {BORDER};
        }}
        .form-section:first-of-type {{
            margin-top: 0.15rem;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: #fff !important;
            border-radius: 16px !important;
            border-color: {BORDER} !important;
            box-shadow: 0 1px 2px rgba(15, 41, 66, 0.05);
            padding: 1rem 1.1rem 1.1rem 1.1rem !important;
        }}
        div[data-testid="stFormSubmitButton"] button {{
            width: 100%;
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 0.65rem 1rem !important;
            background: linear-gradient(180deg, {ACCENT} 0%, {PRIMARY} 100%) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 2px 8px rgba(15, 41, 66, 0.25);
            margin-top: 0.35rem;
        }}
        div[data-testid="stFormSubmitButton"] button:hover {{
            filter: brightness(1.06);
            box-shadow: 0 4px 12px rgba(15, 41, 66, 0.28);
        }}
        .stDownloadButton button {{
            border-radius: 10px !important;
            font-weight: 600 !important;
            width: 100%;
        }}
        .app-foot {{
            text-align: center;
            font-size: 0.78rem;
            color: {MUTED};
            margin-top: 1.75rem;
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
    </style>
    """,
    unsafe_allow_html=True,
)

LOGO_PATH = "imagens/mitri_logo.png"
SETOR_OPCOES = [
    "Clínica Médica - PS",
    "Diarista - Neurologista",
    "Neurocirurgia",
    "UTI",
]


@st.cache_data(show_spinner=False)
def logo_transparente_png(path: str) -> bytes | None:
    """Remove o fundo claro a partir das bordas (preserva branco interno ao símbolo, ex.: letra M)."""
    if not os.path.isfile(path):
        return None
    try:
        from PIL import Image
    except ImportError:
        return None

    def _claro(r: int, g: int, b: int, lim: int) -> bool:
        return r >= lim and g >= lim and b >= lim

    img = Image.open(path).convert("RGBA")
    px = img.load()
    w, h = img.size
    lim = 245
    visto = set()
    fila = deque()

    for x in range(w):
        for y in (0, h - 1):
            if (x, y) not in visto and _claro(*px[x, y][:3], lim):
                visto.add((x, y))
                fila.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if (x, y) not in visto and _claro(*px[x, y][:3], lim):
                visto.add((x, y))
                fila.append((x, y))

    while fila:
        x, y = fila.popleft()
        r, g, b, a = px[x, y]
        px[x, y] = (r, g, b, 0)
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visto:
                if _claro(*px[nx, ny][:3], lim):
                    visto.add((nx, ny))
                    fila.append((nx, ny))

    out = BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def quebrar_texto(texto: str, limite: int = 88) -> list[str]:
    linhas: list[str] = []
    for bloco in texto.replace("\r\n", "\n").split("\n"):
        if not bloco.strip():
            linhas.append("")
            continue
        palavras = bloco.split()
        linha = ""
        for palavra in palavras:
            candidato = (linha + " " + palavra).strip()
            if len(candidato) <= limite:
                linha = candidato
            else:
                if linha:
                    linhas.append(linha)
                linha = palavra
        if linha:
            linhas.append(linha)
    return linhas if linhas else [""]


def duracao_plantao(d: datetime.date, t_in: time, t_out: time) -> timedelta:
    start = datetime.combine(d, t_in)
    end = datetime.combine(d, t_out)
    if end <= start:
        end += timedelta(days=1)
    return end - start


def fmt_duracao(td: timedelta) -> str:
    total = int(td.total_seconds())
    h, r = divmod(total, 3600)
    m, _ = divmod(r, 60)
    return f"{h:02d}:{m:02d}"


def nome_arquivo_seguro(nome: str, data_fmt: str) -> str:
    base = re.sub(r'[<>:"/\\|?*]', "_", nome).strip() or "documento"
    return f"{base}_{data_fmt.replace('/', '-')}.pdf"


def pdf_nova_pagina(c, W: float, H: float, margem: float, y: float, min_y: float):
    if y >= min_y:
        return y
    c.showPage()
    c.setFillColor(colors.HexColor(PRIMARY))
    c.rect(0, H - 0.35 * cm, W, 0.35 * cm, fill=1, stroke=0)
    return H - margem


# ==================================================
# CABEÇALHO
# ==================================================
hdr_logo, hdr_txt = st.columns([1, 3], vertical_alignment="center")
with hdr_logo:
    _logo_png = logo_transparente_png(LOGO_PATH)
    if _logo_png:
        st.image(BytesIO(_logo_png), width=96)
    elif os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=96)
    else:
        st.caption("Logo: imagens/mitri_logo.png")
with hdr_txt:
    st.markdown(
        f"""
        <div class="app-header-text">
            <p class="app-header-label">Formulário</p>
            <h1>Justificativa de ponto</h1>
            <p class="app-header-hospital">Hospital Regional Sul</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
st.caption("Preencha os campos e gere o PDF para registro no ponto.")

with st.container(border=True):
    with st.form("formulario"):
        st.markdown('<p class="form-section">Identificação</p>', unsafe_allow_html=True)
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            nome = st.text_input("Nome do médico *", placeholder="Nome completo")
        with r1c2:
            crm = st.text_input("CRM *", placeholder="Ex.: 12345 / SP")

        st.markdown('<p class="form-section">Plantão</p>', unsafe_allow_html=True)
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            setor = st.selectbox("Setor *", SETOR_OPCOES)
        with r2c2:
            data = st.date_input("Data do plantão *", format="DD/MM/YYYY")

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            hora_entrada = st.time_input("Entrada *", value=time(7, 0), step=timedelta(minutes=15))
        with r3c2:
            hora_saida = st.time_input("Saída *", value=time(19, 0), step=timedelta(minutes=15))

        st.markdown('<p class="form-section">Justificativa e assinatura</p>', unsafe_allow_html=True)
        motivo = st.text_area(
            "Motivo da justificativa *",
            height=140,
            placeholder="Descreva o motivo com objetividade (ex.: atraso no registro, plantão não batido, correção de horário).",
        )
        assinatura = st.text_input("Nome para assinatura *", placeholder="Igual ao documento oficial / CRM")

        enviar = st.form_submit_button("Gerar PDF")

st.markdown(
    """
    <div class="app-foot">
        Em caso de dúvidas, contate a administração do Hospital Regional Sul.
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# GERAR PDF
# ==================================================
if enviar:
    if not nome or not crm or not motivo.strip() or not assinatura:
        st.error("Preencha todos os campos obrigatórios.")
        st.stop()

    if not os.path.exists(LOGO_PATH):
        st.error(f"Logo não encontrada em: `{LOGO_PATH}`. Coloque o arquivo ou ajuste o caminho.")
        st.stop()

    _logo_bytes = logo_transparente_png(LOGO_PATH)
    if _logo_bytes is None:
        with open(LOGO_PATH, "rb") as _lf:
            _logo_bytes = _lf.read()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    margem = 2 * cm
    min_y_conteudo = 2.8 * cm

    _logo_buf = BytesIO(_logo_bytes)
    ir = ImageReader(_logo_buf)
    iw, ih = ir.getSize()
    if iw <= 0 or ih <= 0:
        iw, ih = 1, 1

    strip_h = 0.42 * cm
    header_band_h = 3.85 * cm
    largura_logo = 4.6 * cm
    altura_logo = largura_logo * (ih / iw)

    band_top = H - strip_h
    band_bot = H - header_band_h

    # Faixa superior (cor institucional)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.rect(0, H - strip_h, W, strip_h, fill=1, stroke=0)

    # Área clara: logo centralizado em X; um pouco mais abaixo na faixa (alinha melhor ao título)
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(0, band_bot, W, header_band_h - strip_h, fill=1, stroke=0)

    y_logo_bottom = (band_top + band_bot) / 2 - altura_logo / 2 - 0.38 * cm
    x_logo = (W - largura_logo) / 2
    _logo_draw = BytesIO(_logo_bytes)
    c.drawImage(
        _logo_draw,
        x_logo,
        y_logo_bottom,
        width=largura_logo,
        height=altura_logo,
        mask="auto",
    )

    # Títulos um pouco mais abaixo da faixa (mais respiro junto ao logo)
    y = band_bot - 1.12 * cm
    c.setFillColor(colors.HexColor(PRIMARY))
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W / 2, y, "FORMULÁRIO DE JUSTIFICATIVA DE PONTO")

    y -= 0.65 * cm
    c.setFont("Helvetica", 9.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(W / 2, y, "Hospital Regional Sul")
    c.setFillColor(colors.black)

    y -= 0.6 * cm
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.75)
    c.line(margem, y, W - margem, y)

    data_fmt = data.strftime("%d/%m/%Y")
    hora_ent = hora_entrada.strftime("%H:%M")
    hora_sai = hora_saida.strftime("%H:%M")
    td = duracao_plantao(data, hora_entrada, hora_saida)
    horas = fmt_duracao(td)

    y -= 1.45 * cm
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(margem, y, "DADOS DO PLANTÃO")
    c.setFillColor(colors.black)
    y -= 0.82 * cm

    label_w = 3.2 * cm
    vx = margem + label_w
    campos_pdf = [
        ("Nome", nome),
        ("CRM", crm),
        ("Setor", setor),
        ("Data", data_fmt),
        ("Horário", f"{hora_ent} às {hora_sai}"),
        ("Duração", f"{horas} (h:min)"),
    ]

    inner_left = margem + 0.35 * cm
    line_extra = 0.38 * cm
    for i, (titulo, valor) in enumerate(campos_pdf):
        linhas_val = quebrar_texto(str(valor), limite=68)
        row_h = max(0.72 * cm, 0.45 * cm + max(0, len(linhas_val) - 1) * line_extra + 0.22 * cm)
        y = pdf_nova_pagina(c, W, H, margem, y, min_y_conteudo + row_h + 0.4 * cm)
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#f8fafc"))
            c.rect(margem, y - row_h + 0.12 * cm, W - 2 * margem, row_h, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor(PRIMARY))
        c.drawString(inner_left, y - 0.45 * cm, titulo)
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        for j, lv in enumerate(linhas_val):
            c.drawString(vx, y - 0.45 * cm - j * line_extra, lv)
        y -= row_h

    y -= 1.05 * cm
    y = pdf_nova_pagina(c, W, H, margem, y, min_y_conteudo + 2 * cm)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(margem, y, "JUSTIFICATIVA")
    c.setFillColor(colors.black)
    y -= 0.62 * cm

    linhas = quebrar_texto(motivo.strip(), limite=86)
    line_height = 13
    pad = 14
    altura_box = len(linhas) * line_height + pad
    y = pdf_nova_pagina(c, W, H, margem, y, min_y_conteudo + altura_box * 0.5)

    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.75)
    c.setFillColor(colors.HexColor("#fafbfc"))
    c.roundRect(margem, y - altura_box, W - 2 * margem, altura_box, 6, stroke=1, fill=1)
    c.setFillColor(colors.black)

    texto = c.beginText(margem + 10, y - 20)
    texto.setFont("Helvetica", 10)
    texto.setLeading(line_height)
    for linha in linhas:
        texto.textLine(linha)
    c.drawText(texto)

    y -= altura_box + 2.35 * cm
    y = pdf_nova_pagina(c, W, H, margem, y, min_y_conteudo + 3.2 * cm)

    sig_h = 3.55 * cm
    sig_left = margem
    sig_w = W - 2 * margem
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.85)
    c.roundRect(sig_left, y - sig_h, sig_w, sig_h, 8, stroke=1, fill=1)

    accent_x = sig_left + 0.35 * cm
    c.setFillColor(colors.HexColor(ACCENT))
    c.rect(accent_x, y - sig_h + 0.38 * cm, 0.12 * cm, sig_h - 0.85 * cm, fill=1, stroke=0)
    c.setFillColor(colors.black)

    tx = sig_left + 0.65 * cm
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawString(tx, y - 0.52 * cm, "Assinatura do médico")
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(tx, y - 0.98 * cm, "Nome completo conforme registro no CRM")
    c.setFillColor(colors.black)

    linha_y = y - 2.58 * cm
    c.setStrokeColor(colors.HexColor(ACCENT))
    c.setLineWidth(1.0)
    line_left = tx
    line_right = sig_left + sig_w - 0.45 * cm
    c.line(line_left, linha_y, line_right, linha_y)
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(0.4)
    c.line(line_left, linha_y - 0.12 * cm, line_right, linha_y - 0.12 * cm)

    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawString(line_left, linha_y + 0.26 * cm, assinatura)

    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(line_left, linha_y - 0.42 * cm, "Assinatura / carimbo quando aplicável")

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(
        W / 2,
        1.2 * cm,
        f"Emitido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
    )

    c.save()
    buffer.seek(0)

    st.success("PDF gerado com sucesso. Use o botão abaixo para baixar.")
    st.download_button(
        "Baixar PDF",
        data=buffer,
        file_name=nome_arquivo_seguro(nome, data_fmt),
        mime="application/pdf",
        type="primary",
    )
