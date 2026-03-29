import os
import re
from collections import deque
from datetime import datetime, timedelta, time, timezone
from io import BytesIO
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
PRIMARY  = "#0f2942"
ACCENT   = "#1e4a6e"
MUTED    = "#64748b"
SURFACE  = "#f8fafc"
BORDER   = "#e2e8f0"
SECTION  = "#94a3b8"
SUCCESS  = "#166534"
_BRT     = timezone(timedelta(hours=-3))
LOGO_PATH = "imagens/mitri_logo.png"
# Escopos necessários para Drive e Sheets
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
@st.cache_data(show_spinner=False)
def _cor_dominante_logo(path: str) -> str:
    try:
        from PIL import Image
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
            flex-direction: row;
            align-items: center;
            gap: 1.4rem;
            margin-bottom: 1.4rem;
            padding: 1.4rem 1.8rem;
            background: linear-gradient(160deg, {PRIMARY} 0%, {ACCENT} 100%);
            border-radius: 16px;
            box-shadow: 0 6px 20px rgba(15,41,66,.26);
        }}
        .app-header-logo {{
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .app-header-divider {{
            width: 1.5px;
            height: 64px;
            background: rgba(255,255,255,.22);
            flex-shrink: 0;
        }}
        .app-header-text {{
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }}
        .app-header-text h1 {{
            font-size: 1.5rem !important;
            font-weight: 800 !important;
            color: #fff !important;
            margin: 0 !important;
            letter-spacing: -0.025em;
            line-height: 1.15;
        }}
        .app-header-text .app-header-sub {{
            margin: 0 !important;
            font-size: 0.85rem;
            font-weight: 400;
            color: rgba(255,255,255,.55);
            letter-spacing: 0.04em;
            text-transform: uppercase;
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
        /* ── Rodapé ── */
        .app-foot {{
            text-align: center;
            font-size: 0.76rem;
            color: {MUTED};
            margin-top: 2rem;
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
    total = int(td.total_seconds())
    h, r  = divmod(total, 3600)
    m, _  = divmod(r, 60)
    return f"{h:02d}h{m:02d}min"
def nome_arquivo_seguro(nome: str, data_fmt: str) -> str:
    base = re.sub(r'[<>:"/\\|?*]', "_", nome).strip() or "documento"
    return f"justificativa_{base}_{data_fmt.replace('/', '-')}.pdf"
def _nova_pagina(c, W, H, margem, y, min_y):
    if y >= min_y:
        return y
    _rodape_pdf(c, W, H)
    c.showPage()
    _cabecalho_continua(c, W, H)
    return H - margem - 1.0 * cm
def _cabecalho_continua(c, W, H):
    c.setFillColor(colors.HexColor(PRIMARY))
    c.rect(0, H - 0.55 * cm, W, 0.55 * cm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.rect(0, H - 0.72 * cm, W, 0.18 * cm, fill=1, stroke=0)
def _rodape_pdf(c, W, H):
    emissao = datetime.now(_BRT).strftime('%d/%m/%Y  %H:%M')
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(0, 0, W, 1.8 * cm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.rect(0, 1.78 * cm, W, 0.04 * cm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawString(2 * cm, 1.12 * cm, "Hospital Regional Sul")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(2 * cm, 0.62 * cm, "Documento gerado eletronicamente · Não requer assinatura física")
    c.drawRightString(W - 2 * cm, 0.87 * cm, f"Emitido em {emissao}")
# ==================================================
# GOOGLE DRIVE + SHEETS — FUNÇÕES AUXILIARES
# ==================================================
def _obter_credenciais():
    """Cria credenciais a partir dos secrets do Streamlit."""
    creds = Credentials.from_service_account_info(
        st.secrets["gdrive"],
        scopes=SCOPES,
    )
    return creds
def _obter_ou_criar_subpasta(drive_service, pasta_pai_id: str, nome_subpasta: str) -> str:
    """
    Procura uma subpasta com o nome dado dentro da pasta pai.
    Se não existir, cria a subpasta e retorna seu ID.
    """
    query = (
        f"'{pasta_pai_id}' in parents "
        f"and name = '{nome_subpasta}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    resultado = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=1,
    ).execute()
    arquivos = resultado.get("files", [])
    if arquivos:
        return arquivos[0]["id"]
    # Criar subpasta
    metadata = {
        "name": nome_subpasta,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [pasta_pai_id],
    }
    pasta = drive_service.files().create(
        body=metadata,
        fields="id",
    ).execute()
    return pasta["id"]
def upload_pdf_para_drive(pdf_buffer: BytesIO, nome_arquivo: str, setor: str) -> str:
    """
    Faz upload do PDF para o Google Drive na subpasta do setor.
    Retorna o ID do arquivo criado.
    """
    creds = _obter_credenciais()
    drive_service = build("drive", "v3", credentials=creds)
    pasta_raiz_id = st.secrets["gdrive_settings"]["folder_id"]
    # Obter ou criar subpasta com o nome do setor
    pasta_setor_id = _obter_ou_criar_subpasta(drive_service, pasta_raiz_id, setor)
    # Upload do PDF
    pdf_buffer.seek(0)
    media = MediaIoBaseUpload(
        pdf_buffer,
        mimetype="application/pdf",
        resumable=False,
    )
    file_metadata = {
        "name": nome_arquivo,
        "parents": [pasta_setor_id],
    }
    arquivo = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
    ).execute()
    return arquivo["id"]
def _obter_ou_criar_planilha(drive_service, sheets_service, pasta_raiz_id: str) -> str:
    """
    Procura a planilha 'Justificativas de Ponto' na pasta raiz.
    Se não existir, cria e adiciona o cabeçalho.
    Retorna o spreadsheet_id.
    """
    nome_planilha = "Justificativas de Ponto"
    query = (
        f"'{pasta_raiz_id}' in parents "
        f"and name = '{nome_planilha}' "
        f"and mimeType = 'application/vnd.google-apps.spreadsheet' "
        f"and trashed = false"
    )
    resultado = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=1,
    ).execute()
    arquivos = resultado.get("files", [])
    if arquivos:
        return arquivos[0]["id"]
    # Criar planilha nova
    spreadsheet_body = {
        "properties": {"title": nome_planilha},
        "sheets": [
            {
                "properties": {
                    "title": "Registros",
                    "gridProperties": {"frozenRowCount": 1},
                }
            }
        ],
    }
    planilha = sheets_service.spreadsheets().create(
        body=spreadsheet_body,
        fields="spreadsheetId",
    ).execute()
    spreadsheet_id = planilha["spreadsheetId"]
    # Mover para a pasta correta
    drive_service.files().update(
        fileId=spreadsheet_id,
        addParents=pasta_raiz_id,
        removeParents="root",
        fields="id, parents",
    ).execute()
    # Adicionar cabeçalho
    cabecalho = [[
        "Data/Hora Envio",
        "Nome do Médico",
        "CRM",
        "Setor",
        "Data do Plantão",
        "Hora Entrada",
        "Hora Saída",
        "Duração",
        "Motivo",
        "Assinatura",
        "ID Arquivo Drive",
    ]]
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Registros!A1:K1",
        valueInputOption="RAW",
        body={"values": cabecalho},
    ).execute()
    # Formatar cabeçalho (negrito + cor de fundo)
    requests_body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.06,
                                "green": 0.16,
                                "blue": 0.26,
                            },
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0,
                                },
                                "bold": True,
                            },
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            }
        ]
    }
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=requests_body,
    ).execute()
    return spreadsheet_id
