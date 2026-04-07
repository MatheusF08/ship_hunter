# painel_final.py (Versão Corrigida - Chaves Únicas para Filtros)

import streamlit as st
import pandas as pd
import sqlite3
import subprocess

# --- Configurações ---
DB_FILE = "ship_hunter_prod.db"
TABELAS = {
    "Atracados Agora": "santos_atracados",
    "Programados": "santos_programados",
    "Navios Esperados": "santos_esperados"
}

# --- Funções do Backend ---
@st.cache_data(ttl=600)
def carregar_dados_todas_tabelas():
    """Carrega os dados de todas as tabelas de inteligência do banco de dados."""
    dados = {}
    try:
        with sqlite3.connect(DB_FILE) as conn:
            for nome_amigavel, nome_tabela in TABELAS.items():
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{nome_tabela}';")
                if cursor.fetchone():
                    dados[nome_amigavel] = pd.read_sql_query(f"SELECT * FROM {nome_tabela}", conn)
                else:
                    dados[nome_amigavel] = pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco de dados: {e}")
        for nome_amigavel in TABELAS.keys():
            dados[nome_amigavel] = pd.DataFrame()
    return dados

def executar_coleta_dados():
    """Executa o script de coleta de dados e mostra o log."""
    try:
        with st.spinner("Iniciando a coleta de dados 360º... Isso pode levar um minuto."):
            resultado = subprocess.run(
                ["python", "fase0_inteligencia_geral.py"],
                capture_output=True, text=True, check=True, timeout=180
            )
        st.success("Coleta de dados concluída com sucesso!")
        with st.expander("Ver log de execução da coleta"):
            st.code(resultado.stdout)
    except subprocess.CalledProcessError as e:
        st.error("Ocorreu um erro durante a coleta de dados.")
        with st.expander("Ver detalhes do erro"):
            st.code(e.stderr)
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao executar o script: {e}")

# --- Interface do Usuário (Frontend) ---
st.set_page_config(page_title="Inteligência Portuária 360º", layout="wide")

st.title("🚢 Inteligência Portuária 360º - Porto de Santos")
st.markdown("Visão completa e interativa das operações: Navios Atracados, Programados e Esperados.")

# Carrega os dados de todas as tabelas
todos_os_dados = carregar_dados_todas_tabelas()

# --- Barra Lateral com Ações e Filtros ---
with st.sidebar:
    st.header("Painel de Controle")
    if st.button("🔄 Atualizar Todos os Dados Agora"):
        executar_coleta_dados()
        st.cache_data.clear()
        st.rerun()
    
    st.header("Filtros de Análise")
    
    filtro_nome_navio = st.text_input("Buscar por Nome do Navio:")

    agencias_programados = todos_os_dados.get("Programados", pd.DataFrame()).get('agencia', pd.Series(dtype=str))
    agencias_esperados = todos_os_dados.get("Navios Esperados", pd.DataFrame()).get('agencia', pd.Series(dtype=str))
    todas_as_agencias = pd.concat([agencias_programados, agencias_esperados]).dropna().unique()
    
    if todas_as_agencias.any():
        opcoes_agencia = sorted(todas_as_agencias)
        filtro_agencia = st.multiselect("Filtrar por Agência:", options=opcoes_agencia)
    else:
        filtro_agencia = []

# Cria abas para cada tipo de dado
tab1, tab2, tab3 = st.tabs(["🚢 Atracados Agora", "🗓️ Programados", "🔭 Navios Esperados"])

