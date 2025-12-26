"""
Interface Streamlit para o Sistema de Agentes Bancários
"""
import streamlit as st
import os
from dotenv import load_dotenv
from orchestrator import Orchestrator

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="Banco Ágil - Atendimento Virtual",
    page_icon="🏦",
    layout="wide"
)

# Inicializa o orquestrador na sessão
if "orchestrator" not in st.session_state:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("⚠️ GOOGLE_API_KEY não encontrada! Configure no arquivo .env")
        st.stop()
    st.session_state.orchestrator = Orchestrator(api_key=api_key)
    st.session_state.mensagens = []
    st.session_state.encerrado = False

# Título e descrição
st.title("🏦 Banco Ágil - Atendimento Virtual")
st.markdown("---")
st.markdown("""
Bem-vindo ao nosso sistema de atendimento inteligente! 
Nossos agentes especializados estão prontos para ajudá-lo com:
- 🔐 Autenticação e triagem
- 💳 Consultas e solicitações de crédito
- 📊 Entrevista de crédito para atualização de score
- 💱 Consulta de cotações de moedas
""")

# Sidebar com informações
with st.sidebar:
    st.header("ℹ️ Informações")
    st.markdown("""
    ### Agente Atual
    **{}**
    """.format(st.session_state.orchestrator._obter_nome_agente_atual()))
    
    if st.session_state.orchestrator.contexto.get("autenticado"):
        cliente = st.session_state.orchestrator.contexto.get("cliente")
        if cliente:
            st.markdown("### 👤 Cliente Autenticado")
            st.write(f"**Nome:** {cliente.get('nome', 'N/A')}")
            st.write(f"**CPF:** {cliente.get('cpf', 'N/A')}")
            st.write(f"**Limite:** R$ {float(cliente.get('limite_credito', 0)):,.2f}")
            # Score removido da interface para manter sigilo (boa prática bancária)
    
    st.markdown("---")
    
    # Seção de Debug da IA (sempre visível)
    st.header("🔍 Debug da IA")
    
    # Inicializa debug_info na sessão se não existir
    if "debug_info" not in st.session_state:
        st.session_state.debug_info = []
    
    # Mostra informações de debug da última interação
    with st.expander("📋 Ver Prompts e Respostas da IA", expanded=True):
        if st.session_state.debug_info:
            for idx, debug in enumerate(st.session_state.debug_info):
                st.markdown(f"**### Chamada {idx + 1}**")
                
                if debug.get("contexto"):
                    st.markdown(f"**Contexto:** `{debug['contexto']}`")
                
                st.markdown("**Prompt enviado para a IA:**")
                st.code(debug.get("prompt", "N/A"), language="text")
                
                if debug.get("erro"):
                    st.error(f"**❌ Erro:** {debug['erro']}")
                else:
                    st.markdown("**Resposta da IA:**")
                    st.code(debug.get("resposta", "N/A"), language="text")
                
                if idx < len(st.session_state.debug_info) - 1:
                    st.markdown("---")
        else:
            st.info("ℹ️ Nenhuma chamada à IA ainda. Envie uma mensagem para ver os prompts e respostas.")
    
    st.markdown("---")
    
    if st.button("🔄 Reiniciar Conversa"):
        st.session_state.orchestrator.resetar()
        st.session_state.mensagens = []
        st.session_state.encerrado = False
        st.session_state.debug_info = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📝 Dados de Teste")
    st.markdown("""
    **CPF:** 12345678900  
    **Data Nascimento:** 15/05/1990
    
    **CPF:** 98765432100  
    **Data Nascimento:** 22/08/1985
    """)

# Área de mensagens
st.header("💬 Conversa")

# Exibe histórico de mensagens
for idx, msg in enumerate(st.session_state.mensagens):
    if msg["tipo"] == "usuario":
        with st.chat_message("user"):
            st.write(msg["conteudo"])
    else:
        with st.chat_message("assistant"):
            st.write(msg["conteudo"])
            if msg.get("agente"):
                st.caption(f"Agente: {msg['agente']}")

# Se a conversa foi encerrada, mostra mensagem
if st.session_state.encerrado:
    st.info("💬 A conversa foi encerrada. Clique em 'Reiniciar Conversa' para começar uma nova.")
else:
    # Input do usuário
    mensagem_usuario = st.chat_input("Digite sua mensagem aqui...")
    
    if mensagem_usuario:
        # Adiciona mensagem do usuário
        st.session_state.mensagens.append({
            "tipo": "usuario",
            "conteudo": mensagem_usuario
        })
        
        # Processa mensagem
        with st.spinner("Processando..."):
            resultado = st.session_state.orchestrator.processar_mensagem(mensagem_usuario)
        
        # Armazena informações de debug (acumula se já existir)
        if resultado.get("debug_info"):
            # Se já existe debug_info, adiciona ao final (acumula histórico)
            if st.session_state.debug_info:
                st.session_state.debug_info.extend(resultado["debug_info"])
            else:
                st.session_state.debug_info = resultado["debug_info"]
        
        # Se houve erro, mostra alerta
        if resultado.get("erro"):
            st.error(f"⚠️ Erro na interpretação da IA: {resultado['erro']}")
        
        # Adiciona resposta do agente
        st.session_state.mensagens.append({
            "tipo": "agente",
            "conteudo": resultado["resposta"],
            "agente": resultado["agente_atual"]
        })
        
        # Verifica se deve encerrar
        if resultado.get("encerrar"):
            st.session_state.encerrado = True
        
        st.rerun()

# Rodapé
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>Banco Ágil - Sistema de Agentes Inteligentes | Desenvolvido para Tech4Humans</small>
</div>
""", unsafe_allow_html=True)

