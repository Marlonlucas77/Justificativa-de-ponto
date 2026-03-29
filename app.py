import os
import re
import base64
from collections import deque
from datetime import datetime, timedelta, time, timezone
from io import BytesIO

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# ==================================================
# CONFIGURAÇÕES DE CORES E TEMA
# ==================================================
st.set_page_config(
    page_title="Justificativa de Ponto",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Cores baseadas no verde da empresa (ajustado para harmonia)
PRIMARY  = "#166534"  # Verde Escuro
ACCENT   = "#15803d"  # Verde Médio
LOGO_COLOR = "#22c55e" # Verde Brilhante
MUTED    = "#64748b"
SURFACE  = "#f8fafc"
BORDER   = "#e2e8f0"
SECTION  = "#94a3b8"
_BRT     = timezone(timedelta(hours=-3))

LOGO_PATH = "imagens/mitri_logo.png"

# ==================================================
# ESTILIZAÇÃO CSS (RESPONSIVO E DESKTOP)
# ==================================================
st.markdown(
    f"""
    <style>
        /* Forçar layout de colunas no Mobile */
        [data-testid="column"] {{
            min-width: 45% !important;
            flex: 1 1 45% !important;
        }}
        
        html, body, [class*="css"] {{
            font-family: system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
        .block-container {{
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 750px !important;
        }}

        /* ── Cabeçalho APP ── */
        .app-header {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 1rem;
            margin-bottom: 2rem;
            padding: 2rem;
            background: #ffffff;
            border-radius: 16px;
            border: 1px solid {BORDER};
            box-shadow: 0 4px 15px rgba(0,0,0,.05);
        }}
        .app-header-text h1 {{
            font-size: 1.8rem !important;
            font-weight: 800 !important;
            color: {PRIMARY} !important;
            margin: 0 !important;
            letter-spacing: -0.025em;
        }}
        .app-header-sub {{
            margin: 0 !important;
            font-size: 0.9rem;
            font-weight: 500;
            color: {MUTED};
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}

        /* ── Seções ── */
        .form-section {{
            display: flex;
            align-items: center;
            gap: 0.55rem;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            color: {SECTION};
            margin: 1.5rem 0 0.8rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 2px solid {BORDER};
        }}
        .form-section::before {{
            content: "";
            display: inline-block;
            width: 4px;
            height: 14px;
            background: {LOGO_COLOR};
            border-radius: 2px;
        }}

        /* ── Botões ── */
        div[data-testid="stFormSubmitButton"] button {{
            width: 100%;
            background: {PRIMARY} !important;
            color: white !important;
            border: none !important;
            padding: 0.75rem !important;
            font-weight: 600 !important;
            border-radius: 12px !important;
            transition: 0.3s;
        }}
        div[data-testid="stFormSubmitButton"] button:hover {{
            background: {ACCENT} !important;
            transform: translateY(-1px);
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================
def logo_transparente_png(path: str) -> bytes | None:
    if not os.path.isfile(path): return None
    with open(path, "rb") as f:
        return f.read()

def quebrar_texto(texto: str, limite: int = 88) -> list[str]:
    linhas = []
    for bloco in texto.split("\n"):
        palavras = bloco.split(); linha = ""
        for p in palavras:
            if len(linha + " " + p) <= limite: linha = (linha + " " + p).strip()
            else:
                linhas.append(linha); linha = p
        if linha: linhas.append(linha)
    return linhas if linhas else [""]

def nome_arquivo_seguro(nome: str, data_fmt: str) -> str:
    base = re.sub(r'[<>:"/\\|?*]', "_", nome).strip() or "justificativa"
    return f"justificativa_{base}_{data_fmt.replace('/', '-')}.pdf"

# ==================================================
# INTERFACE DO APP
# ==================================================
_logo_bytes = logo_transparente_png(LOGO_PATH)
logo_html = ""
if _logo_bytes:
    _b64 = base64.b64encode(_logo_bytes).decode()
    logo_html = f'<img src="data:image/png;base64,{_b64}" style="height:120px; width:auto; margin-bottom:10px;">'

st.markdown(
    f"""
    <div class="app-header">
        {logo_html}
        <div class="app-header-text">
            <p class="app-header-sub">Hospital Regional Sul</p>
            <h1>Justificativa de Ponto</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    with st.form("formulario"):
        st.markdown('<p class="form-section">Identificação</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do médico *")
        crm = c2.text_input("CRM *")

        st.markdown('<p class="form-section">Dados do Plantão</p>', unsafe_allow_html=True)
        setor = st.selectbox("Setor *", ["Clínica Médica - PS", "Neurologia", "Neurocirurgia", "UTI"])
        ca, cb, cc = st.columns(3)
        data = ca.date_input("Data *", format="DD/MM/YYYY")
        h_ent = cb.time_input("Entrada *", value=time(7, 0))
        h_sai = cc.time_input("Saída *", value=time(19, 0))

        st.markdown('<p class="form-section">Justificativa</p>', unsafe_allow_html=True)
        motivo = st.text_area("Motivo *", height=120)

        st.markdown('<p class="form-section">Assinatura</p>', unsafe_allow_html=True)
        assinatura = st.text_input("Nome para assinatura eletrônica *")
        
        enviar = st.form_submit_button("GERAR DOCUMENTO PDF")

# ==================================================
# GERAÇÃO DO PDF
# ==================================================
if enviar:
    if not all([nome, crm, motivo, assinatura]):
        st.error("Por favor, preencha todos os campos obrigatórios.")
        st.stop()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    margem = 2.0 * cm

    # ─────────────────────────────────────────────────────────────
    # CABEÇALHO PDF (TUDO BRANCO E CENTRALIZADO)
    # ─────────────────────────────────────────────────────────────
    # Logo Centralizado (Aumentado)
    if _logo_bytes:
        _ir = ImageReader(BytesIO(_logo_bytes))
        logo_w = 5.5 * cm  # Aumentado conforme solicitado
        iw, ih = _ir.getSize()
        logo_h = logo_w * (ih / iw)
        c.drawImage(_ir, (W - logo_w)/2, H - 4.5 * cm, width=logo_w, height=logo_h, mask="auto")

    # Título Centralizado
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(W/2, H - 5.8 * cm, "JUSTIFICATIVA DE PONTO")
    
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(W/2, H - 6.4 * cm, "Hospital Regional Sul")

    # Linha decorativa verde
    c.setStrokeColor(colors.HexColor(LOGO_COLOR))
    c.setLineWidth(2)
    c.line(margem, H - 7.0 * cm, W - margem, H - 7.0 * cm)

    y = H - 8.5 * cm

    # ─────────────────────────────────────────────────────────────
    # CORPO DO DOCUMENTO
    # ─────────────────────────────────────────────────────────────
    def desenhar_bloco(titulo, dados, current_y):
        # Título da seção
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor(PRIMARY))
        c.drawString(margem, current_y, titulo.upper())
        current_y -= 0.6 * cm
        
        # Fundo do bloco
        bloco_h = (len(dados) * 0.8 * cm) + 0.4 * cm
        c.setFillColor(colors.HexColor("#f8fafc"))
        c.roundRect(margem, current_y - bloco_h, W - (2 * margem), bloco_h, 6, fill=1, stroke=0)
        
        # Conteúdo
        temp_y = current_y - 0.6 * cm
        for label, valor in dados:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(colors.HexColor(ACCENT))
            c.drawString(margem + 0.5 * cm, temp_y, f"{label}:")
            
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.black)
            c.drawString(margem + 3.5 * cm, temp_y, str(valor))
            temp_y -= 0.8 * cm
            
        return current_y - bloco_h - 1.0 * cm

    # Bloco 1 - Dados
    campos_plantao = [
        ("Médico", nome),
        ("CRM", crm),
        ("Setor", setor),
        ("Data", data.strftime("%d/%m/%Y")),
        ("Horário", f"{h_ent.strftime('%H:%M')} às {h_sai.strftime('%H:%M')}")
    ]
    y = desenhar_bloco("Informações do Plantão", campos_plantao, y)

    # Bloco 2 - Justificativa
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawString(margem, y, "JUSTIFICATIVA")
    y -= 0.6 * cm
    
    # Caixa de texto da justificativa
    linhas_mot = quebrar_texto(motivo, limite=80)
    box_h = (len(linhas_mot) * 0.5 * cm) + 1.0 * cm
    c.setFillColor(colors.HexColor("#ffffff"))
    c.setStrokeColor(colors.HexColor(BORDER))
    c.roundRect(margem, y - box_h, W - (2 * margem), box_h, 4, fill=1, stroke=1)
    
    txt_y = y - 0.7 * cm
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    for linha in linhas_mot:
        c.drawString(margem + 0.5 * cm, txt_y, linha)
        txt_y -= 0.5 * cm
    
    y -= box_h + 2.0 * cm

    # ─────────────────────────────────────────────────────────────
    # ASSINATURA E RODAPÉ
    # ─────────────────────────────────────────────────────────────
    # Linha de Assinatura
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(W/2 - 4 * cm, y + 1 * cm, W/2 + 4 * cm, y + 1 * cm)
    
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W/2, y + 0.5 * cm, assinatura.upper())
    c.setFont("Helvetica", 8)
    c.drawCentredString(W/2, y, f"Documento assinado digitalmente em {datetime.now(_BRT).strftime('%d/%m/%Y %H:%M')}")

    # Rodapé final
    c.setFillColor(colors.HexColor(MUTED))
    c.setFont("Helvetica", 7)
    c.drawCentredString(W/2, 1.5 * cm, "Hospital Regional Sul - Sistema de Gestão de Escalas")

    c.save()
    buffer.seek(0)

    st.success("PDF gerado com sucesso!")
    st.download_button(
        label="⬇️ BAIXAR JUSTIFICATIVA (PDF)",
        data=buffer,
        file_name=nome_arquivo_seguro(nome, data.strftime("%d/%m/%Y")),
        mime="application/pdf",
        use_container_width=True,
    )