# 🔥 CORREÇÃO: A função agora aceita um 'tab_name' para criar chaves únicas
def exibir_tabela_filtrada(df, tab_name, nome_coluna_navio, nome_coluna_carga, nome_coluna_agencia=None):
    if df.empty:
        st.info("Nenhum dado encontrado para esta categoria. Execute a atualização.")
        return

    df_filtrado = df.copy()

    if filtro_nome_navio:
        df_filtrado = df_filtrado[df_filtrado[nome_coluna_navio].str.contains(filtro_nome_navio, case=False, na=False)]
    
    if filtro_agencia and nome_coluna_agencia and nome_coluna_agencia in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado[nome_coluna_agencia].isin(filtro_agencia)]

    if nome_coluna_carga in df_filtrado.columns:
        opcoes_carga = sorted(df_filtrado[nome_coluna_carga].dropna().unique())
        # 🔥 CORREÇÃO: A chave agora é única para cada aba (ex: 'filtro_carga_atracados')
        filtro_carga_local = st.multiselect(f"Filtrar por Carga/Mercadoria:", options=opcoes_carga, key=f"filtro_carga_{tab_name}")
        if filtro_carga_local:
            df_filtrado = df_filtrado[df_filtrado[nome_coluna_carga].isin(filtro_carga_local)]
    
    st.dataframe(df_filtrado, use_container_width=True)
    st.caption(f"Exibindo {len(df_filtrado)} de {len(df)} registros.")

with tab1:
    st.header(f"Navios Atracados ({len(todos_os_dados.get('Atracados Agora', []))} registros)")
    # 🔥 CORREÇÃO: Passando 'atracados' como nome da aba para a chave
    exibir_tabela_filtrada(todos_os_dados.get("Atracados Agora"), tab_name="atracados", nome_coluna_navio='navio', nome_coluna_carga='carga')

with tab2:
    st.header(f"Atracações Programadas ({len(todos_os_dados.get('Programados', []))} registros)")
    # 🔥 CORREÇÃO: Passando 'programados' como nome da aba para a chave
    exibir_tabela_filtrada(todos_os_dados.get("Programados"), tab_name="programados", nome_coluna_navio='navio', nome_coluna_carga='carga')

with tab3:
    st.header(f"Navios Esperados ({len(todos_os_dados.get('Navios Esperados', []))} registros)")
    df_esperados = todos_os_dados.get("Navios Esperados")
    
    if df_esperados is not None and not df_esperados.empty:
        df_filtrado_esperados = df_esperados.copy()

        if filtro_nome_navio:
            df_filtrado_esperados = df_filtrado_esperados[df_filtrado_esperados['navio'].str.contains(filtro_nome_navio, case=False, na=False)]
        if filtro_agencia and 'agencia' in df_filtrado_esperados.columns:
            df_filtrado_esperados = df_filtrado_esperados[df_filtrado_esperados['agencia'].isin(filtro_agencia)]

        col1, col2 = st.columns(2)
        with col1:
            if 'categoria_carga' in df_filtrado_esperados.columns:
                opcoes_categoria = sorted(df_filtrado_esperados['categoria_carga'].dropna().unique())
                filtro_categoria = st.multiselect("Filtrar por Categoria de Carga:", options=opcoes_categoria, key="filtro_categoria_esperados")
                if filtro_categoria:
                    df_filtrado_esperados = df_filtrado_esperados[df_filtrado_esperados['categoria_carga'].isin(filtro_categoria)]
        with col2:
            if 'mercadoria' in df_filtrado_esperados.columns:
                opcoes_mercadoria = sorted(df_filtrado_esperados['mercadoria'].dropna().unique())
                filtro_mercadoria = st.multiselect("Filtrar por Mercadoria Específica:", options=opcoes_mercadoria, key="filtro_mercadoria_esperados")
                if filtro_mercadoria:
                    df_filtrado_esperados = df_filtrado_esperados[df_filtrado_esperados['mercadoria'].isin(filtro_mercadoria)]

        st.dataframe(df_filtrado_esperados, use_container_width=True)
        st.caption(f"Exibindo {len(df_filtrado_esperados)} de {len(df_esperados)} registros.")
    else:
        st.info("Nenhum dado de navios esperados encontrado. Execute a atualização.")
