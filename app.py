import os
import re
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
        .app-hero {{
            background: linear-gradient(180deg, #ffffff 0%, {SURFACE} 100%);
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 1.35rem 1.6rem 1.55rem 1.6rem;
            margin-bottom: 1.35rem;
            box-shadow: 0 1px 3px rgba(15, 41, 66, 0.06), 0 8px 24px rgba(15, 41, 66, 0.06);
            text-align: center;
        }}
        .app-hero .hero-text {{
            max-width: 34rem;
            margin: 0 auto;
        }}
        .app-hero h1 {{
            font-size: 1.4rem !important;
            font-weight: 700 !important;
            color: {PRIMARY} !important;
            margin: 0 0 0.35rem 0 !important;
            letter-spacing: -0.03em;
            line-height: 1.2;
        }}
        .app-hero p {{
            margin: 0 !important;
            color: {MUTED};
            font-size: 0.92rem;
            line-height: 1.45;
        }}
        .app-hero .tag {{
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: {ACCENT};
            background: rgba(30, 74, 110, 0.08);
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            margin-bottom: 0.65rem;
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
_, hero_logo, _ = st.columns([1, 2, 1])
with hero_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=172)
    else:
        st.caption("Logo: imagens/mitri_logo.png")

st.markdown(
    f"""
    <div class="app-hero">
        <div class="hero-text">
            <span class="tag">Recursos humanos</span>
            <h1>Justificativa de ponto</h1>
            <p>Hospital Regional Sul — preencha os campos, confira os dados e gere o PDF para registro no ponto.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
        Hospital Regional Sul — formulário para uso interno. Em caso de dúvidas, contate a administração.
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

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    margem = 2 * cm
    min_y_conteudo = 2.8 * cm

    ir = ImageReader(LOGO_PATH)
    iw, ih = ir.getSize()
    if iw <= 0 or ih <= 0:
        iw, ih = 1, 1

    strip_h = 0.42 * cm
    header_band_h = 3.65 * cm
    largura_logo = 4.6 * cm
    altura_logo = largura_logo * (ih / iw)

    band_top = H - strip_h
    band_bot = H - header_band_h

    # Faixa superior (cor institucional)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.rect(0, H - strip_h, W, strip_h, fill=1, stroke=0)

    # Área clara: logo centralizado no topo (horizontal e vertical na faixa)
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(0, band_bot, W, header_band_h - strip_h, fill=1, stroke=0)

    y_logo_bottom = (band_top + band_bot) / 2 - altura_logo / 2
    x_logo = (W - largura_logo) / 2
    c.drawImage(
        LOGO_PATH,
        x_logo,
        y_logo_bottom,
        width=largura_logo,
        height=altura_logo,
        mask="auto",
    )

    # Títulos logo abaixo da faixa do logo (alinha ao centro da página)
    y = band_bot - 0.95 * cm
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

    y -= 1.15 * cm
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(margem, y, "DADOS DO PLANTÃO")
    c.setFillColor(colors.black)
    y -= 0.55 * cm

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

    y -= 0.35 * cm
    y = pdf_nova_pagina(c, W, H, margem, y, min_y_conteudo + 2 * cm)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(margem, y, "JUSTIFICATIVA")
    c.setFillColor(colors.black)
    y -= 0.5 * cm

    linhas = quebrar_texto(motivo.strip(), limite=86)
    line_height = 13
    pad = 12
    altura_box = len(linhas) * line_height + pad
    y = pdf_nova_pagina(c, W, H, margem, y, min_y_conteudo + altura_box * 0.5)

    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.8)
    c.roundRect(margem, y - altura_box, W - 2 * margem, altura_box, 4, stroke=1, fill=0)

    texto = c.beginText(margem + 8, y - 18)
    texto.setFont("Helvetica", 10)
    texto.setLeading(line_height)
    for linha in linhas:
        texto.textLine(linha)
    c.drawText(texto)

    y -= altura_box + 1.8 * cm
    y = pdf_nova_pagina(c, W, H, margem, y, min_y_conteudo + 2.2 * cm)

    sig_h = 2.0 * cm
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.6)
    c.roundRect(margem, y - sig_h, W - 2 * margem, sig_h, 5, stroke=1, fill=1)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawString(margem + 0.4 * cm, y - 0.45 * cm, "Assinatura do médico")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(margem + 0.4 * cm, y - 0.85 * cm, "Nome completo conforme registro profissional")
    c.setFillColor(colors.black)
    linha_y = y - 1.45 * cm
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(0.5)
    line_left = margem + 0.45 * cm
    line_right = W - margem - 0.45 * cm
    c.line(line_left, linha_y, line_right, linha_y)
    c.setFont("Helvetica", 10)
    c.drawString(line_left, linha_y + 0.22 * cm, assinatura)

    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(margem, 1.25 * cm, "Hospital Regional Sul — uso interno")
    c.drawRightString(W - margem, 1.25 * cm, f"Emitido em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

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