def registrar_na_planilha(
    nome: str,
    crm: str,
    setor: str,
    data_fmt: str,
    hora_ent: str,
    hora_sai: str,
    duracao: str,
    motivo: str,
    assinatura: str,
    arquivo_drive_id: str,
):
    """
    Adiciona uma nova linha na planilha 'Justificativas de Ponto'
    com os dados da justificativa.
    """
    creds = _obter_credenciais()
    drive_service  = build("drive", "v3", credentials=creds)
    sheets_service = build("sheets", "v4", credentials=creds)
    pasta_raiz_id = st.secrets["gdrive_settings"]["folder_id"]
    spreadsheet_id = _obter_ou_criar_planilha(
        drive_service, sheets_service, pasta_raiz_id
    )
    agora = datetime.now(_BRT).strftime("%d/%m/%Y %H:%M:%S")
    nova_linha = [[
        agora,
        nome,
        crm,
        setor,
        data_fmt,
        hora_ent,
        hora_sai,
        duracao,
        motivo,
        assinatura,
        arquivo_drive_id,
    ]]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Registros!A:K",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": nova_linha},
    ).execute()
# ==================================================
# CABEÇALHO DA PÁGINA (APP)
# ==================================================
_logo_png = logo_transparente_png(LOGO_PATH)
logo_html = ""
if _logo_png:
    import base64
    _b64 = base64.b64encode(_logo_png).decode()
    logo_html = (
        f'<img src="data:image/png;base64,{_b64}" '
        f'style="height:110px;width:auto;filter:brightness(0) invert(1);display:block;" />'
    )
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
st.caption("Preencha todos os campos obrigatórios (*) e clique em **Enviar relatório** para realizar a justificativa.")
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
            crm  = st.text_input("CRM *", placeholder="Ex.: 12345")
        st.markdown('<p class="form-section">Dados do Plantão</p>', unsafe_allow_html=True)
        ca, cb, cc = st.columns([3, 2, 2])
        with ca:
            setor = st.selectbox("Setor *", SETOR_OPCOES)
        with cb:
            data  = st.date_input("Data *", format="DD/MM/YYYY")
        with cc:
            st.empty()
        cd, ce = st.columns(2)
        with cd:
            hora_entrada = st.time_input("Entrada *", value=time(7, 0),  step=timedelta(minutes=15))
        with ce:
            hora_saida   = st.time_input("Saída *",   value=time(19, 0), step=timedelta(minutes=15))
        st.markdown('<p class="form-section">Justificativa</p>', unsafe_allow_html=True)
        motivo = st.text_area(
            "Motivo *",
            height=150,
            placeholder=(
                "Descreva o motivo com objetividade.\n"
                "Ex.: atraso no registro de entrada, plantão não batido, correção de horário..."
            ),
        )
        st.markdown('<p class="form-section">Assinatura</p>', unsafe_allow_html=True)
        cf, cg = st.columns([3, 2])
        with cf:
            assinatura = st.text_input(
                "Nome para assinatura *",
                placeholder="Conforme documento oficial",
            )
        with cg:
            st.markdown(
                f"""
                <div style="
                    margin-top: 1.65rem;
                    padding: 0.5rem 0.75rem;
                    background: {SURFACE};
                    border: 1px solid {BORDER};
                    border-radius: 8px;
                    font-size: 0.78rem;
                    color: {MUTED};
                    line-height: 1.5;
                ">
                    O nome digitado será registrado como assinatura eletrônica no relatório.
                </div>
                """,
                unsafe_allow_html=True,
            )
        enviar = st.form_submit_button("📄  Enviar relatório", use_container_width=True)
