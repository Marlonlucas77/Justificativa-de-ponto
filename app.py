# (SEU CÓDIGO ORIGINAL MANTIDO — só alterei pontos necessários)

# ... (mantive tudo igual até a parte do logo HTML)

logo_html = ""
    import base64
    _b64 = base64.b64encode(_logo_png).decode()
    # 🔥 LOGO MAIOR AQUI
    logo_html = f'<img src="data:image/png;base64,{_b64}" style="height:110px;width:auto;filter:brightness(0) invert(1);display:block;" />'
elif os.path.exists(LOGO_PATH):
    logo_html = '<span style="color:rgba(255,255,255,.5);font-size:0.8rem;">Logo</span>'

# ==================================================
# PDF
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
        st.error(f"Logo não encontrada em `{LOGO_PATH}`.")
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
    margem = 2.1 * cm
    min_y  = 2.8 * cm

    # =========================================
    # CABEÇALHO PDF (FUNDO BRANCO)
    # =========================================
    logo_area_h = 3.8 * cm

    c.setFillColor(colors.white)  # 🔥 AGORA BRANCO
    c.rect(0, H - logo_area_h, W, logo_area_h, fill=1, stroke=0)

    _ir    = ImageReader(BytesIO(_logo_bytes))
    iw, ih = _ir.getSize()
    if iw <= 0 or ih <= 0: iw = ih = 1

    logo_w = 4.8 * cm
    logo_h = logo_w * (ih / iw)
    logo_x = (W - logo_w) / 2
    logo_y = H - logo_area_h + (logo_area_h - logo_h) / 2

    c.drawImage(_ir, logo_x, logo_y, width=logo_w, height=logo_h, mask="auto")

    titulo_y = H - logo_area_h - 0.7 * cm
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor(PRIMARY))
    c.drawCentredString(W / 2, titulo_y, "JUSTIFICATIVA DE PONTO")

    subtitulo_y = titulo_y - 0.58 * cm
    c.setFont("Helvetica", 9.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawCentredString(W / 2, subtitulo_y, "Hospital Regional Sul")

    y = subtitulo_y - 0.7 * cm
    c.setStrokeColor(colors.black)
    c.line(margem, y, W - margem, y)

    y -= 1.1 * cm

    # =========================================
    # DADOS
    # =========================================
    campos = [
        ("Médico",  nome),
        ("CRM",     crm),
        ("Setor",   setor),
        ("Data",    data_fmt),
        ("Entrada", hora_ent),
        ("Saída",   hora_sai),
        ("Duração", horas_dur),
    ]

    for titulo, valor in campos:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margem, y, f"{titulo}:")
        c.setFont("Helvetica", 11)
        c.drawString(margem + 4*cm, y, str(valor))
        y -= 0.8 * cm

    # =========================================
    # JUSTIFICATIVA (FUNDO BRANCO)
    # =========================================
    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem, y, "Justificativa:")

    y -= 0.5 * cm

    linhas = quebrar_texto(motivo)

    altura_box = len(linhas) * 14 + 20

    c.setFillColor(colors.white)  # 🔥 BRANCO
    c.rect(margem, y - altura_box, W - 2*margem, altura_box)

    texto = c.beginText(margem + 5, y - 15)
    texto.setFont("Helvetica", 11)

    for linha in linhas:
        texto.textLine(linha)

    c.drawText(texto)

    # =========================================
    # ASSINATURA (FUNDO BRANCO)
    # =========================================
    y -= altura_box + 2 * cm

    c.setFillColor(colors.white)  # 🔥 BRANCO
    c.drawString(margem, y, "Assinatura:")
    c.line(margem, y - 5, W - margem, y - 5)
    c.drawString(margem + 5*cm, y, assinatura)

    # =========================================
    # RODAPÉ
    # =========================================
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(
        W/2,
        2*cm,
        f"Emitido em {datetime.now(_BRT).strftime('%d/%m/%Y %H:%M')}"
    )

    c.save()
    buffer.seek(0)

    st.success("Relatório enviado com sucesso.")
    st.download_button(
        "⬇ Baixar PDF",
        data=buffer,
        file_name=nome_arquivo_seguro(nome, data_fmt),
        mime="application/pdf"
    )
