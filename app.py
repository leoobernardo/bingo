import json
import os
import cv2
import numpy as np
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

ARQUIVO_DADOS = "bingo_dados.json"

REGRAS_COLUNAS = {
    "B": (1, 15),
    "I": (16, 30),
    "N": (31, 45),
    "G": (46, 60),
    "O": (61, 75),
}

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

# --- TELA DE SORTEIO (PAINEL HTML/CSS INTEGRADO ULTRAPACK) ---
# --- TELA DE SORTEIO (PAINEL HTML/CSS COM CLIQUE DIRETO) ---
elif menu == "Acompanhar Sorteio":
    st.subheader("🎯 Painel de Sorteio")
    st.caption("Toque diretamente no número para marcar ou desmarcar:")

    # Captura evento de clique enviado pelo HTML
    params = st.query_params
    if "clique_num" in params:
        num_clicado = int(params["clique_num"])
        # Remove o parâmetro da URL para não repetir em refresh
        st.query_params.clear()

        if num_clicado in st.session_state.sorteados:
            st.session_state.sorteados.remove(num_clicado)
            for c_nome, orig in st.session_state.cartelas_originais.items():
                if num_clicado in orig:
                    st.session_state.cartelas[c_nome].add(num_clicado)
        else:
            st.session_state.sorteados.append(num_clicado)
            for c_nome in st.session_state.cartelas:
                st.session_state.cartelas[c_nome].discard(num_clicado)

        salvar_dados()
        st.rerun()

    sorteados_set = set(st.session_state.sorteados)

    # HTML + JavaScript para lidar com o clique direto nos quadradinhos
    html_grid = """
    <style>
        .bingo-board {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 3px;
            width: 100%;
            max-width: 400px;
            margin: 0 auto;
            font-family: sans-serif;
            user-select: none;
        }
        .header-cell {
            background-color: #FF4B4B;
            color: white;
            font-weight: bold;
            text-align: center;
            padding: 6px 0;
            border-radius: 4px;
            font-size: 14px;
        }
        .num-cell {
            background-color: #262730;
            color: #FAFAFA;
            text-align: center;
            padding: 8px 0;
            border-radius: 3px;
            font-size: 13px;
            font-weight: bold;
            border: 1px solid #363940;
            cursor: pointer;
            -webkit-tap-highlight-color: transparent;
        }
        .num-cell:active {
            transform: scale(0.95);
        }
        .num-cell.active {
            background-color: #FF4B4B;
            color: white;
            border-color: #FF2222;
            box-shadow: 0 0 5px rgba(255, 75, 75, 0.5);
        }
    </style>

    <script>
    function alternarPedra(num) {
        // Envia o número clicado para a URL da aplicação Streamlit
        window.parent.postMessage({
            type: 'streamlit:setQueryParams',
            queryParams: { clique_num: num }
        }, '*');
    }
    </script>

    <div class="bingo-board">
        <div class="header-cell">B</div>
        <div class="header-cell">I</div>
        <div class="header-cell">N</div>
        <div class="header-cell">G</div>
        <div class="header-cell">O</div>
    """

    for i in range(15):
        numeros_linha = [1 + i, 16 + i, 31 + i, 46 + i, 61 + i]
        for n in numeros_linha:
            is_active = "active" if n in sorteados_set else ""
            html_grid += f'<div class="num-cell {is_active}" onclick="alternarPedra({n})">{n}</div>'

    html_grid += "</div>"

    components.html(html_grid, height=530, scrolling=False)

    st.divider()

    # Ranking das cartelas
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
