import os
import re
import uuid
import base64
import json
from collections import deque
from datetime import datetime, timedelta, time, timezone
from io import BytesIO
import requests as http_requests
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

PRIMARY  = "#0f2942"
ACCENT   = "#1e4a6e"
MUTED    = "#64748b"
SURFACE  = "#f8fafc"
BORDER   = "#e2e8f0"
SECTION  = "#94a3b8"
SUCCESS  = "#166534"
_BRT     = timezone(timedelta(hours=-3))
LOGO_PATH = "imagens/mitri_logo.png"

# ── Inicialização do session_state ────────────────────────────────────────────
for _k, _v in {
    "enviado":          False,   # True após envio bem-sucedido
    "ultimo_protocolo": None,    # Protocolo do último envio
    "ultimo_resumo":    None,    # Dict com dados do último envio (para o card)
    # Chave de dedup: "CRM|DATA|HORA_ENT|HORA_SAI" — impede reenvio na sessão
    "chaves_enviadas":  set(),
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


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

# ==================================================
# CSS GLOBAL
# ==================================================
st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@500&display=swap');

        html, body, [class*="css"] {{
            font-family: 'DM Sans', system-ui, sans-serif !important;
        }}
        .block-container {{
            padding-top: 1.6rem !important;
            padding-bottom: 3rem !important;
            max-width: 660px !important;
        }}

        /* ── Fundo da página levemente texturizado ── */
        .stApp {{
            background-color: #f0f4f8 !important;
        }}

        /* ══════════════════════════════════════════
           CABEÇALHO — horizontal, compacto
        ══════════════════════════════════════════ */
        .app-header {{
            display: flex;
            align-items: center;
            gap: 0.85rem;
            padding: 0.7rem 1.0rem;
            margin-bottom: 1.0rem;
            background: {PRIMARY};
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(15,41,66,.22), inset 0 1px 0 rgba(255,255,255,.06);
            border: 1px solid rgba(255,255,255,.07);
            min-height: 0;
        }}
        .app-header-logo {{
            flex-shrink: 0;
            display: flex;
            align-items: center;
        }}
        .app-header-logo img {{
            height: 32px;
            width: auto;
            display: block;
            filter: brightness(0) invert(1);
            opacity: 0.92;
        }}
        .app-header-sep {{
            width: 1px;
            height: 24px;
            background: rgba(255,255,255,.18);
            flex-shrink: 0;
        }}
        .app-header-text {{
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0;
        }}
        .app-header-text h1 {{
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            color: #fff !important;
            margin: 0 0 0.1rem 0 !important;
            letter-spacing: -0.01em;
            line-height: 1.2 !important;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .app-header-text .app-header-sub {{
            margin: 0 !important;
            font-size: 0.68rem;
            font-weight: 400;
            color: rgba(255,255,255,.42);
            letter-spacing: 0.07em;
            text-transform: uppercase;
            line-height: 1;
            white-space: nowrap;
        }}
        /* Badge "documento oficial" no canto direito do header */
        .app-header-badge {{
            margin-left: auto;
            flex-shrink: 0;
            background: rgba(255,255,255,.07);
            border: 1px solid rgba(255,255,255,.13);
            border-radius: 5px;
            padding: 0.2rem 0.55rem;
            font-size: 0.6rem;
            font-weight: 600;
            color: rgba(255,255,255,.42);
            letter-spacing: 0.08em;
            text-transform: uppercase;
            white-space: nowrap;
        }}

        /* ══════════════════════════════════════════
           HINT / CAPTION
        ══════════════════════════════════════════ */
        .stCaption, .stCaption p,
        [data-testid="stCaptionContainer"] p,
        div[data-testid="stMarkdownContainer"] p small,
        small {{
            font-size: 0.78rem !important;
            color: #64748b !important;
            margin-bottom: 0.6rem !important;
        }}

        /* ══════════════════════════════════════════
           CARD DO FORMULÁRIO
        ══════════════════════════════════════════ */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: #ffffff !important;
            border-radius: 14px !important;
            border: 1px solid #dde3eb !important;
            box-shadow: 0 1px 4px rgba(15,41,66,.06), 0 4px 18px rgba(15,41,66,.05) !important;
            padding: 1.35rem 1.45rem 1.5rem !important;
        }}

        /* ══════════════════════════════════════════
           LABELS DOS CAMPOS
        ══════════════════════════════════════════ */
        label[data-testid="stWidgetLabel"] p,
        .stTextInput label p,
        .stSelectbox label p,
        .stDateInput label p,
        .stTimeInput label p,
        .stTextArea label p {{
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            color: #374151 !important;
            letter-spacing: 0.01em !important;
            margin-bottom: 0.18rem !important;
        }}

        /* ══════════════════════════════════════════
           INPUTS
        ══════════════════════════════════════════ */
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] div,
        [data-testid="stDateInput"] input,
        div[data-baseweb="datepicker"] input {{
            border-radius: 8px !important;
            font-size: 0.88rem !important;
            border-color: #d1d9e0 !important;
            background: #fafbfc !important;
        }}
        [data-baseweb="input"] input:focus,
        [data-baseweb="textarea"] textarea:focus {{
            border-color: {LOGO_COLOR} !important;
            box-shadow: 0 0 0 3px {LOGO_COLOR}22 !important;
        }}

        /* ══════════════════════════════════════════
           SEÇÕES DO FORMULÁRIO
        ══════════════════════════════════════════ */
        .form-section {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.67rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: {SECTION};
            margin: 1.2rem 0 0.65rem 0;
            padding-bottom: 0.38rem;
            border-bottom: 1px solid {BORDER};
        }}
        .form-section-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: {LOGO_COLOR};
            flex-shrink: 0;
            box-shadow: 0 0 0 3px {LOGO_COLOR}28;
        }}

        /* ══════════════════════════════════════════
           BOTÃO ENVIAR
        ══════════════════════════════════════════ */
        div[data-testid="stFormSubmitButton"] button {{
            width: 100%;
            border-radius: 9px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            padding: 0.62rem 1rem !important;
            background: {PRIMARY} !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 2px 8px rgba(15,41,66,.30), inset 0 1px 0 rgba(255,255,255,.10) !important;
            margin-top: 0.55rem;
            letter-spacing: 0.02em;
            transition: filter .15s, box-shadow .15s;
        }}
        div[data-testid="stFormSubmitButton"] button:hover {{
            filter: brightness(1.10) !important;
            box-shadow: 0 4px 14px rgba(15,41,66,.38) !important;
        }}
        /* Faixa de cor accent no topo do botão */
        div[data-testid="stFormSubmitButton"] button::before {{
            content: "";
            display: block;
            height: 2px;
            border-radius: 2px 2px 0 0;
            background: {LOGO_COLOR};
            position: absolute;
            top: 0; left: 0; right: 0;
        }}
        div[data-testid="stFormSubmitButton"] button {{ position: relative; overflow: hidden; }}

        /* ══════════════════════════════════════════
           BOTÃO DOWNLOAD
        ══════════════════════════════════════════ */
        .stDownloadButton button {{
            border-radius: 9px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            width: 100%;
        }}

        /* ══════════════════════════════════════════
           BOTÃO SECUNDÁRIO (nova justificativa)
        ══════════════════════════════════════════ */
        .stButton > button {{
            border-radius: 9px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            border: 1.5px solid #d1d9e0 !important;
            color: {PRIMARY} !important;
            background: #fff !important;
        }}
        .stButton > button:hover {{
            border-color: {LOGO_COLOR} !important;
            color: {LOGO_COLOR} !important;
            background: #f5feff !important;
        }}

        /* ══════════════════════════════════════════
           CARD DE SUCESSO
        ══════════════════════════════════════════ */
        .success-card {{
            background: #fff;
            border: 1px solid #bbf7d0;
            border-top: 3px solid #22c55e;
            border-radius: 12px;
            padding: 1.4rem 1.4rem 1.3rem;
            margin: 0.8rem 0 1rem;
            box-shadow: 0 2px 12px rgba(22,101,52,.08);
        }}
        .success-card-header {{
            display: flex;
            align-items: center;
            gap: 0.7rem;
            margin-bottom: 1rem;
        }}
        .success-icon {{
            width: 40px; height: 40px;
            background: linear-gradient(135deg, #16a34a, #15803d);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.15rem;
            flex-shrink: 0;
            box-shadow: 0 2px 8px rgba(22,101,52,.28);
        }}
        .success-title {{
            font-size: 1.0rem; font-weight: 700;
            color: #14532d; margin: 0; line-height: 1.25;
        }}
        .success-subtitle {{
            font-size: 0.76rem; color: #16a34a;
            margin: 0.12rem 0 0 0; font-weight: 500;
        }}
        .success-protocol {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 6px;
            padding: 0.28rem 0.65rem;
            font-size: 0.75rem;
            color: #166534;
            font-family: 'DM Mono', 'Courier New', monospace;
            font-weight: 500;
            margin-bottom: 1rem;
            letter-spacing: 0.04em;
        }}
        .success-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
        }}
        .success-field {{
            background: #f8fafc;
            border-radius: 7px;
            padding: 0.5rem 0.65rem;
            border: 1px solid #e9eef4;
        }}
        .success-field-label {{
            font-size: 0.63rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: #16a34a;
            margin-bottom: 0.18rem;
        }}
        .success-field-value {{
            font-size: 0.85rem;
            font-weight: 600;
            color: #1e293b;
            word-break: break-word;
        }}
        .success-field.full {{ grid-column: 1 / -1; }}

        /* ══════════════════════════════════════════
           ALERTA DUPLICATA
        ══════════════════════════════════════════ */
        .dup-warning {{
            background: #fffbeb;
            border: 1px solid #fcd34d;
            border-left: 3px solid #f59e0b;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            margin: 0.4rem 0 0.9rem;
            display: flex; gap: 0.65rem; align-items: flex-start;
        }}
        .dup-warning-icon {{ font-size: 1.1rem; flex-shrink: 0; margin-top: 0.05rem; }}
        .dup-warning-body {{ font-size: 0.83rem; color: #92400e; line-height: 1.55; }}
        .dup-warning-body strong {{ color: #78350f; }}

        /* ══════════════════════════════════════════
           RODAPÉ
        ══════════════════════════════════════════ */
        .app-foot {{
            text-align: center;
            font-size: 0.72rem;
            color: #a0aec0;
            margin-top: 1.8rem;
            padding-top: 0.9rem;
            border-top: 1px solid {BORDER};
            letter-spacing: 0.01em;
        }}

        /* ── misc ── */
        [data-testid="stImage"] img,
        [data-testid="stImage"] picture img,
        [data-testid="stImage"] {{
            background: transparent !important;
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
    return f"{base}_{data_fmt.replace('/', '-')}.pdf"


def gerar_protocolo() -> str:
    """Gera número de protocolo único: HRS-YYYYMMDD-XXXX (8 hex maiúsculos)."""
    sufixo = uuid.uuid4().hex[:8].upper()
    hoje   = datetime.now(_BRT).strftime("%Y%m%d")
    return f"HRS-{hoje}-{sufixo}"


def chave_dedup(crm: str, data_fmt: str, hora_ent: str, hora_sai: str) -> str:
    """Chave única que identifica um plantão específico de um médico."""
    return f"{crm.strip().upper()}|{data_fmt}|{hora_ent}|{hora_sai}"


# ==================================================
# PDF — helpers internos
# ==================================================
def _nova_pagina(c, W, H, margem, y, min_y):
    if y >= min_y:
        return y
    _rodape_pdf(c, W, H)
    c.showPage()
    _cabecalho_continua(c, W, H)
    return H - margem - 1.0 * cm


def _cabecalho_continua(c, W, H):
    c.setFillColor(colors.white)
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
    c.drawString(2 * cm, 0.62 * cm, "Documento gerado eletronicamente")
    c.drawRightString(W - 2 * cm, 0.87 * cm, f"Emitido em {emissao}")


# ==================================================
# GOOGLE APPS SCRIPT
# ==================================================
def verificar_duplicata_remota(crm: str, data_fmt: str, hora_ent: str, hora_sai: str) -> bool:
    """
    Consulta o Apps Script para saber se já existe um registro
    com o mesmo CRM + data + horários na planilha.
    Retorna True se for duplicata.
    """
    try:
        apps_script_url = st.secrets["apps_script"]["url"]
        resp = http_requests.get(
            apps_script_url,
            params={
                "action":    "verificar_duplicata",
                "crm":       crm.strip().upper(),
                "data_fmt":  data_fmt,
                "hora_ent":  hora_ent,
                "hora_sai":  hora_sai,
            },
            timeout=15,
        )
        resp.raise_for_status()
        dados = resp.json()
        return dados.get("duplicata", False)
    except Exception:
        # Se a verificação remota falhar, não bloqueia o envio
        return False


def enviar_para_google(pdf_buffer: BytesIO, nome_arquivo: str, dados: dict) -> dict:
    """
    Envia o PDF e os dados para o Google Apps Script Web App.
    O script salva o PDF no Drive (subpasta por setor) e
    registra os dados na planilha.
    Retorna o JSON de resposta do Apps Script.
    """
    apps_script_url = st.secrets["apps_script"]["url"]
    pdf_buffer.seek(0)
    pdf_b64 = base64.b64encode(pdf_buffer.read()).decode("utf-8")

    payload = {
        "nome":             dados["nome"],
        "crm":              dados["crm"],
        "setor":            dados["setor"],
        "data_fmt":         dados["data_fmt"],
        "hora_ent":         dados["hora_ent"],
        "hora_sai":         dados["hora_sai"],
        "duracao":          dados["duracao"],
        "motivo":           dados["motivo"],
        "assinatura":       dados["assinatura"],
        "protocolo":        dados["protocolo"],
        "nome_arquivo":     nome_arquivo,
        "pdf_base64":       pdf_b64,
        "titulo_planilha":  dados.get("titulo_planilha", "JUSTIFICATIVA DE PONTO"),
        "logo_base64":      dados.get("logo_base64", ""),
    }
    resp = http_requests.post(
        apps_script_url,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ==================================================
# CABEÇALHO DA PÁGINA (APP)
# ==================================================
_logo_png = logo_transparente_png(LOGO_PATH)
_logo_inner = ""
if _logo_png:
    _b64 = base64.b64encode(_logo_png).decode()
    _logo_inner = (
        f'<div class="app-header-logo">'
        f'<img src="data:image/png;base64,{_b64}" /></div>'
        f'<div class="app-header-sep"></div>'
    )
elif os.path.exists(LOGO_PATH):
    _logo_inner = (
        '<div class="app-header-logo">'
        '<span style="color:rgba(255,255,255,.4);font-size:0.75rem;font-weight:700;letter-spacing:.06em;">HRS</span>'
        '</div><div class="app-header-sep"></div>'
    )

st.markdown(
    f"""
    <div class="app-header">
        {_logo_inner}
        <div class="app-header-text">
            <h1>Justificativa de Ponto</h1>
            <p class="app-header-sub">Hospital Regional Sul</p>
        </div>
        <div class="app-header-badge">Documento Oficial</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# CARD DE SUCESSO (exibido após envio bem-sucedido)
# ==================================================
if st.session_state.enviado and st.session_state.ultimo_resumo:
    r = st.session_state.ultimo_resumo

    st.markdown(
        f"""
        <div class="success-card">
            <div class="success-card-header">
                <div class="success-icon">✅</div>
                <div>
                    <p class="success-title">Justificativa enviada!</p>
                    <p class="success-subtitle">Registrada com sucesso no sistema do Hospital Regional Sul</p>
                </div>
            </div>
            <div class="success-protocol">
                🔐&nbsp; Protocolo: {r["protocolo"]}
            </div>
            <div class="success-grid">
                <div class="success-field">
                    <div class="success-field-label">Médico</div>
                    <div class="success-field-value">{r["nome"]}</div>
                </div>
                <div class="success-field">
                    <div class="success-field-label">CRM</div>
                    <div class="success-field-value">{r["crm"]}</div>
                </div>
                <div class="success-field">
                    <div class="success-field-label">Setor</div>
                    <div class="success-field-value">{r["setor"]}</div>
                </div>
                <div class="success-field">
                    <div class="success-field-label">Data</div>
                    <div class="success-field-value">{r["data_fmt"]}</div>
                </div>
                <div class="success-field">
                    <div class="success-field-label">Entrada</div>
                    <div class="success-field-value">{r["hora_ent"]}</div>
                </div>
                <div class="success-field">
                    <div class="success-field-label">Saída / Duração</div>
                    <div class="success-field-value">{r["hora_sai"]} &nbsp;·&nbsp; {r["duracao"]}</div>
                </div>
                <div class="success-field full">
                    <div class="success-field-label">Enviado em</div>
                    <div class="success-field-value">{r["enviado_em"]}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Botão de download do PDF
    if st.session_state.get("ultimo_pdf_bytes"):
        st.download_button(
            label="⬇  Baixar PDF",
            data=st.session_state.ultimo_pdf_bytes,
            file_name=st.session_state.ultimo_arquivo_nome,
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    # Botão para nova justificativa
    if st.button("＋  Registrar nova justificativa", use_container_width=True):
        st.session_state.enviado          = False
        st.session_state.ultimo_protocolo = None
        st.session_state.ultimo_resumo    = None
        st.rerun()

    st.markdown(
        '<p class="app-foot">Em caso de dúvidas, contate a administração · Hospital Regional Sul</p>',
        unsafe_allow_html=True,
    )
    st.stop()  # Não renderiza o formulário enquanto mostra o card

# ==================================================
# FORMULÁRIO
# ==================================================
st.caption("Preencha todos os campos obrigatórios (*) e clique em **Enviar relatório** para realizar a justificativa.")

with st.container(border=True):
    with st.form("formulario"):
        st.markdown('<p class="form-section"><span class="form-section-dot"></span>Identificação</p>', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            nome = st.text_input("Nome do médico *", placeholder="Nome completo")
        with c2:
            crm  = st.text_input("CRM *", placeholder="Ex.: 12345")

        st.markdown('<p class="form-section"><span class="form-section-dot"></span>Dados do Plantão</p>', unsafe_allow_html=True)
        ca, cb = st.columns([3, 2])
        with ca:
            setor = st.selectbox("Setor *", SETOR_OPCOES)
        with cb:
            data = st.date_input(
                "Data *",
                value=datetime.now(_BRT).date(),
                format="DD/MM/YYYY",
            )

        cd, ce = st.columns(2)
        with cd:
            hora_entrada = st.time_input("Entrada *", value=time(7, 0),  step=timedelta(minutes=15))
        with ce:
            hora_saida   = st.time_input("Saída *",   value=time(19, 0), step=timedelta(minutes=15))

        st.markdown('<p class="form-section"><span class="form-section-dot"></span>Justificativa</p>', unsafe_allow_html=True)
        motivo = st.text_area(
            "Motivo *",
            height=150,
            placeholder=(
                "Descreva o motivo com objetividade.\n"
                "Ex.: atraso no registro de entrada, plantão não batido, correção de horário..."
            ),
        )

        st.markdown('<p class="form-section"><span class="form-section-dot"></span>Assinatura</p>', unsafe_allow_html=True)
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
# PROCESSAMENTO DO ENVIO
# ==================================================
if enviar:
    # ── 1. Validação de campos obrigatórios ─────────────────────
    erros = []
    if not nome.strip():       erros.append("Nome do médico")
    if not crm.strip():        erros.append("CRM")
    if not motivo.strip():     erros.append("Motivo da justificativa")
    if not assinatura.strip(): erros.append("Nome para assinatura")

    if erros:
        st.error(f"Campos obrigatórios não preenchidos: **{', '.join(erros)}**.")
        st.stop()

    # ── 2. Logo ──────────────────────────────────────────────────
    if not os.path.exists(LOGO_PATH):
        st.error(f"Logo não encontrada em `{LOGO_PATH}`. Verifique o caminho.")
        st.stop()

    _logo_bytes = logo_transparente_png(LOGO_PATH)
    if _logo_bytes is None:
        with open(LOGO_PATH, "rb") as _lf:
            _logo_bytes = _lf.read()

    # ── 3. Derivações ────────────────────────────────────────────
    data_fmt  = data.strftime("%d/%m/%Y")
    hora_ent  = hora_entrada.strftime("%H:%M")
    hora_sai  = hora_saida.strftime("%H:%M")
    td_dur    = duracao_plantao(data, hora_entrada, hora_saida)
    horas_dur = fmt_duracao(td_dur)
    chave     = chave_dedup(crm, data_fmt, hora_ent, hora_sai)

    # ── 4. Proteção contra duplicata — camada FRONTEND ───────────
    if chave in st.session_state.chaves_enviadas:
        st.markdown(
            f"""
            <div class="dup-warning">
                <div class="dup-warning-icon">⚠️</div>
                <div class="dup-warning-body">
                    <strong>Justificativa já enviada nesta sessão.</strong><br>
                    Já existe um registro para o CRM <strong>{crm.strip().upper()}</strong>
                    no dia <strong>{data_fmt}</strong>
                    das <strong>{hora_ent}</strong> às <strong>{hora_sai}</strong>.<br>
                    Caso precise corrigir algo, entre em contato com a administração.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    # ── 5. Proteção contra duplicata — camada REMOTA (planilha) ──
    with st.spinner("Verificando registros existentes..."):
        if verificar_duplicata_remota(crm, data_fmt, hora_ent, hora_sai):
            st.markdown(
                f"""
                <div class="dup-warning">
                    <div class="dup-warning-icon">⚠️</div>
                    <div class="dup-warning-body">
                        <strong>Registro duplicado detectado na planilha.</strong><br>
                        Já existe uma justificativa cadastrada para o CRM
                        <strong>{crm.strip().upper()}</strong>
                        no dia <strong>{data_fmt}</strong>
                        das <strong>{hora_ent}</strong> às <strong>{hora_sai}</strong>.<br>
                        Se acredita que é um erro, contate a administração.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.stop()

    # ── 6. Gera protocolo único ───────────────────────────────────
    protocolo = gerar_protocolo()

    # ── 7. Geração do PDF ─────────────────────────────────────────
    buffer = BytesIO()
    c      = canvas.Canvas(buffer, pagesize=A4)
    W, H   = A4
    margem = 2.0 * cm
    min_y  = 2.2 * cm

    # — Cabeçalho PDF —
    iw, ih = ImageReader(BytesIO(_logo_bytes)).getSize()
    if iw <= 0 or ih <= 0:
        iw = ih = 1
    logo_w = 4.4 * cm
    logo_h = logo_w * (ih / iw)
    logo_x = (W - logo_w) / 2
    logo_y = H - 1.0 * cm - logo_h
    titulo_y    = logo_y - 0.80 * cm
    subtitulo_y = titulo_y - 0.62 * cm
    protocolo_y = subtitulo_y - 0.52 * cm
    cabecalho_base_y = protocolo_y - 0.50 * cm
    hdr_h = H - cabecalho_base_y

    c.setFillColor(colors.white)
    c.rect(0, cabecalho_base_y, W, hdr_h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.rect(0, cabecalho_base_y - 0.20 * cm, W, 0.20 * cm, fill=1, stroke=0)

    c.drawImage(
        ImageReader(BytesIO(_logo_bytes)),
        logo_x, logo_y,
        width=logo_w, height=logo_h,
        mask="auto", preserveAspectRatio=True,
    )

    cx = W / 2
    c.setFont("Helvetica-Bold", 17)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(cx, titulo_y, "JUSTIFICATIVA DE PONTO")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, subtitulo_y, "Hospital Regional Sul")
    # Protocolo no cabeçalho do PDF
    c.setFont("Helvetica-Oblique", 8.5)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.drawCentredString(cx, protocolo_y, f"Protocolo: {protocolo}")

    y = cabecalho_base_y - 0.20 * cm - 1.0 * cm
    y -= 0.55 * cm
    y -= 0.50 * cm

    # — Helpers de campos PDF —
    ROW_H      = 1.02 * cm
    LINE_EXTRA = 0.52 * cm
    LBL_W      = 3.4 * cm
    VAL_X      = margem + LBL_W

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

    def _campo(cy: float, label: str, valor: str, shade: bool) -> float:
        linhas_v = quebrar_texto(str(valor), limite=42)
        rh = max(ROW_H, 0.44 * cm + max(0, len(linhas_v) - 1) * LINE_EXTRA + 0.20 * cm)
        if shade:
            c.setFillColor(colors.HexColor("#f0f4f8"))
            c.rect(margem, cy - rh + 0.08 * cm, W - 2 * margem, rh, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor(PRIMARY))
        c.drawString(margem + 0.35 * cm, cy - 0.52 * cm, label.upper())
        c.setFont("Helvetica", 11.5)
        c.setFillColor(colors.HexColor("#1e293b"))
        for j, lv in enumerate(linhas_v):
            c.drawString(VAL_X, cy - 0.52 * cm - j * LINE_EXTRA, lv)
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
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(colors.HexColor(PRIMARY))
            c.drawString(ox + 0.35 * cm, cy - 0.52 * cm, label.upper())
            c.setFont("Helvetica", 11.5)
            c.setFillColor(colors.HexColor("#1e293b"))
            c.drawString(ox + 3.2 * cm, cy - 0.52 * cm, str(valor))
        c.setStrokeColor(colors.HexColor(BORDER))
        c.setLineWidth(0.35)
        c.line(margem, cy - rh + 0.08 * cm, W - margem, cy - rh + 0.08 * cm)
        return cy - rh

    # — Bloco 1: Dados do Plantão —
    y = _secao_titulo(y, "Dados do Plantão")
    bloco1_top = y + 0.85 * cm
    y = _campo(y, "Médico",  nome,     True)
    y = _campo(y, "CRM",     crm,      False)
    y = _campo(y, "Setor",   setor,    True)
    y = _campo_2col(y, [("Data",    data_fmt,  False), ("Duração", horas_dur, False)])
    y = _campo_2col(y, [("Entrada", hora_ent,  True),  ("Saída",   hora_sai,  True)])
    bloco1_bot = y

    c.setFillColor(colors.HexColor("#f8fafb"))
    c.roundRect(margem, bloco1_bot, W - 2 * margem, bloco1_top - bloco1_bot, 8, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#d0d7de"))
    c.setLineWidth(0.8)
    c.roundRect(margem, bloco1_bot, W - 2 * margem, bloco1_top - bloco1_bot, 8, stroke=1, fill=0)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, bloco1_bot + 0.15 * cm, 0.25 * cm, bloco1_top - bloco1_bot - 0.3 * cm, 3, fill=1, stroke=0)

    y_redraw = bloco1_top - 0.85 * cm
    y_redraw = _campo(y_redraw, "Médico",  nome,     True)
    y_redraw = _campo(y_redraw, "CRM",     crm,      False)
    y_redraw = _campo(y_redraw, "Setor",   setor,    True)
    y_redraw = _campo_2col(y_redraw, [("Data",    data_fmt,  False), ("Duração", horas_dur, False)])
    y_redraw = _campo_2col(y_redraw, [("Entrada", hora_ent,  True),  ("Saída",   hora_sai,  True)])

    # — Bloco 2: Justificativa —
    y -= 1.25 * cm
    y = _nova_pagina(c, W, H, margem, y, min_y + 3.0 * cm)
    y = _secao_titulo(y, "Justificativa")
    linhas_mot = quebrar_texto(motivo.strip(), limite=78)
    line_h_mot = 19
    pad_top    = 26
    pad_bot    = 22
    box_h      = len(linhas_mot) * line_h_mot + pad_top + pad_bot
    y = _nova_pagina(c, W, H, margem, y, min_y + box_h / 28.35 + 0.5 * cm)

    c.setFillColor(colors.HexColor("#fafbfc"))
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.8)
    c.roundRect(margem, y - box_h, W - 2 * margem, box_h, 6, stroke=1, fill=1)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, y - box_h, 0.22 * cm, box_h, 3, fill=1, stroke=0)
    texto_obj = c.beginText(margem + 0.52 * cm, y - pad_top)
    texto_obj.setFont("Helvetica", 12)
    texto_obj.setLeading(line_h_mot)
    texto_obj.setFillColor(colors.HexColor("#1e293b"))
    for ln in linhas_mot:
        texto_obj.textLine(ln)
    c.drawText(texto_obj)
    y -= box_h

    # — Bloco 3: Assinatura —
    y -= 1.35 * cm
    y = _nova_pagina(c, W, H, margem, y, min_y + 3.5 * cm)
    y = _secao_titulo(y, "Assinatura do Médico")
    sig_h = 3.05 * cm
    sig_w = W - 2 * margem

    c.setFillColor(colors.HexColor("#fafcfd"))
    c.setStrokeColor(colors.HexColor("#d0d7de"))
    c.setLineWidth(0.8)
    c.roundRect(margem, y - sig_h, sig_w, sig_h, 10, stroke=1, fill=1)
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.roundRect(margem, y - sig_h + 0.25 * cm, 0.25 * cm, sig_h - 0.5 * cm, 3, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(cx, y - 0.78 * cm, assinatura.upper())
    line_w = 3.2 * cm
    c.setStrokeColor(colors.HexColor(LOGO_COLOR))
    c.setLineWidth(1.2)
    c.line(cx - line_w, y - 1.08 * cm, cx + line_w, y - 1.08 * cm)
    c.setFont("Helvetica", 10.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 1.48 * cm, f"CRM {crm.upper()}  ·  {setor}")
    c.setStrokeColor(colors.HexColor(BORDER))
    c.setLineWidth(0.4)
    c.line(cx - 4.0 * cm, y - 1.88 * cm, cx + 4.0 * cm, y - 1.88 * cm)
    horario_ass = datetime.now(_BRT).strftime("%d/%m/%Y  %H:%M")
    c.setFont("Helvetica-Oblique", 9.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 2.38 * cm, f"Assinado eletronicamente em {horario_ass}")
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.circle(cx - 3.8 * cm, y - 2.32 * cm, 0.12 * cm, fill=1, stroke=0)
    y -= sig_h

    # — Rodapé —
    _rodape_pdf(c, W, H)
    c.save()
    buffer.seek(0)

    # ── 8. Upload Google Drive + registro na planilha ─────────────
    arquivo_nome = nome_arquivo_seguro(nome, data_fmt)
    pdf_bytes    = buffer.getvalue()

    try:
        with st.spinner("Enviando PDF para o Google Drive e registrando na planilha..."):
            resultado = enviar_para_google(
                pdf_buffer=BytesIO(pdf_bytes),
                nome_arquivo=arquivo_nome,
                dados={
                    "nome":            nome,
                    "crm":             crm,
                    "setor":           setor,
                    "data_fmt":        data_fmt,
                    "hora_ent":        hora_ent,
                    "hora_sai":        hora_sai,
                    "duracao":         horas_dur,
                    "motivo":          motivo.strip(),
                    "assinatura":      assinatura,
                    "protocolo":       protocolo,
                    "titulo_planilha": "JUSTIFICATIVA DE PONTO",
                    "logo_base64":     base64.b64encode(_logo_bytes).decode("utf-8"),
                },
            )

        if resultado.get("status") == "ok":
            # ── Marca a chave como enviada na sessão ─────────────
            st.session_state.chaves_enviadas.add(chave)
            # ── Salva resumo para o card de sucesso ──────────────
            st.session_state.ultimo_protocolo = protocolo
            st.session_state.ultimo_resumo    = {
                "nome":       nome,
                "crm":        crm.upper(),
                "setor":      setor,
                "data_fmt":   data_fmt,
                "hora_ent":   hora_ent,
                "hora_sai":   hora_sai,
                "duracao":    horas_dur,
                "protocolo":  protocolo,
                "enviado_em": datetime.now(_BRT).strftime("%d/%m/%Y às %H:%M"),
            }
            st.session_state.ultimo_pdf_bytes    = pdf_bytes
            st.session_state.ultimo_arquivo_nome = arquivo_nome
            st.session_state.enviado             = True
            st.rerun()  # Mostra o card de sucesso

        else:
            st.warning(
                f"Resposta inesperada do servidor: {resultado.get('message', 'Sem detalhes')}\n\n"
                "Você ainda pode baixar o PDF abaixo."
            )
            # Download disponível mesmo com falha no servidor
            st.download_button(
                label="⬇  Baixar PDF",
                data=pdf_bytes,
                file_name=arquivo_nome,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

    except Exception as e:
        st.warning(
            f"O PDF foi gerado, mas houve um erro ao enviá-lo ao servidor: {e}\n\n"
            "Você ainda pode baixar o PDF abaixo."
        )
        st.download_button(
            label="⬇  Baixar PDF",
            data=pdf_bytes,
            file_name=arquivo_nome,
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
