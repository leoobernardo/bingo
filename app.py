# --- TELA DE SORTEIO (MATRIZ REAL 5 COLUNAS X 15 LINHAS) ---
elif menu == "Acompanhar Sorteio":
    # Força as colunas do Streamlit a ficarem lado a lado mesmo no celular
    st.markdown(
        """
        <style>
        /* Desativa o empilhamento automático em telas pequenas */
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 2px !important;
        }
        [data-testid="column"] {
            width: 20% !important;
            flex: 1 1 20% !important;
            min-width: 0px !important;
        }
        div.stButton > button {
            padding: 2px 0px !important;
            font-size: 11px !important;
            min-height: 32px !important;
            margin: 0px !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.subheader("🎯 Painel de Sorteio")

    # Cabeçalho fixo das 5 colunas B - I - N - G - O
    letras = ["B", "I", "N", "G", "O"]
    cols_header = st.columns(5)
    for idx, letra in enumerate(letras):
        cols_header[idx].markdown(
            f"<h4 style='text-align: center; margin: 0;'>{letra}</h4>",
            unsafe_allow_html=True,
        )

    st.write("")

    # Linha por linha (1 a 15) preenchendo as 5 colunas simultaneamente
    for i in range(15):
        cols = st.columns(5)

        # Para cada linha i:
        # B = 1 + i, I = 16 + i, N = 31 + i, G = 46 + i, O = 61 + i
        numeros_linha = [1 + i, 16 + i, 31 + i, 46 + i, 61 + i]

        for col_idx, n in enumerate(numeros_linha):
            ja_sorteado = n in st.session_state.sorteados
            label = f"🔴{n}" if ja_sorteado else str(n)
            tipo_botao = "primary" if ja_sorteado else "secondary"

            if cols[col_idx].button(
                label,
                key=f"sorteio_{n}",
                type=tipo_botao,
                use_container_width=True,
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
