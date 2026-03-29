import os
import re
import base64
from collections import deque
from datetime import datetime, timedelta, time, timezone
from io import BytesIO
@@ -13,7 +13,7 @@
from reportlab.pdfgen import canvas

# ==================================================
# CONFIG
# CONFIGURAÇÕES DE CORES E TEMA
# ==================================================
st.set_page_config(
    page_title="Justificativa de Ponto",
@@ -22,662 +22,305 @@
    initial_sidebar_state="collapsed",
)

PRIMARY  = "#0f2942"
ACCENT   = "#1e4a6e"
# Cores baseadas no verde da empresa (ajustado para harmonia)
PRIMARY  = "#166534"  # Verde Escuro
ACCENT   = "#15803d"  # Verde Médio
LOGO_COLOR = "#22c55e" # Verde Brilhante
MUTED    = "#64748b"
SURFACE  = "#f8fafc"
BORDER   = "#e2e8f0"
SECTION  = "#94a3b8"
SUCCESS  = "#166534"
_BRT     = timezone(timedelta(hours=-3))

LOGO_PATH = "imagens/mitri_logo.png"


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
            max-width: 700px !important;
            max-width: 750px !important;
        }}

        /* ── Cabeçalho ── */
        /* ── Cabeçalho APP ── */
        .app-header {{
            display: flex;
            flex-direction: row;
            flex-direction: column;
            align-items: center;
            gap: 1.4rem;
            margin-bottom: 1.4rem;
            padding: 1.4rem 1.8rem;
            background: linear-gradient(160deg, {PRIMARY} 0%, {ACCENT} 100%);
            text-align: center;
            gap: 1rem;
            margin-bottom: 2rem;
            padding: 2rem;
            background: #ffffff;
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
            border: 1px solid {BORDER};
            box-shadow: 0 4px 15px rgba(0,0,0,.05);
        }}
        .app-header-text h1 {{
            font-size: 1.5rem !important;
            font-size: 1.8rem !important;
            font-weight: 800 !important;
            color: #fff !important;
            color: {PRIMARY} !important;
            margin: 0 !important;
            letter-spacing: -0.025em;
            line-height: 1.15;
        }}
        .app-header-text .app-header-sub {{
        .app-header-sub {{
            margin: 0 !important;
            font-size: 0.85rem;
            font-weight: 400;
            color: rgba(255,255,255,.55);
            letter-spacing: 0.04em;
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
            font-size: 0.7rem;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.13em;
            color: {SECTION};
            margin: 1.3rem 0 0.7rem 0;
            margin: 1.5rem 0 0.8rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 1.5px solid {BORDER};
            border-bottom: 2px solid {BORDER};
        }}
        .form-section::before {{
            content: "";
            display: inline-block;
            width: 3px;
            height: 13px;
            width: 4px;
            height: 14px;
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
        /* ── Botões ── */
        div[data-testid="stFormSubmitButton"] button {{
            width: 100%;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            padding: 0.7rem 1rem !important;
            background: linear-gradient(180deg, {LOGO_COLOR} 0%, {PRIMARY} 100%) !important;
            background: {PRIMARY} !important;
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
            padding: 0.75rem !important;
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
            border-radius: 12px !important;
            transition: 0.3s;
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
        div[data-testid="stFormSubmitButton"] button:hover {{
            background: {ACCENT} !important;
            transform: translateY(-1px);
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
# FUNÇÕES AUXILIARES
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

    if not os.path.isfile(path): return None
    with open(path, "rb") as f:
        return f.read()

def quebrar_texto(texto: str, limite: int = 88) -> list[str]:
    linhas: list[str] = []
    for bloco in texto.replace("\r\n", "\n").split("\n"):
        if not bloco.strip():
            linhas.append(""); continue
    linhas = []
    for bloco in texto.split("\n"):
        palavras = bloco.split(); linha = ""
        for palavra in palavras:
            candidato = (linha + " " + palavra).strip()
            if len(candidato) <= limite:
                linha = candidato
        for p in palavras:
            if len(linha + " " + p) <= limite: linha = (linha + " " + p).strip()
            else:
                if linha: linhas.append(linha)
                linha = palavra
                linhas.append(linha); linha = p
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
    base = re.sub(r'[<>:"/\\|?*]', "_", nome).strip() or "justificativa"
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
# CABEÇALHO DA PÁGINA (APP)
# INTERFACE DO APP
# ==================================================
_logo_png = logo_transparente_png(LOGO_PATH)

_logo_bytes = logo_transparente_png(LOGO_PATH)
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
if _logo_bytes:
    _b64 = base64.b64encode(_logo_bytes).decode()
    logo_html = f'<img src="data:image/png;base64,{_b64}" style="height:120px; width:auto; margin-bottom:10px;">'

st.markdown(
    f"""
    <div class="app-header">
        <div class="app-header-logo">{logo_html}</div>
        <div class="app-header-divider"></div>
        {logo_html}
        <div class="app-header-text">
            <h1>Justificativa de Ponto</h1>
            <p class="app-header-sub">Hospital Regional Sul</p>
            <h1>Justificativa de Ponto</h1>
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
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do médico *")
        crm = c2.text_input("CRM *")

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
        setor = st.selectbox("Setor *", ["Clínica Médica - PS", "Neurologia", "Neurocirurgia", "UTI"])
        ca, cb, cc = st.columns(3)
        data = ca.date_input("Data *", format="DD/MM/YYYY")
        h_ent = cb.time_input("Entrada *", value=time(7, 0))
        h_sai = cc.time_input("Saída *", value=time(19, 0))

        st.markdown('<p class="form-section">Justificativa</p>', unsafe_allow_html=True)
        motivo = st.text_area(
            "Motivo *",
            height=150,
            placeholder=(
                "Descreva o motivo com objetividade.\n"
                "Ex.: atraso no registro de entrada, plantão não batido, correção de horário..."
            ),
        )
        motivo = st.text_area("Motivo *", height=120)

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
        assinatura = st.text_input("Nome para assinatura eletrônica *")
        
        enviar = st.form_submit_button("GERAR DOCUMENTO PDF")

# ==================================================
# GERAR PDF  –  layout profissional
# GERAÇÃO DO PDF
# ==================================================
if enviar:
    erros = []
    if not nome.strip():        erros.append("Nome do médico")
    if not crm.strip():         erros.append("CRM")
    if not motivo.strip():      erros.append("Motivo da justificativa")
    if not assinatura.strip():  erros.append("Nome para assinatura")

    if erros:
        st.error(f"Campos obrigatórios não preenchidos: **{', '.join(erros)}**.")
    if not all([nome, crm, motivo, assinatura]):
        st.error("Por favor, preencha todos os campos obrigatórios.")
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
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    margem = 2.0 * cm
    min_y  = 2.2 * cm

    # ─────────────────────────────────────────────────────────────
    # CABEÇALHO PDF
    # Painel BRANCO à esquerda → logo nítido com cores originais
    # Painel AZUL à direita    → título branco
    # CABEÇALHO PDF (TUDO BRANCO E CENTRALIZADO)
    # ─────────────────────────────────────────────────────────────
    hdr_h        = 4.8 * cm
    logo_panel_w = 5.8 * cm   # largura do painel branco

    # painel esquerdo branco
    c.setFillColor(colors.white)
    c.rect(0, H - hdr_h, logo_panel_w, hdr_h, fill=1, stroke=0)

    # painel direito azul médio
    c.setFillColor(colors.HexColor("#1e4a6e"))
    c.rect(logo_panel_w, H - hdr_h, W - logo_panel_w, hdr_h, fill=1, stroke=0)

    # faixa accent na base do cabeçalho
    c.setFillColor(colors.HexColor(LOGO_COLOR))
    c.rect(0, H - hdr_h - 0.20 * cm, W, 0.20 * cm, fill=1, stroke=0)

    # logo centralizado no painel branco — cores originais, sem filtro
    _ir    = ImageReader(BytesIO(_logo_bytes))
    iw, ih = _ir.getSize()
    if iw <= 0 or ih <= 0: iw = ih = 1
    logo_w = 4.4 * cm
    logo_h = logo_w * (ih / iw)
    logo_x = (logo_panel_w - logo_w) / 2
    logo_y = H - hdr_h + (hdr_h - logo_h) / 2
    c.drawImage(_ir, logo_x, logo_y, width=logo_w, height=logo_h,
                mask="auto", preserveAspectRatio=True)

    # separador vertical sutil
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.5)
    c.line(logo_panel_w, H - hdr_h + 0.4 * cm, logo_panel_w, H - 0.4 * cm)
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

    # textos no painel azul
    txt_x = logo_panel_w + 0.95 * cm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.white)
    c.drawString(txt_x, H - 2.0 * cm, "JUSTIFICATIVA DE PONTO")
    # Linha decorativa verde
    c.setStrokeColor(colors.HexColor(LOGO_COLOR))
    c.setLineWidth(2)
    c.line(margem, H - 7.0 * cm, W - margem, H - 7.0 * cm)

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.Color(1, 1, 1, 0.75))
    c.drawString(txt_x, H - 2.85 * cm, "Hospital Regional Sul")

    y = H - hdr_h - 0.20 * cm - 1.0 * cm   # início do conteúdo
    y = H - 8.5 * cm

    # ─────────────────────────────────────────────────────────────
    # HELPERS PDF
    # CORPO DO DOCUMENTO
    # ─────────────────────────────────────────────────────────────
    def _secao_titulo(cy: float, titulo: str) -> float:
        pill_w = c.stringWidth(titulo.upper(), "Helvetica-Bold", 8) + 0.8 * cm
    def desenhar_bloco(titulo, dados, current_y):
        # Título da seção
        c.setFont("Helvetica-Bold", 10)
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
    c.roundRect(margem, y - box_h, W - (2 * margem), box_h, 4, fill=1, stroke=1)
    
    txt_y = y - 0.7 * cm
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    for linha in linhas_mot:
        c.drawString(margem + 0.5 * cm, txt_y, linha)
        txt_y -= 0.5 * cm
    
    y -= box_h + 2.0 * cm

    # ─────────────────────────────────────────────────────────────
    # BLOCO 3 — ASSINATURA
    # ASSINATURA E RODAPÉ
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

    # Linha de Assinatura
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(W/2 - 4 * cm, y + 1 * cm, W/2 + 4 * cm, y + 1 * cm)
    
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(cx, y - 0.72 * cm, assinatura.upper())

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 1.4 * cm, f"CRM {crm.upper()}  ·  {setor}")
    c.drawCentredString(W/2, y + 0.5 * cm, assinatura.upper())
    c.setFont("Helvetica", 8)
    c.drawCentredString(W/2, y, f"Documento assinado digitalmente em {datetime.now(_BRT).strftime('%d/%m/%Y %H:%M')}")

    horario_ass = datetime.now(_BRT).strftime("%d/%m/%Y  %H:%M")
    c.setFont("Helvetica-Oblique", 8.5)
    # Rodapé final
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(cx, y - 2.15 * cm, f"Assinado eletronicamente em {horario_ass}")
    c.setFont("Helvetica", 7)
    c.drawCentredString(W/2, 1.5 * cm, "Hospital Regional Sul - Sistema de Gestão de Escalas")

    y -= sig_h

    # ─────────────────────────────────────────────────────────────
    # RODAPÉ
    # ─────────────────────────────────────────────────────────────
    _rodape_pdf(c, W, H)
    c.save()
    buffer.seek(0)

    st.success("✅ Relatório enviado com sucesso!")
    st.success("PDF gerado com sucesso!")
    st.download_button(
        label="⬇  Baixar PDF",
        label="⬇️ BAIXAR JUSTIFICATIVA (PDF)",
        data=buffer,
        file_name=nome_arquivo_seguro(nome, data_fmt),
        file_name=nome_arquivo_seguro(nome, data.strftime("%d/%m/%Y")),
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