st.markdown(
    '<p class="app-foot">Em caso de dúvidas, contate a administração · Hospital Regional Sul</p>',
    unsafe_allow_html=True,
)
# ==================================================
# GERAR PDF  –  layout profissional
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
    data_fmt  = data.strftime("%d/%m/%Y")
    hora_ent  = hora_entrada.strftime("%H:%M")
    hora_sai  = hora_saida.strftime("%H:%M")
    td_dur    = duracao_plantao(data, hora_entrada, hora_saida)
    horas_dur = fmt_duracao(td_dur)
    buffer = BytesIO()
    c      = canvas.Canvas(buffer, pagesize=A4)
    W, H   = A4
    margem = 2.0 * cm
    min_y  = 2.2 * cm
    # ─────────────────────────────────────────────────────────────
    # CABEÇALHO PDF
    # ─────────────────────────────────────────────────────────────
    hdr_h        = 4.8 * cm
    logo_panel_w = 5.8 * cm
    c.setFillColor(colors.white)
    c.rect(0, H - hdr_h, logo_panel_w, hdr_h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#1e4a6e"))
    c.rect(logo_panel_w, H - hdr_h, W - logo_panel_w, hdr_h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.rect(0, H - hdr_h - 0.20 * cm, W, 0.20 * cm, fill=1, stroke=0)
    _ir    = ImageReader(BytesIO(_logo_bytes))
    iw, ih = _ir.getSize()
    if iw <= 0 or ih <= 0: iw = ih = 1
    logo_w = 4.4 * cm
    logo_h = logo_w * (ih / iw)
    logo_x = (logo_panel_w - logo_w) / 2
    logo_y = H - hdr_h + (hdr_h - logo_h) / 2
    c.drawImage(_ir, logo_x, logo_y, width=logo_w, height=logo_h,
                mask="auto", preserveAspectRatio=True)
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.5)
    c.line(logo_panel_w, H - hdr_h + 0.4 * cm, logo_panel_w, H - 0.4 * cm)
    txt_x = logo_panel_w + 0.95 * cm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.white)
    c.drawString(txt_x, H - 2.0 * cm, "JUSTIFICATIVA DE PONTO")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.Color(1, 1, 1, 0.75))
    c.drawString(txt_x, H - 2.85 * cm, "Hospital Regional Sul")
    y = H - hdr_h - 0.20 * cm - 1.0 * cm
    # ─────────────────────────────────────────────────────────────
    # HELPERS PDF
    # ─────────────────────────────────────────────────────────────
    def _secao_titulo(cy: float, titulo: str) -> float:
        pill_w = c.stringWidth(titulo.upper(), "Helvetica-Bold", 8) + 0.8 * cm
        c.setFillColor(colors.HexColor(PRIMARY))
        c.roundRect(margem, cy - 0.05 * cm, pill_w, 0.52 * cm, 4, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.white)
        c.drawString(margem + 0.35 * cm, cy + 0.11 * cm, titulo.upper())
        c.setStrokeColor(colors.HexColor(BORDER))
        c.setLineWidth(0.5)
        c.line(margem + pill_w + 0.25 * cm, cy + 0.22 * cm, W - margem, cy + 0.22 * cm)
        return cy - 0.85 * cm
    ROW_H      = 0.72 * cm
    LINE_EXTRA = 0.40 * cm
    LBL_W      = 3.2 * cm
    VAL_X      = margem + LBL_W
    def _campo(cy: float, label: str, valor: str, shade: bool) -> float:
        linhas_v = quebrar_texto(str(valor), limite=42)
        rh = max(ROW_H, 0.44 * cm + max(0, len(linhas_v) - 1) * LINE_EXTRA + 0.20 * cm)
        if shade:
            c.setFillColor(colors.HexColor("#f0f4f8"))
            c.rect(margem, cy - rh + 0.08 * cm, W - 2 * margem, rh, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(colors.HexColor(PRIMARY))
        c.drawString(margem + 0.35 * cm, cy - 0.46 * cm, label.upper())
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#1e293b"))
        for j, lv in enumerate(linhas_v):
            c.drawString(VAL_X, cy - 0.46 * cm - j * LINE_EXTRA, lv)
        c.setStrokeColor(colors.HexColor(BORDER))
        c.setLineWidth(0.35)
        c.line(margem, cy - rh + 0.08 * cm, W - margem, cy - rh + 0.08 * cm)
        return cy - rh
    def _campo_2col(cy: float, pares: list[tuple]) -> float:
        rh = ROW_H
        col_w = (W - 2 * margem) / 2
        for i, (label, valor, shade) in enumerate(pares):
            ox = margem + i * col_w
            if shade:
                c.setFillColor(colors.HexColor("#f0f4f8"))
                c.rect(ox, cy - rh + 0.08 * cm, col_w, rh, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 9.5)
            c.setFillColor(colors.HexColor(PRIMARY))
            c.drawString(ox + 0.35 * cm, cy - 0.46 * cm, label.upper())
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.HexColor("#1e293b"))
            c.drawString(ox + 3.0 * cm, cy - 0.46 * cm, str(valor))
        c.setStrokeColor(colors.HexColor(BORDER))
        c.setLineWidth(0.35)
        c.line(margem, cy - rh + 0.08 * cm, W - margem, cy - rh + 0.08 * cm)
        return cy - rh
    # ─────────────────────────────────────────────────────────────
    # BLOCO 1 — DADOS DO PLANTÃO
    # ─────────────────────────────────────────────────────────────
    y = _secao_titulo(y, "Dados do Plantão")
    bloco1_top = y + 0.85 * cm
    y = _campo(y, "Médico",  nome,   True)
    y = _campo(y, "CRM",     crm,    False)
    y = _campo(y, "Setor",   setor,  True)
    y = _campo_2col(y, [("Data", data_fmt, False), ("Duração", horas_dur, False)])
    y = _campo_2col(y, [("Entrada", hora_ent, True), ("Saída", hora_sai, True)])
    bloco1_bot = y
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.7)
    c.roundRect(margem, bloco1_bot, W - 2 * margem, bloco1_top - bloco1_bot, 5, stroke=1, fill=0)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, bloco1_bot, 0.22 * cm, bloco1_top - bloco1_bot, 3, fill=1, stroke=0)
    # ─────────────────────────────────────────────────────────────
    # BLOCO 2 — JUSTIFICATIVA
    # ─────────────────────────────────────────────────────────────
    y -= 0.9 * cm
    y = _nova_pagina(c, W, H, margem, y, min_y + 3.0 * cm)
    y = _secao_titulo(y, "Justificativa")
    linhas_mot = quebrar_texto(motivo.strip(), limite=84)
    line_h_mot = 15
    pad_top    = 22
    pad_bot    = 16
    box_h      = len(linhas_mot) * line_h_mot + pad_top + pad_bot
    y = _nova_pagina(c, W, H, margem, y, min_y + box_h / 28.35 + 0.5 * cm)
    c.setFillColor(colors.HexColor("#fafbfc"))
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.8)
    c.roundRect(margem, y - box_h, W - 2 * margem, box_h, 6, stroke=1, fill=1)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, y - box_h, 0.22 * cm, box_h, 3, fill=1, stroke=0)
    texto_obj = c.beginText(margem + 0.52 * cm, y - pad_top)
    texto_obj.setFont("Helvetica", 10.5)
    texto_obj.setLeading(line_h_mot)
    texto_obj.setFillColor(colors.HexColor("#1e293b"))
    for ln in linhas_mot:
        texto_obj.textLine(ln)
    c.drawText(texto_obj)
    y -= box_h
    # ─────────────────────────────────────────────────────────────
    # BLOCO 3 — ASSINATURA
    # ─────────────────────────────────────────────────────────────
    y -= 1.0 * cm
    y = _nova_pagina(c, W, H, margem, y, min_y + 5.0 * cm)
    y = _secao_titulo(y, "Assinatura do Médico")
    sig_h = 3.0 * cm
    sig_w = W - 2 * margem
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.9)
    c.roundRect(margem, y - sig_h, sig_w, sig_h, 8, stroke=1, fill=1)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, y - sig_h + 0.35 * cm, 0.22 * cm, sig_h - 0.7 * cm, 3, fill=1, stroke=0)
    cx = W / 2
    c.setStrokeColor(colors.HexColor(PRIMARY))
    c.setLineWidth(1.1)
    c.line(cx - 2.5 * cm, y - 1.1 * cm, cx + 2.5 * cm, y - 1.1 * cm)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(cx, y - 0.72 * cm, assinatura.upper())
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 1.4 * cm, f"CRM {crm.upper()}  ·  {setor}")
    horario_ass = datetime.now(_BRT).strftime("%d/%m/%Y  %H:%M")
    c.setFont("Helvetica-Oblique", 8.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 2.15 * cm, f"Assinado eletronicamente em {horario_ass}")
    y -= sig_h
    # ─────────────────────────────────────────────────────────────
    # RODAPÉ
    # ─────────────────────────────────────────────────────────────
    _rodape_pdf(c, W, H)
    c.save()
    buffer.seek(0)
    # ─────────────────────────────────────────────────────────────
    # UPLOAD PARA GOOGLE DRIVE + REGISTRO NA PLANILHA
    # ─────────────────────────────────────────────────────────────
    arquivo_nome = nome_arquivo_seguro(nome, data_fmt)
    try:
        with st.spinner("Enviando PDF para o Google Drive..."):
            arquivo_id = upload_pdf_para_drive(buffer, arquivo_nome, setor)
        with st.spinner("Registrando na planilha..."):
            registrar_na_planilha(
                nome=nome,
                crm=crm,
                setor=setor,
                data_fmt=data_fmt,
                hora_ent=hora_ent,
                hora_sai=hora_sai,
                duracao=horas_dur,
                motivo=motivo.strip(),
                assinatura=assinatura,
                arquivo_drive_id=arquivo_id,
            )
        st.success("Relatório enviado com sucesso! PDF salvo no Google Drive e dados registrados na planilha.")
    except Exception as e:
        st.warning(
            f"O PDF foi gerado, mas houve um erro ao salvar no Google Drive/Planilha: {e}\n\n"
            "Você ainda pode baixar o PDF abaixo."
        )
    # Sempre disponibiliza o download local
    buffer.seek(0)
    st.download_button(
        label="⬇  Baixar PDF",
        data=buffer,
        file_name=arquivo_nome,
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
