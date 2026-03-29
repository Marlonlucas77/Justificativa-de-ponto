import streamlit as st
from datetime import datetime, time, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO
import os

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(
    page_title="Justificativa de Ponto",
    page_icon="📄",
    layout="centered"
)

LOGO_PATH = "imagens/mitri_logo.png"

# ==================================================
# HEADER (LOGO + TEXTO)
# ==================================================
col1, col2 = st.columns([1, 4], vertical_alignment="center")

with col1:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=120)  # 🔥 LOGO MAIOR

with col2:
    st.markdown("""
    <h2 style="margin-bottom:5px;">Justificativa de Ponto</h2>
    <p style="margin:0; color:gray;">Hospital Regional Sul</p>
    """, unsafe_allow_html=True)

st.divider()

# ==================================================
# FORMULÁRIO
# ==================================================
with st.form("formulario"):

    c1, c2 = st.columns(2)

    with c1:
        nome = st.text_input("Nome do médico *")
        crm = st.text_input("CRM *")

    with c2:
        setor = st.selectbox(
            "Setor *",
            ["Clínica Médica - PS", "Diarista - Neurologista", "Neurocirurgia", "UTI"]
        )
        data = st.date_input("Data *")

    c3, c4 = st.columns(2)

    with c3:
        entrada = st.time_input("Entrada", value=time(7, 0))

    with c4:
        saida = st.time_input("Saída", value=time(19, 0))

    motivo = st.text_area("Motivo *", height=120)

    assinatura = st.text_input("Nome para assinatura *")

    enviar = st.form_submit_button("Gerar PDF")

# ==================================================
# FUNÇÕES
# ==================================================
def calcular_duracao(data, inicio, fim):
    ini = datetime.combine(data, inicio)
    f = datetime.combine(data, fim)
    if f <= ini:
        f += timedelta(days=1)
    return f - ini

def formatar_duracao(td):
    h = td.seconds // 3600
    m = (td.seconds % 3600) // 60
    return f"{h:02d}:{m:02d}"

def quebrar_texto(texto, limite=90):
    palavras = texto.split()
    linhas = []
    linha = ""

    for palavra in palavras:
        if len(linha + palavra) < limite:
            linha += palavra + " "
        else:
            linhas.append(linha)
            linha = palavra + " "

    linhas.append(linha)
    return linhas

# ==================================================
# GERAR PDF
# ==================================================
if enviar:

    if not nome or not crm or not motivo or not assinatura:
        st.error("Preencha todos os campos obrigatórios.")
        st.stop()

    if not os.path.exists(LOGO_PATH):
        st.error("Logo não encontrada na pasta imagens.")
        st.stop()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4

    margem = 2 * cm

    # =========================================
    # CABEÇALHO (FUNDO BRANCO)
    # =========================================
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1)

    # LOGO CENTRAL
    largura_logo = 5 * cm
    c.drawImage(
        LOGO_PATH,
        (W - largura_logo) / 2,
        H - 4 * cm,
        width=largura_logo,
        preserveAspectRatio=True
    )

    # TÍTULO
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, H - 5.2 * cm, "JUSTIFICATIVA DE PONTO")

    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, H - 5.8 * cm, "Hospital Regional Sul")

    # LINHA
    c.line(margem, H - 6.2 * cm, W - margem, H - 6.2 * cm)

    # =========================================
    # DADOS
    # =========================================
    y = H - 7.2 * cm

    data_fmt = data.strftime("%d/%m/%Y")
    duracao = calcular_duracao(data, entrada, saida)
    duracao_fmt = formatar_duracao(duracao)

    campos = [
        ("Nome", nome),
        ("CRM", crm),
        ("Setor", setor),
        ("Data", data_fmt),
        ("Horário", f"{entrada.strftime('%H:%M')} às {saida.strftime('%H:%M')}"),
        ("Duração", duracao_fmt),
    ]

    for titulo, valor in campos:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margem, y, f"{titulo}:")
        c.setFont("Helvetica", 11)
        c.drawString(margem + 4*cm, y, str(valor))
        y -= 0.8 * cm

    # =========================================
    # JUSTIFICATIVA
    # =========================================
    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem, y, "Justificativa:")

    y -= 0.5 * cm

    linhas = quebrar_texto(motivo)
    altura = len(linhas) * 14 + 20

    c.rect(margem, y - altura, W - 2*margem, altura)

    txt = c.beginText(margem + 5, y - 15)
    txt.setFont("Helvetica", 11)

    for linha in linhas:
        txt.textLine(linha)

    c.drawText(txt)

    # =========================================
    # ASSINATURA
    # =========================================
    y -= altura + 2 * cm

    c.drawString(margem, y, "Assinatura:")
    c.line(margem, y - 5, W - margem, y - 5)
    c.drawString(margem + 5*cm, y, assinatura)

    # RODAPÉ
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(
        W/2,
        2*cm,
        f"Emitido em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    c.save()
    buffer.seek(0)

    st.success("PDF gerado com sucesso!")

    st.download_button(
        "⬇ Baixar PDF",
        buffer,
        file_name=f"{nome}.pdf",
        mime="application/pdf"
    )
