import streamlit as st
from datetime import datetime, time
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from io import BytesIO

# ==================================================
# CONFIGURAÇÃO DA PÁGINA
# ==================================================
st.set_page_config(
    page_title="Justificativa de Ponto",
    layout="centered"
)

# ==================================================
# CABEÇALHO
# ==================================================
st.markdown("## 📄 Formulário de Justificativa de Ponto")
st.markdown(
    "<span style='color:gray'>Hospital Regional Sul</span>",
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
        [
            "Clínica Médica - PS",
            "Diarista - Neurologista",
            "Neurocirurgia",
            "UTI"
        ]
    )
    data = st.date_input("Data do Plantão *")
    
    c1, c2 = st.columns(2)
    with c1:
        hora_entrada = st.time_input("Horário de Entrada *", value=time(7, 0))
    with c2:
        hora_saida = st.time_input("Horário de Saída *", value=time(19, 0))

    motivo = st.text_area("Motivo da justificativa *", height=120)
    assinatura = st.text_input("Assinatura *")

    enviar = st.form_submit_button("✅ Gerar PDF")

# ==================================================
# PROCESSAMENTO
# ==================================================
if enviar:
    if not nome or not crm or not motivo or not assinatura:
        st.error("❌ Preencha todos os campos obrigatórios.")
        st.stop()

    # Formata dados
    data_fmt = data.strftime("%d/%m/%Y")
    hora_ent = hora_entrada.strftime("%H:%M")
    hora_sai = hora_saida.strftime("%H:%M")

    # Calcula duração
    duracao = datetime.combine(data, hora_saida) - datetime.combine(data, hora_entrada)
    horas = f"{duracao.seconds//3600:02d}:{(duracao.seconds%3600)//60:02d}"

    # ==================================================
    # GERAR PDF EM MEMÓRIA (SEM DISCO)
    # ==================================================
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    X = 2 * cm

    # Cabeçalho do PDF
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(
        W / 2,
        H - 3 * cm,
        "FORMULÁRIO DE JUSTIFICATIVA DO PONTO"
    )
    c.setFont("Helvetica", 10)
    c.drawCentredString(
        W / 2,
        H - 3.6 * cm,
        "Hospital Regional Sul"
    )
    c.line(X, H - 4 * cm, W - X, H - 4 * cm)

    # Conteúdo
    y = H - 5.5 * cm
    c.setFont("Helvetica", 11)
    c.drawString(X, y, f"Nome: {nome}")
    y -= 1 * cm
    c.drawString(X, y, f"CRM: {crm}")
    y -= 1 * cm
    c.drawString(X, y, f"Setor: {setor}")
    y -= 1 * cm
    c.drawString(X, y, f"Data do plantão: {data_fmt}")
    y -= 1 * cm
    c.drawString(X, y, f"Horário: {hora_ent} - {hora_sai}")
    y -= 1 * cm
    c.drawString(X, y, f"Duração: {horas}")

    # Justificativa
    y -= 1.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(X, y, "Justificativa:")
    y -= 0.8 * cm
    c.setFont("Helvetica", 11)

    text = c.beginText(X, y)
    text.setLeading(14)
    for linha in motivo.split("\n"):
        text.textLine(linha)
    c.drawText(text)

    # Assinatura
    c.setFont("Helvetica-Bold", 11)
    c.drawString(X, 5 * cm, "Assinatura:")
    c.setFont("Helvetica", 11)
    c.drawString(X + 4 * cm, 5 * cm, assinatura)
    c.line(X, 4.8 * cm, X + 12 * cm, 4.8 * cm)

    # Rodapé
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(
        W / 2,
        2 * cm,
        "Documento gerado eletronicamente por sistema interno."
    )

    c.save()
    buffer.seek(0)

    # ==================================================
    # DOWNLOAD
    # ==================================================
    nome_arquivo = f"Justificativa_{nome.replace(' ', '_')}_{data.strftime('%Y%m%d')}.pdf"

    st.success("✅ PDF gerado com sucesso!")
    st.download_button(
        label="⬇️ Baixar PDF",
        data=buffer,
        file_name=nome_arquivo,
        mime="application/pdf"
    )
