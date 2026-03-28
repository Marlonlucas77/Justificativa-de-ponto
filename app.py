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

LOGO_PATH = "imagens/mitri_logo.png"

# ==================================================
# CABEÇALHO – TELA INICIAL (PROFISSIONAL)
# ==================================================
with st.container():
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=160)

    st.markdown(
        """
        <h3 style="text-align:center; margin-bottom:4px; font-weight:600;">
            FORMULÁRIO DE JUSTIFICATIVA DE PONTO
        </h3>
        <p style="text-align:center; color:gray; margin-top:0; font-size:15px;">
            Hospital Regional Sul
        </p>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

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

    col1, col2 = st.columns(2)
    with col1:
        hora_entrada = st.time_input("Horário de Entrada *", value=time(7, 0))
    with col2:
        hora_saida = st.time_input("Horário de Saída *", value=time(19, 0))

    motivo = st.text_area("Motivo da justificativa *", height=120)
    assinatura = st.text_input("Assinatura *")

    enviar = st.form_submit_button("✅ Gerar PDF")

# ==================================================
# PROCESSAMENTO E PDF
# ==================================================
if enviar:
    if not nome or not crm or not motivo or not assinatura:
        st.error("❌ Preencha todos os campos obrigatórios.")
        st.stop()

    data_fmt = data.strftime("%d/%m/%Y")
    hora_ent = hora_entrada.strftime("%H:%M")
    hora_sai = hora_saida.strftime("%H:%M")

    duracao = datetime.combine(data, hora_saida) - datetime.combine(data, hora_entrada)
    horas = f"{duracao.seconds // 3600:02d}:{(duracao.seconds % 3600) // 60:02d}"

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    X = 2 * cm
    y = H - 2 * cm

    # LOGO CENTRALIZADO NO PDF
    if os.path.exists(LOGO_PATH):
        c.drawImage(
            LOGO_PATH,
            (W - 5 * cm) / 2,
            y,
            width=5 * cm,
            preserveAspectRatio=True,
            mask="auto"
        )

    # TÍTULO PDF
    y -= 2.4 * cm
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(
        W / 2,
        y,
        "FORMULÁRIO DE JUSTIFICATIVA DE PONTO"
    )

    y -= 0.8 * cm
    c.setFont("Helvetica", 10)
    c.drawCentredString(
        W / 2,
        y,
        "Hospital Regional Sul"
    )

    y -= 0.6 * cm
    c.line(2 * cm, y, W - 2 * cm, y)

    # DADOS
    y -= 1.2 * cm
    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, y, f"Nome: {nome}")
    y -= 0.9 * cm
    c.drawString(2 * cm, y, f"CRM: {crm}")
    y -= 0.9 * cm
    c.drawString(2 * cm, y, f"Setor: {setor}")
    y -= 0.9 * cm
    c.drawString(2 * cm, y, f"Data do plantão: {data_fmt}")
    y -= 0.9 * cm
    c.drawString(2 * cm, y, f"Horário: {hora_ent} - {hora_sai}")
    y -= 0.9 * cm
    c.drawString(2 * cm, y, f"Duração: {horas}")

    # JUSTIFICATIVA
    y -= 1.3 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Justificativa:")
    y -= 0.8 * cm

    c.setFont("Helvetica", 11)
    texto = c.beginText(2 * cm, y)
    texto.setLeading(14)
    for linha in motivo.split("\n"):
        texto.textLine(linha)
    c.drawText(texto)

    # ASSINATURA
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, 5 * cm, "Assinatura:")
    c.setFont("Helvetica", 11)
    c.drawString(6 * cm, 5 * cm, assinatura)
    c.line(2 * cm, 4.8 * cm, W - 2 * cm, 4.8 * cm)

    # RODAPÉ
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(
        W / 2,
        2 * cm,
        "Documento gerado eletronicamente por sistema interno da instituição."
    )

    c.save()
    buffer.seek(0)

    nome_arquivo = f"Justificativa_{nome.replace(' ', '_')}_{data.strftime('%Y%m%d')}.pdf"

    st.success("✅ PDF gerado corretamente!")
    st.download_button(
        "⬇️ Baixar PDF",
        data=buffer,
        file_name=nome_arquivo,
        mime="application/pdf"
    )
