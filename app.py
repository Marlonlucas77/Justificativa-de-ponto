import os
import re
from collections import deque
from datetime import datetime, timedelta, time, timezone
from io import BytesIO
import base64

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

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
SUCCESS = "#166534"
_BRT = timezone(timedelta(hours=-3))

LOGO_PATH = "imagens/mitri_logo.png"

SETOR_OPCOES = [
    "Clínica Médica - PS",
    "Diarista - Neurologista",
    "Neurocirurgia",
    "UTI",
]

# ==================================================
# GOOGLE DRIVE – FUNÇÃO DE UPLOAD
# ==================================================
def upload_pdf_para_drive(pdf_buffer, nome_arquivo):
    creds = Credentials.from_service_account_info(
        st.secrets["gdrive"],
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    service = build("drive", "v3", credentials=creds)

    folder_id = st.secrets["gdrive_settings"]["folder_id"]

    media = MediaIoBaseUpload(
        pdf_buffer,
        mimetype="application/pdf",
        resumable=False
    )

    file_metadata = {
        "name": nome_arquivo,
        "parents": [folder_id]
    }

    service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

# ==================================================
# APP HEADER
# ==================================================
st.markdown("<div style='margin-top:40px'></div>", unsafe_allow_html=True)

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=160)

st.markdown(
    """
    <h3 style="text-align:center; margin-bottom:2px; font-weight:600;">
        FORMULÁRIO DE JUSTIFICATIVA DE PONTO
    </h3>
    <p style="text-align:center; color:#6e6e6e; margin-top:0; font-size:15px;">
        Hospital Regional Sul
    </p>
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
    setor = st.selectbox("Setor *", SETOR_OPCOES)
    data = st.date_input("Data do Plantão *")

    c1, c2 = st.columns(2)
    with c1:
        hora_entrada = st.time_input("Entrada *", value=time(7, 0))
    with c2:
        hora_saida = st.time_input("Saída *", value=time(19, 0))

    motivo = st.text_area("Motivo *", height=150)
    assinatura = st.text_input("Assinatura *")

    enviar = st.form_submit_button("📄 Enviar relatório", use_container_width=True)

# ==================================================
# PDF
# ==================================================
if enviar:
    if not nome or not crm or not motivo or not assinatura:
        st.error("Todos os campos são obrigatórios.")
        st.stop()

    data_fmt = data.strftime("%d/%m/%Y")
    hora_ent = hora_entrada.strftime("%H:%M")
    hora_sai = hora_saida.strftime("%H:%M")

    inicio = datetime.combine(data, hora_entrada)
    fim = datetime.combine(data, hora_saida)
    if fim <= inicio:
        fim += timedelta(days=1)

    duracao = fim - inicio
    horas = f"{duracao.seconds//3600:02d}:{(duracao.seconds%3600)//60:02d}"

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    X = 2 * cm
    y = H - 3 * cm

    if os.path.exists(LOGO_PATH):
        c.drawImage(
            LOGO_PATH,
            (W - 5 * cm) / 2,
            y,
            width=5 * cm,
            preserveAspectRatio=True,
            mask="auto"
        )

    y -= 2.5 * cm
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W / 2, y, "FORMULÁRIO DE JUSTIFICATIVA DE PONTO")

    y -= 0.9 * cm
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, y, "Hospital Regional Sul")

    y -= 0.7 * cm
    c.line(X, y, W - X, y)

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
        y -= 1 * cm

    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(X, y, "Justificativa:")
    y -= 0.8 * cm

    texto = c.beginText(X, y)
    texto.setLeading(14)
    for ln in motivo.split("\n"):
        texto.textLine(ln)
    c.drawText(texto)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(X, 5 * cm, "Assinatura:")
    c.line(X, 4.8 * cm, W - X, 4.8 * cm)
    c.setFont("Helvetica", 11)
    c.drawString(X + 4 * cm, 5 * cm, assinatura)

    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(W / 2, 2 * cm,
        "Documento gerado eletronicamente por sistema interno da instituição."
    )

    c.save()
    buffer.seek(0)

    nome_arquivo = f"justificativa_{nome.replace(' ', '_')}_{data_fmt.replace('/', '-')}.pdf"

    # ✅ ENVIA PARA O GOOGLE DRIVE (ADICIONADO)
    upload_pdf_para_drive(buffer, nome_arquivo)

    buffer.seek(0)

    st.success("✅ Relatório enviado com sucesso!")
    st.download_button(
        "⬇ Baixar PDF",
        data=buffer,
        file_name=nome_arquivo,
        mime="application/pdf",
        use_container_width=True,
    )
