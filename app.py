import json
import os
from google import genai
from google.genai import types
import streamlit as st

ARQUIVO_DADOS = "bingo_dados.json"

# Regras das colunas do Bingo Tradicional (75 Bolas)
REGRAS_COLUNAS = {
    "B": (1, 15),
    "I": (16, 30),
    "N": (31, 45),
    "G": (46, 60),
    "O": (61, 75),
}

# --- CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(
    page_title="Bingo 75 Vision", page_icon="🎲", layout="centered"
)


# --- GERENCIAMENTO DE DADOS (PERSISTÊNCIA) ---
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


# Inicializa a sessão
if "cartelas" not in st.session_state:
    (
        st.session_state.cartelas,
        st.session_state.cartelas_originais,
        st.session_state.sorteados,
    ) = carregar_dados()


# --- FUNÇÃO DE LEITURA COM GEMINI VISION ---
def ler_cartela_com_ia(imagem_bytes):
    """Envia a foto para a API do Gemini processar os números da cartela."""
    api_key = os.environ.get(
        "GEMINI_API_KEY", st.secrets.get("GEMINI_API_KEY", "")
    )
    if not api_key:
        st.error(
            "Chave API do Gemini não configurada! Configure a variável GEMINI_API_KEY nos Secrets do Streamlit."
        )
        return None

    # Inicializa o cliente padrão da SDK
    client = genai.Client(api_key=api_key)

    prompt = """
    Examine esta imagem de uma cartela de bingo tradicional de 75 bolas.
    A cartela possui 5 colunas: B (1-15), I (16-30), N (31-45), G (46-60), O (61-75).
    Extraia exatamente os 5 números presentes em cada coluna.
    Retorne estritamente um JSON no seguinte formato válido, sem formatação markdown em volta:
    {
        "B": [num1, num2, num3, num4, num5],
        "I": [num1, num2, num3, num4, num5],
        "N": [num1, num2, num3, num4, num5],
        "G": [num1, num2, num3, num4, num5],
        "O": [num1, num2, num3, num4, num5]
    }
    """

    imagem_part = types.Part.from_bytes(
        data=imagem_bytes,
        mime_type="image/jpeg",
    )

    # Nomes oficiais válidos na SDK atual
    modelos = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]

    ultimo_erro = None

    for modelo in modelos:
        try:
            response = client.models.generate_content(
                model=modelo, contents=[imagem_part, prompt]
            )

            texto_limpo = (
                response.text.strip().replace("```json", "").replace("```", "")
            )
            dados = json.loads(texto_limpo)
            return dados
        except Exception as e:
            ultimo_erro = e
            continue

    st.error(f"Erro ao ler imagem com IA: {ultimo_erro}")
    return None





# --- INTERFACE E NAVEGAÇÃO ---
st.title("🎲 Bingo 75 Mobile")

menu = st.sidebar.radio(
    "Navegação",
    [
        "Menu Principal",
        "Cadastrar por Foto (IA)",
        "Cadastro Manual",
        "Acompanhar Sorteio",
    ],
)

# --- MENU PRINCIPAL ---
if menu == "Menu Principal":
    st.subheader("Bem-vindo ao Gerenciador de Bingo!")
    st.write(
        f"**Cartelas Cadastradas:** {len(st.session_state.cartelas_originais)}"
    )
    st.write(
        f"**Pedras Sorteadas:** {len(st.session_state.sorteados)} pedras"
    )

    st.divider()

    if st.button("🔄 Novo Sorteio (Manter Cartelas)", use_container_width=True):
        st.session_state.sorteados = []
        for nome, orig in st.session_state.cartelas_originais.items():
            st.session_state.cartelas[nome] = set(orig)
        salvar_dados()
        st.success("Sorteio reiniciado! Cartelas mantidas.")
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
        st.success("Todos os dados foram apagados.")
        st.rerun()


