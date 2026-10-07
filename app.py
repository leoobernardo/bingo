import json
import os
import cv2
import numpy as np
from PIL import Image
import streamlit as st

ARQUIVO_DADOS = "bingo_dados.json"

REGRAS_COLUNAS = {
    "B": (1, 15),
    "I": (16, 30),
    "N": (31, 45),
    "G": (46, 60),
    "O": (61, 75),
}

# Configuração com layout WIDE obrigatório para caber as 5 colunas
st.set_page_config(
    page_title="Bingo 75 Vision", page_icon="🎲", layout="wide"
)


# --- PERSISTÊNCIA DE DADOS ---
def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return (
                    {
                        nome: set(nums)
                        for nome, nums in dados.get("cartelas", {}).items()
                    },
                    {
                        nome: set(nums)
                        for nome, nums in dados.get(
                            "cartelas_originais", {}
                        ).items()
                    },
                    dados.get("sorteados", []),
                )
        except Exception:
            pass
    return {}, {}, []


def salvar_dados():
    dados = {
        "cartelas": {
            nome: list(nums)
            for nome, nums in st.session_state.cartelas.items()
        },
        "cartelas_originais": {
            nome: list(nums)
            for nome, nums in st.session_state.cartelas_originais.items()
        },
        "sorteados": st.session_state.sorteados,
    }
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


if "cartelas" not in st.session_state:
    (
        st.session_state.cartelas,
        st.session_state.cartelas_originais,
        st.session_state.sorteados,
    ) = carregar_dados()


# --- OCR & PROCESSAMENTO ---
def redimensionar_imagem(img, largura_max=600):
    altura, largura = img.shape[:2]
    if largura > largura_max:
        proporcao = largura_max / float(largura)
        nova_altura = int(altura * proporcao)
        return cv2.resize(
            img, (largura_max, nova_altura), interpolation=cv2.INTER_AREA
        )
    return img


