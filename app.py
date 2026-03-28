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
# CONFIGURAÇÕES
# ==================================================
BASE_DIR = r"C:\Users\MarlonLucasRocha\OneDrive - Santa Casa de Misericórdia de Chavantes\PROJETO PYTHON"
PASTA_BASE = os.path.join(BASE_DIR, "justificativas")
PLANILHA_PATH = os.path.join(PASTA_BASE, "registros.xlsx")
LOGO_PATH = os.path.join(BASE_DIR, "imagens", "mitri_logo.png")

SETORES = [
    "Clínica Médica - PS",
    "Diarista - Neurologista",
    "Neurocirurgia",
    "UTI"
]

for setor in SETORES:
    os.makedirs(os.path.join(PASTA_BASE, setor), exist_ok=True)

st.set_page_config(page_title="Justificativa de Ponto", layout="centered")

# ==================================================
# CABEÇALHO DO FORMULÁRIO
# ==================================================
col_logo, col_text = st.columns([1, 6])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=90)
with col_text:
    st.markdown("### **FORMULÁRIO DE JUSTIFICATIVA DO PONTO**")
    st.markdown("<span style='color:gray'>Hospital Regional Sul</span>", unsafe_allow_html=True)
st.markdown("---")

# ==================================================
# FUNÇÃO PLANILHA (BONITA)
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

    nova = not os.path.exists(PLANILHA_PATH)

    if nova:
        wb = Workbook()
        ws = wb.active
        ws.title = "Relatório"

        if os.path.exists(LOGO_PATH):
            img = XLImage(LOGO_PATH)
            img.width = 160
            img.height = 70
            ws.add_image(img, "A1")

        ws.merge_cells("B2:H3")
        t = ws["B2"]
        t.value = "RELATÓRIO DE JUSTIFICATIVAS DE PLANTÃO\nHOSPITAL REGIONAL SUL"
        t.font = Font(size=14, bold=True)
        t.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        header_fill = PatternFill("solid", fgColor="D9D9D9")
        border = Border(*(Side(style="thin"),)*4)

        for col, h in enumerate(headers, start=1):
            cell = ws.cell(row=5, column=col, value=h)
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = border

        wb.save(PLANILHA_PATH)

    wb = load_workbook(PLANILHA_PATH)
    ws = wb.active
    row = ws.max_row + 1

    for col, h in enumerate(headers, start=1):
        ws.cell(row=row, column=col, value=dados[h]).border = Border(*(Side(style="thin"),)*4)

    for i in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 24

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
# GOOGLE DRIVE - CONFIGURAÇÃO (ADICIONADO)
# ==================================================
PASTAS_SETOR = {
    "Clínica Médica - PS": "1ng6xrCZZPcuasV9HwyMRTk8JZXHsoqJ",
    "Diarista - Neurologista": "1B0xRIkghWujIeDUOQeVlstrplufr0a",
    "Neurocirurgia": "1zTTrnf3Jvi-4tEGw7AqUbC0AUm-HZCRY",
    "UTI": "1NusTpQs-Zv1c6W_gr5j5gNQhSN2dd",
}

creds = Credentials.from_service_account_info(
    st.secrets["gdrive"],
    scopes=["https://www.googleapis.com/auth/drive"]
)

drive_service = build("drive", "v3", credentials=creds)

def upload_pdf_para_drive(caminho_pdf, nome_arquivo, setor):
    pasta_id = PASTAS_SETOR.get(setor)
    media = MediaFileUpload(caminho_pdf, mimetype="application/pdf")
    drive_service.files().create(
        body={"name": nome_arquivo, "parents": [pasta_id]},
        media_body=media,
        fields="id"
    ).execute()

# ==================================================
# PROCESSAMENTO
# ==================================================
if enviar:
    if not nome or not crm or not motivo:
        st.error("Preencha todos os campos obrigatórios.")
        st.stop()

    data_fmt = data.strftime("%d/%m/%Y")
    data_arquivo = data.strftime("%d-%m-%Y")
    hora_ent = hora_entrada.strftime("%H:%M")
    hora_sai = hora_saida.strftime("%H:%M")

    duracao = datetime.combine(data, hora_saida) - datetime.combine(data, hora_entrada)
    horas_formatadas = f"{duracao.seconds//3600:02d}:{(duracao.seconds%3600)//60:02d}"

    pasta_setor = os.path.join(PASTA_BASE, ocupacao)
    os.makedirs(pasta_setor, exist_ok=True)
    pdf_path = os.path.join(pasta_setor, f"{nome} - {data_arquivo}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    W, H = A4
    X = 2 * cm
    COR_PRINCIPAL = colors.HexColor("#030D0C")

    if os.path.exists(LOGO_PATH):
        c.drawImage(LOGO_PATH, (W - 6 * cm) / 2, H - 7 * cm, width=6 * cm)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 7 * cm,
        "FORMULÁRIO DE JUSTIFICATIVA DO PONTO – HOSPITAL REGIONAL SUL")
    c.line(X, H - 8.2 * cm, W - X, H - 8.2 * cm)

    c.setFont("Helvetica", 10)
    y = H - 10 * cm
    c.drawString(X, y, f"Nome: {nome}")
    c.drawString(X, y - 1 * cm, f"CRM: {crm}")
    c.drawString(X, y - 2 * cm, f"Setor: {ocupacao}")
    c.drawString(X, y - 3 * cm, f"Data: {data_fmt}")
    c.drawString(X, y - 4 * cm, f"Horário: {hora_ent} - {hora_sai}")

    c.drawString(X, y - 6 * cm, "Justificativa:")
    text = c.beginText(X, y - 7 * cm)
    text.textLine(motivo)
    c.drawText(text)

    c.drawString(X, 6 * cm, "Assinatura:")
    c.drawString(X + 3 * cm, 6 * cm, assinatura)

    c.save()

    # ✅ UPLOAD PARA O GOOGLE DRIVE (ADICIONADO)
    upload_pdf_para_drive(
        pdf_path,
        f"{nome} - {data_arquivo}.pdf",
        ocupacao
    )

    registrar_planilha({
        "Nome dos Médicos": nome,
        "Horas de Plantão": horas_formatadas,
        "Data do Plantão": data_fmt,
        "Horário de Entrada": hora_ent,
        "Horário de Saída": hora_sai,
        "Ocupação": ocupacao,
        "Motivo": motivo
    })

    st.success("✅ Documento gerado e salvo no Google Drive com sucesso!")
