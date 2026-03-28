import streamlit as st
from streamlit_drawable_canvas import st_canvas
from datetime import datetime, time
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
import os

# ==================================================
# CONFIGURAÇÕES (COMPATÍVEL COM STREAMLIT CLOUD)
# ==================================================
BASE_DIR = "."
PASTA_BASE = "temp"
PLANILHA_PATH = os.path.join(PASTA_BASE, "registros.xlsx")
LOGO_PATH = os.path.join("imagens", "mitri_logo.png")

os.makedirs(PASTA_BASE, exist_ok=True)

SETORES = [
    "Clínica Médica - PS",
    "Diarista - Neurologista",
    "Neurocirurgia",
    "UTI"
]

for setor in SETORES:
    os.makedirs(os.path.join(PASTA_BASE, setor), exist_ok=True)

st.set_page_config(
    page_title="Justificativa de Ponto",
    layout="centered"
)

# ==================================================
# CABEÇALHO DO FORMULÁRIO
# ==================================================
col_logo, col_text = st.columns([1, 6])

with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=90)

with col_text:
    st.markdown("### **FORMULÁRIO DE JUSTIFICATIVA DO PONTO**")
    st.markdown(
        "<span style='color:gray'>Hospital Regional Sul</span>",
        unsafe_allow_html=True
    )

st.markdown("---")

# ==================================================
# FUNÇÃO PLANILHA (MANTIDA)
# ==================================================
def registrar_planilha(dados):
    headers = [
        "Nome dos Médicos",
        "Horas de Plantão",
        "Data do Plantão",
        "Horário de Entrada",
        "Horário de Saída",
        "Ocupação",
        "Motivo"
    ]

    novo = not os.path.exists(PLANILHA_PATH)

    if novo:
        wb = Workbook()
        ws = wb.active
        ws.title = "Relatório"

        ws.merge_cells("A1:G1")
        ws["A1"] = "RELATÓRIO DE JUSTIFICATIVAS DE PLANTÃO"
        ws["A1"].font = Font(bold=True, size=14)
        ws["A1"].alignment = Alignment(horizontal="center")

        for i, h in enumerate(headers, start=1):
            c = ws.cell(row=3, column=i, value=h)
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="D9D9D9")
            c.border = Border(*(Side(style="thin"),)*4)

        wb.save(PLANILHA_PATH)

    wb = load_workbook(PLANILHA_PATH)
    ws = wb.active
    r = ws.max_row + 1

    valores = [
        dados["Nome dos Médicos"],
        dados["Horas de Plantão"],
        dados["Data do Plantão"],
        dados["Horário de Entrada"],
        dados["Horário de Saída"],
        dados["Ocupação"],
        dados["Motivo"],
    ]

    for i, v in enumerate(valores, start=1):
        cell = ws.cell(row=r, column=i, value=v)
        cell.border = Border(*(Side(style="thin"),)*4)

    wb.save(PLANILHA_PATH)

# ==================================================
# FORMULÁRIO
# ==================================================
with st.form("formulario"):
    nome = st.text_input("Nome do médico *")
    crm = st.text_input("CRM *")
    ocupacao = st.selectbox("Setor *", SETORES)
    data = st.date_input("Data do Plantão *", format="DD/MM/YYYY")

    c1, c2 = st.columns(2)
    with c1:
        hora_entrada = st.time_input("Horário de Entrada *", value=time(7, 0))
    with c2:
        hora_saida = st.time_input("Horário de Saída *", value=time(19, 0))

    motivo = st.text_area("Motivo *", height=120)
    assinatura = st.text_input("Assinatura *")

    enviar = st.form_submit_button("✅ Gerar documento")

# ==================================================
# GOOGLE DRIVE - CONFIGURAÇÃO
# ==================================================
PASTAS_SETOR = {
    "Clínica Médica - PS": "1ng6xrCZZPcuasV9HwyMRTk8JZXHsoqJ",
    "Diarista - Neurologista": "1B0xRIkghWujIeDUOQeVlstrplufr0a",
    "Neurocirurgia": "1zTTrnf3Jvi-4tEGw7AqUbC0AUm-HZCRY",
    "UTI": "1NusTpQs-Zv1c6W_gr5j5gNQhSN2dd",
}

def upload_pdf_para_drive(caminho_pdf, nome_pdf, setor):
    try:
        if "gdrive" not in st.secrets:
            st.error("❌ Secret gdrive não encontrado.")
            return

        creds = Credentials.from_service_account_info(
            st.secrets["gdrive"],
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = build("drive", "v3", credentials=creds)

        pasta_id = PASTAS_SETOR.get(setor)
        if not pasta_id:
            st.error("❌ Setor não mapeado no Drive.")
            return

        media = MediaFileUpload(caminho_pdf, mimetype="application/pdf")
        drive.files().create(
            body={"name": nome_pdf, "parents": [pasta_id]},
            media_body=media,
            fields="id"
        ).execute()

    except Exception as e:
        st.error("❌ Erro ao enviar PDF para o Google Drive")
        st.code(str(e))

# ==================================================
# PROCESSAMENTO
# ==================================================
if enviar:
    if not nome or not crm or not motivo:
        st.error("Preencha todos os campos obrigatórios.")
        st.stop()

    data_fmt = data.strftime("%d/%m/%Y")
    data_arq = data.strftime("%d-%m-%Y")
    hora_ent = hora_entrada.strftime("%H:%M")
    hora_sai = hora_saida.strftime("%H:%M")

    dur = datetime.combine(data, hora_saida) - datetime.combine(data, hora_entrada)
    horas = f"{dur.seconds//3600:02d}:{(dur.seconds%3600)//60:02d}"

    pasta = os.path.join(PASTA_BASE, ocupacao)
    pdf_path = os.path.join(pasta, f"{nome} - {data_arq}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    W, H = A4
    X = 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, H-7*cm,
        "FORMULÁRIO DE JUSTIFICATIVA DO PONTO – HOSPITAL REGIONAL SUL")
    c.line(X, H-8.2*cm, W-X, H-8.2*cm)

    y = H-10*cm
    c.setFont("Helvetica", 10)
    c.drawString(X, y, f"Nome: {nome}")
    c.drawString(X, y-1*cm, f"CRM: {crm}")
    c.drawString(X, y-2*cm, f"Setor: {ocupacao}")
    c.drawString(X, y-3*cm, f"Data: {data_fmt}")
    c.drawString(X, y-4*cm, f"Horário: {hora_ent} - {hora_sai}")

    c.drawString(X, y-6*cm, "Justificativa:")
    txt = c.beginText(X, y-7*cm)
    txt.textLine(motivo)
    c.drawText(txt)

    c.drawString(X, 6*cm, "Assinatura:")
    c.drawString(X+3*cm, 6*cm, assinatura)

    c.save()

    upload_pdf_para_drive(
        pdf_path,
        f"{nome} - {data_arq}.pdf",
        ocupacao
    )

    registrar_planilha({
        "Nome dos Médicos": nome,
        "Horas de Plantão": horas,
        "Data do Plantão": data_fmt,
        "Horário de Entrada": hora_ent,
        "Horário de Saída": hora_sai,
        "Ocupação": ocupacao,
        "Motivo": motivo
    })

    st.success("✅ Documento gerado e salvo no Google Drive com sucesso!")
