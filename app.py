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
    page_title="Justificativa de Ponto",
    page_icon="📄",
    layout="centered"
)

LOGO_PATH = "imagens/mitri_logo.png"

# ==================================================
# ESTILO PROFISSIONAL
# ==================================================
st.markdown("""
<style>
h1, h2, h3 {text-align:center;}
.stButton>button {
    width:100%;
    background-color:#0e6efd;
    color:white;
    border-radius:8px;
    height:45px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# CABEÇALHO
# ==================================================
if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=140)

st.title("Formulário de Justificativa de Ponto")
st.caption("Hospital Regional Sul")

st.divider()

# ==================================================
# FORMULÁRIO
# ==================================================
with st.form("formulario"):

    col1, col2 = st.columns(2)

    with col1:
        nome = st.text_input("Nome do médico *")
        crm = st.text_input("CRM *")

    with col2:
        setor = st.selectbox(
            "Setor *",
            ["Clínica Médica - PS", "Diarista - Neurologista", "Neurocirurgia", "UTI"]
        )
        data = st.date_input("Data do Plantão *")

    c1, c2 = st.columns(2)
    with c1:
        hora_entrada = st.time_input("Entrada", value=time(7, 0))
    with c2:
        hora_saida = st.time_input("Saída", value=time(19, 0))

    motivo = st.text_area("Motivo da justificativa *", height=120)

    assinatura = st.text_input("Nome para assinatura *")

    enviar = st.form_submit_button("📄 Gerar PDF")

# ==================================================
# FUNÇÃO PARA QUEBRAR TEXTO (PDF)
# ==================================================
def quebrar_texto(texto, limite=90):
    linhas = []
    palavras = texto.split()
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
# GERAÇÃO DO PDF PROFISSIONAL
# ==================================================
if enviar:

    if not nome or not crm or not motivo or not assinatura:
        st.error("Preencha todos os campos obrigatórios.")
        st.stop()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4

    margem = 2 * cm
    y = H - 2.5 * cm

    # LOGO
    if os.path.exists(LOGO_PATH):
        c.drawImage(LOGO_PATH, margem, y, width=4*cm, preserveAspectRatio=True)
    
    # TÍTULO
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, y, "FORMULÁRIO DE JUSTIFICATIVA DE PONTO")

    y -= 1.2 * cm
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, y, "Hospital Regional Sul")

    y -= 0.5 * cm
    c.line(margem, y, W - margem, y)

    # DADOS
    data_fmt = data.strftime("%d/%m/%Y")
    hora_ent = hora_entrada.strftime("%H:%M")
    hora_sai = hora_saida.strftime("%H:%M")

    duracao = datetime.combine(data, hora_saida) - datetime.combine(data, hora_entrada)
    horas = f"{duracao.seconds//3600:02d}:{(duracao.seconds%3600)//60:02d}"

    y -= 1.2 * cm
    c.setFont("Helvetica", 11)

    campos = [
        ("Nome", nome),
        ("CRM", crm),
        ("Setor", setor),
        ("Data", data_fmt),
        ("Horário", f"{hora_ent} às {hora_sai}"),
        ("Duração", horas),
    ]

    for titulo, valor in campos:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margem, y, f"{titulo}:")
        c.setFont("Helvetica", 10)
        c.drawString(margem + 4*cm, y, valor)
        y -= 0.8 * cm

    # CAIXA JUSTIFICATIVA
    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem, y, "Justificativa:")

    y -= 0.5 * cm

    linhas = quebrar_texto(motivo, 90)

    altura_box = len(linhas) * 14 + 10

    c.rect(margem, y - altura_box, W - 2*margem, altura_box)

    texto = c.beginText(margem + 5, y - 15)
    texto.setFont("Helvetica", 10)

    for linha in linhas:
        texto.textLine(linha)

    c.drawText(texto)

    # ASSINATURA
    y -= altura_box + 2 * cm

    c.drawString(margem, y, "Assinatura:")
    c.line(margem, y - 5, W - margem, y - 5)

    c.drawString(margem + 5*cm, y, assinatura)

    # RODAPÉ
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(W/2, 2*cm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    c.save()
    buffer.seek(0)

    st.success("PDF gerado com sucesso!")

    st.download_button(
        "⬇️ Baixar PDF",
        data=buffer,
        file_name=f"{nome}-{data_fmt}.pdf",
        mime="application/pdf"
    )