# --- CADASTRO POR FOTO (IA) ---
elif menu == "Cadastrar por Foto (IA)":
    st.subheader("📸 Cadastrar Cartela por Foto")

    nome_cartela = st.text_input("Nome / Identificador da Cartela:")

    foto = st.camera_input("Tire uma foto da cartela de bingo")

    if foto and nome_cartela:
        if st.button("🔍 Ler Cartela com IA", use_container_width=True):
            with st.spinner("IA analisando a imagem..."):
                bytes_foto = foto.getvalue()
                resultado = ler_cartela_com_ia(bytes_foto)

                if resultado:
                    st.session_state["cartela_temp"] = resultado
                    st.success("Leitura concluída! Confira os números abaixo.")

    # TELA DE CONFIRMAÇÃO E VALIDAÇÃO
    if "cartela_temp" in st.session_state:
        st.divider()
        st.subheader("📋 Confirmação da Leitura")
        st.info("Confira se os números lidos pela IA estão corretos:")

        dados_ia = st.session_state["cartela_temp"]
        numeros_finais = set()

        cols = st.columns(5)
        validacao_ok = True

        for i, (letra, (inicio, fim)) in enumerate(REGRAS_COLUNAS.items()):
            with cols[i]:
                st.markdown(f"### **{letra}**")
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

                    # Valida regras de intervalo por coluna
                    if not (inicio <= num_editado <= fim):
                        validacao_ok = False

        st.write(f"**Total de Números Únicos:** {len(numeros_finais)} / 25")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "✅ Confirmar e Salvar",
                type="primary",
                use_container_width=True,
            ):
                if len(numeros_finais) != 25 or not validacao_ok:
                    st.error(
                        "Erro: A cartela precisa ter exatamente 25 números válidos dentro das faixas B-I-N-G-O!"
                    )
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
                    st.success(
                        f"Cartela '{nome_cartela}' cadastrada com sucesso!"
                    )
                    st.rerun()

        with col2:
            if st.button("❌ Descartar", use_container_width=True):
                del st.session_state["cartela_temp"]
                st.rerun()


# --- CADASTRO MANUAL ---
elif menu == "Cadastro Manual":
    st.subheader("➕ Cadastro Manual")
    nome = st.text_input("Nome da Cartela:")

    st.write("Selecione os 25 números (5 por coluna):")
    nums_selecionados = set()

    cols = st.columns(5)
    for i, (letra, (inicio, fim)) in enumerate(REGRAS_COLUNAS.items()):
        with cols[i]:
            st.markdown(f"**{letra}** ({inicio}-{fim})")
            for n in range(inicio, fim + 1):
                if st.checkbox(str(n), key=f"manual_{n}"):
                    nums_selecionados.add(n)

    st.write(f"**Selecionados:** {len(nums_selecionados)}/25")

    if st.button("Salvar Cartela", type="primary", use_container_width=True):
        if not nome or len(nums_selecionados) != 25:
            st.error("Preencha o nome e selecione exatamente 25 números!")
        else:
            st.session_state.cartelas_originais[nome] = set(nums_selecionados)
            st.session_state.cartelas[nome] = set(nums_selecionados)
            salvar_dados()
            st.success("Cartela cadastrada com sucesso!")


# --- TELA DE SORTEIO ---
elif menu == "Acompanhar Sorteio":
    st.subheader("🎯 Painel de Sorteio")

    # Grade de Pedras (1 a 75)
    st.write("Clique no número para marcar como sorteado:")

    cols = st.columns(5)
    for i, (letra, (inicio, fim)) in enumerate(REGRAS_COLUNAS.items()):
        with cols[i]:
            st.markdown(f"### **{letra}**")
            for n in range(inicio, fim + 1):
                ja_sorteado = n in st.session_state.sorteados
                label = f"🔴 {n}" if ja_sorteado else str(n)

                if st.button(
                    label,
                    key=f"sorteio_{n}",
                    use_container_width=True,
                    disabled=ja_sorteado,
                ):
                    st.session_state.sorteados.append(n)
                    for c_nome in st.session_state.cartelas:
                        st.session_state.cartelas[c_nome].discard(n)
                    salvar_dados()
                    st.rerun()

    st.divider()

    # Ranking: Exibe apenas quem falta <= 3 números
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