def ler_cartela_com_ia(imagem_bytes):
    try:
        import easyocr

        file_bytes = np.asarray(bytearray(imagem_bytes), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            st.error("Não foi possível processar a imagem.")
            return None

        img = redimensionar_imagem(img, largura_max=600)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        reader = easyocr.Reader(["en"], gpu=False)
        resultados = reader.readtext(gray, detail=0, allowlist="0123456789")

        numeros_encontrados = []
        for texto in resultados:
            if texto.isdigit():
                val = int(texto)
                if 1 <= val <= 75:
                    numeros_encontrados.append(val)

        if len(numeros_encontrados) < 15:
            st.warning("Poucos números identificados. Tire uma foto mais clara.")
            return None

        nums = numeros_encontrados[:25]
        while len(nums) < 25:
            nums.append(0)

        dados = {
            "B": [nums[0], nums[5], nums[10], nums[15], nums[20]],
            "I": [nums[1], nums[6], nums[11], nums[16], nums[21]],
            "N": [nums[2], nums[7], nums[12], nums[17], nums[22]],
            "G": [nums[3], nums[8], nums[13], nums[18], nums[23]],
            "O": [nums[4], nums[9], nums[14], nums[19], nums[24]],
        }

        return dados
    except Exception as e:
        st.error(f"Erro no OCR: {e}")
        return None


# --- MENU PRINCIPAL ---
st.title("🎲 Bingo 75 Mobile")

menu = st.sidebar.radio(
    "Navegação",
    [
        "Menu Principal",
        "Cadastrar por Foto (IA)",
        "Cadastro Manual",
        "Acompanhar Sorteio",
    ],
    key="main_navigation_radio",
)

if menu == "Menu Principal":
    st.subheader("Bem-vindo ao Gerenciador de Bingo!")
    st.write(
        f"**Cartelas Cadastradas:** {len(st.session_state.cartelas_originais)}"
    )
    st.write(f"**Pedras Sorteadas:** {len(st.session_state.sorteados)}")

    st.divider()

    if st.button("🔄 Novo Sorteio (Manter Cartelas)", use_container_width=True):
        st.session_state.sorteados = []
        for nome, orig in st.session_state.cartelas_originais.items():
            st.session_state.cartelas[nome] = set(orig)
        salvar_dados()
        st.success("Sorteio reiniciado!")
        st.rerun()

    if st.button(
        "❌ Zerar Tudo (Apagar Cartelas)",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.cartelas.clear()
        st.session_state.cartelas_originais.clear()
        st.session_state.sorteados.clear()
        if os.path.exists(ARQUIVO_DADOS):
            os.remove(ARQUIVO_DADOS)
        st.success("Dados apagados.")
        st.rerun()

elif menu == "Cadastrar por Foto (IA)":
    st.subheader("📸 Cadastrar Cartela por Foto")
    nome_cartela = st.text_input("Nome da Cartela:")
    foto = st.file_uploader(
        "Envie ou tire uma foto", type=["jpg", "jpeg", "png"]
    )

    if foto and nome_cartela:
        if st.button("🔍 Ler Cartela com IA", use_container_width=True):
            with st.spinner("Analisando imagem..."):
                resultado = ler_cartela_com_ia(foto.getvalue())
                if resultado:
                    st.session_state["cartela_temp"] = resultado
                    st.success("Leitura concluída!")

    if "cartela_temp" in st.session_state:
        st.divider()
        st.subheader("📋 Confirmação")
        dados_ia = st.session_state["cartela_temp"]
        numeros_finais = set()

        cols = st.columns(5)
        validacao_ok = True

        for i, (letra, (inicio, fim)) in enumerate(REGRAS_COLUNAS.items()):
            with cols[i]:
                st.markdown(f"**{letra}**")
                nums_coluna = dados_ia.get(letra, [])
                for idx, val in enumerate(nums_coluna):
                    num_editado = st.number_input(
                        f"{letra}{idx+1}",
                        min_value=1,
                        max_value=75,
                        value=int(val),
                        key=f"input_{letra}_{idx}",
                        label_visibility="collapsed",
                    )
                    numeros_finais.add(num_editado)
                    if not (inicio <= num_editado <= fim):
                        validacao_ok = False

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "✅ Salvar", type="primary", use_container_width=True
            ):
                if len(numeros_finais) != 25 or not validacao_ok:
                    st.error("Cartela inválida! Verifique os números.")
                else:
                    st.session_state.cartelas_originais[nome_cartela] = set(
                        numeros_finais
                    )
                    st.session_state.cartelas[nome_cartela] = set(
                        numeros_finais
                    )
                    for s in st.session_state.sorteados:
                        st.session_state.cartelas[nome_cartela].discard(s)
                    salvar_dados()
                    del st.session_state["cartela_temp"]
                    st.success("Salvo com sucesso!")
                    st.rerun()
        with col2:
            if st.button("❌ Descartar", use_container_width=True):
                del st.session_state["cartela_temp"]
                st.rerun()

elif menu == "Cadastro Manual":
    st.subheader("➕ Cadastro Manual")
    nome = st.text_input("Nome da Cartela:")
    nums_selecionados = set()

    cols = st.columns(5)
    for i, (letra, (inicio, fim)) in enumerate(REGRAS_COLUNAS.items()):
        with cols[i]:
            st.markdown(f"**{letra}**")
            for n in range(inicio, fim + 1):
                if st.checkbox(str(n), key=f"manual_{n}"):
                    nums_selecionados.add(n)

    if st.button("Salvar Cartela", type="primary", use_container_width=True):
        if not nome or len(nums_selecionados) != 25:
            st.error("Selecione exatamente 25 números!")
        else:
            st.session_state.cartelas_originais[nome] = set(nums_selecionados)
            st.session_state.cartelas[nome] = set(nums_selecionados)
            salvar_dados()
            st.success("Salvo!")

# --- TELA DE SORTEIO (PAINEL MOBILE QUADRADO 5 COLUNAS x 15 LINHAS) ---
elif menu == "Acompanhar Sorteio":
    # CSS focado em espremer os botões ao máximo na horizontal
    st.markdown(
        """
        <style>
        /* Tira as margens laterais da página */
        .block-container {
            padding: 0.5rem 0.2rem !important;
            max-width: 100vw !important;
        }

        /* Força colunas lado a lado sem quebra de linha */
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 1px !important;
            margin: 0px !important;
            padding: 0px !important;
        }

        div[data-testid="column"] {
            width: 20% !important;
            flex: 1 1 20% !important;
            min-width: 0px !important;
            padding: 0px !important;
        }

        /* Formatação em estilo 'quadradinho' para os botões */
        div.stButton > button {
            width: 100% !important;
            height: 28px !important;
            min-height: 28px !important;
            padding: 0px !important;
            font-size: 11px !important;
            font-weight: bold !important;
            border-radius: 2px !important;
            margin: 1px 0px !important;
            line-height: 28px !important;
        }

        /* Remove botão de atalho/ícones internos */
        div.stButton > button p {
            font-size: 11px !important;
            margin: 0 !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.subheader("🎯 Painel de Sorteio")

    # Cabeçalho B I N G O
    cols_header = st.columns(5)
    for idx, letra in enumerate(["B", "I", "N", "G", "O"]):
        cols_header[idx].markdown(
            f"<div style='text-align:center; font-weight:bold; color:#FF4B4B;'>{letra}</div>",
            unsafe_allow_html=True,
        )

    # Renderiza 15 linhas com 5 colunas cada
    for i in range(15):
        cols = st.columns(5)
        numeros_linha = [1 + i, 16 + i, 31 + i, 46 + i, 61 + i]

        for col_idx, n in enumerate(numeros_linha):
            ja_sorteado = n in st.session_state.sorteados
            tipo = "primary" if ja_sorteado else "secondary"
            label = f"{n}"  # Mantém apenas o número para economizar espaço

            if cols[col_idx].button(
                label, key=f"sorteio_{n}", type=tipo, use_container_width=True
            ):
                if ja_sorteado:
                    st.session_state.sorteados.remove(n)
                    for (
                        c_nome,
                        orig,
                    ) in st.session_state.cartelas_originais.items():
                        if n in orig:
                            st.session_state.cartelas[c_nome].add(n)
                else:
                    st.session_state.sorteados.append(n)
                    for c_nome in st.session_state.cartelas:
                        st.session_state.cartelas[c_nome].discard(n)

                salvar_dados()
                st.rerun()

    st.divider()

    st.subheader("🔥 Cartelas Armadas (Faltam ≤ 3)")

    cartelas_armadas = [
        (nome, faltantes)
        for nome, faltantes in st.session_state.cartelas.items()
        if len(faltantes) <= 3
    ]
    cartelas_ordenadas = sorted(cartelas_armadas, key=lambda x: len(x[1]))

    if not cartelas_ordenadas:
        st.info("Nenhuma cartela no momento falta 3 ou menos números.")
    else:
        for nome, faltantes in cartelas_ordenadas:
            qtd = len(faltantes)
            nums_str = (
                ", ".join(map(str, sorted(list(faltantes))))
                if qtd > 0
                else "🏆 BINGO!"
            )

            if qtd == 0:
                st.balloons()
                st.success(f"🏆 **{nome}** - BINGO!")
            else:
                st.warning(f"**{nome}** — Faltam {qtd}: [{nums_str}]")
