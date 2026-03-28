import streamlit as st
from datetime import datetime, time
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from io import BytesIO
import os

# ==================================================
# CONFIGURAÇÃO DA PÁGINA
# ==================================================
st.set_page_config(
    page_title="Formulário de Justificativa de Ponto",
    layout="centered"
)

# ==================================================
# RESET VISUAL FORÇADO (ANTI-CACHE)
# ==================================================
st.markdown(
    """
    <style>
        header, footer {display:none !important;}
        .block-container {padding-top: 0px !important;}
        body {margin-top: 0px !important;}
    </style>
    """,
    unsafe_allow_html=True
)

LOGO_PATH = "imagens/mitri_logo.png"

# ==================================================
# CABEÇALHO FIXO E CENTRALIZADO
# ==================================================
st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=160)

st.markdown(
    """
    <div style="text-align:center; margin-top:18px;">
        <div style="font-size:20px; font-weight:600;">
            FORMULÁRIO DE JUSTIFICATIVA DE PONTO
        </div>
        <div style="font-size:15px; color:#6e6e6e; margin-top:2px;">
            Hospital Regional Sul
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<hr style='margin-top:25px;'>", unsafe_allow_html=True)

# ==================================================
# FORMULÁRIO
# ==================================================
with st.form("formulario"):
    nome = st.text_input("Nome do médico *")
    crm = st.text_input("CRM *")
    setor = st.selectbox(
        "Setor *",
        ["Clínica Médica - PS", "Diarista - Neurologista", "Neurocirurgia", "UTI"]
    )
    data = st.date_input("Data do Plantão *")

    c1, c2 = st.columns(2)
    with c1:
        hora_entrada = st.time_input("Horário de Entrada *", value=time(7, 0))
    with c2:
        hora_saida = st.time_input("Horário de Saída *", value=time(19, 0))

    motivo = st.text_area("Motivo da justificativa *", height=120)
    assinatura = st.text_input("Assinatura *")

    enviar = st.form_submit_button("✅ Gerar PDF")

# ==================================================
# PDF – LAYOUT PROFISSIONAL DEFINITIVO
# ==================================================
if enviar:
    if not nome or not crm or not motivo or not assinatura:
        st.error("Preencha todos os campos obrigatórios.")
        st.stop()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    X = 1 * cm
    y = H - 2 * cm

    if os.path.exists(LOGO_PATH):
        c.drawImage(
            LOGO_PATH,
            (W - 5*cm)/2,
            y,
            width=5*cm,
            preserveAspectRatio=True,
            mask="auto"
        )

    y -= 2.5 * cm
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W/2, y, "FORMULÁRIO DE JUSTIFICATIVA DE PONTO")

    y -= 0.9 * cm
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, y, "Hospital Regional Sul")

    y -= 0.7 * cm
    c.line(X, y, W-X, y)

    data_fmt = data.strftime("%d/%m/%Y")
    hora_ent = hora_entrada.strftime("%H:%M")
    hora_sai = hora_saida.strftime("%H:%M")
    duracao = datetime.combine(data, hora_saida) - datetime.combine(data, hora_entrada)
    horas = f"{duracao.seconds//3600:02d}:{(duracao.seconds%3600)//60:02d}"

    y -= 1.4 * cm
    c.setFont("Helvetica", 11)

    for campo in [
        f"Nome: {nome}",
        f"CRM: {crm}",
        f"Setor: {setor}",
        f"Data do plantão: {data_fmt}",
        f"Horário: {hora_ent} - {hora_sai}",
        f"Duração: {horas}",
    ]:
        c.drawString(X, y, campo)
        y -= 1*cm

    y -= 0.5*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(X, y, "Justificativa:")
    y -= 0.8*cm

    texto = c.beginText(X, y)
    texto.setLeading(14)
    for linha in motivo.split("\n"):
        texto.textLine(linha)
    c.drawText(texto)

    c.drawString(X, 5*cm, "Assinatura:")
    c.line(X, 4.8*cm, W-X, 4.8*cm)
    c.drawString(X+4*cm, 5*cm, assinatura)

    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(W/2, 2*cm, "Documento gerado eletronicamente por sistema interno.")

    c.save()
    buffer.seek(0)

    st.download_button(
        "⬇️ Baixar PDF",
        data=buffer,
        file_name=f"{nome}-{data_fmt}.pdf",
        mime="application/pdf"
    )

