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
    st.session_state.chain_of_thought = False  # CoT desativado por padrão

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
            st.write(f"**Limite Atual:** R$ {float(cliente.get('limite_credito', 0)):,.2f}")
            
            # Mostra score e limite máximo se disponível (após entrevista)
            if "ultimo_resultado" in st.session_state:
                resultado = st.session_state.ultimo_resultado
                if resultado and isinstance(resultado, dict) and resultado.get("score_calculado"):
                    st.markdown("---")
                    st.markdown("### 📊 Resultado da Entrevista")
                    st.success(f"**Score:** {resultado['score_calculado']} pontos")
                    if resultado.get("limite_maximo"):
                        st.info(f"**Limite Máximo:** R$ {resultado['limite_maximo']:,.2f}")
    
    st.markdown("---")
    
    # Toggle de Chain-of-Thought
    st.header("⚙️ Configurações")
    cot_enabled = st.toggle(
        "💭 Chain-of-Thought",
        value=st.session_state.get("chain_of_thought", False),
        help="Quando ativado, o agente explica seu raciocínio antes de responder"
    )
    if cot_enabled != st.session_state.get("chain_of_thought", False):
        st.session_state.chain_of_thought = cot_enabled
        st.rerun()
    
    st.markdown("---")
    
    # Seção de Debug da IA
    st.header("🔍 Debug da IA")
    
    # Inicializa debug_info e índice na sessão
    if "debug_info" not in st.session_state:
        st.session_state.debug_info = []
    if "debug_idx" not in st.session_state:
        st.session_state.debug_idx = 0
    if "ultimo_resultado" not in st.session_state:
        st.session_state.ultimo_resultado = {}
    
    if st.session_state.debug_info:
        total = len(st.session_state.debug_info)
        
        # Navegação
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("◀ Anterior", disabled=st.session_state.debug_idx <= 0):
                st.session_state.debug_idx -= 1
                st.rerun()
        
        with col2:
            # Atualiza índice para o último se necessário
            if st.session_state.debug_idx >= total:
                st.session_state.debug_idx = total - 1
            st.markdown(f"**Chamada {st.session_state.debug_idx + 1} de {total}**")
        
        with col3:
            if st.button("Próxima ▶", disabled=st.session_state.debug_idx >= total - 1):
                st.session_state.debug_idx += 1
                st.rerun()
        
        # Botão para ir direto ao último
        if st.button("⏭️ Ir para última chamada"):
            st.session_state.debug_idx = total - 1
            st.rerun()
        
        # Mostra chamada selecionada
        debug = st.session_state.debug_info[st.session_state.debug_idx]
        
        # Info compacta
        modelo = debug.get("modelo_usado", "N/A")
        tempo = debug.get("tempo_ms", 0)
        st.caption(f"🤖 `{modelo}` | ⏱️ {tempo}ms")
        
        if debug.get("contexto"):
            st.caption(f"📍 {debug['contexto']}")
        
        # Raciocínio (Chain-of-Thought) - mostra primeiro se houver
        if debug.get("raciocinio"):
            with st.expander("💭 Raciocínio (Chain-of-Thought)", expanded=True):
                st.info(debug.get("raciocinio", ""))
        
        # Tool calls - usa tool_calls_completos se disponível (tem mais detalhes)
        tool_calls = debug.get("tool_calls_completos", debug.get("tool_calls", []))
        if tool_calls:
            # Suporta tanto formato antigo (lista de strings) quanto novo (lista de dicts)
            if isinstance(tool_calls[0], dict):
                # Filtra responder_usuario (já mostrou o raciocínio acima)
                other_tools = [tc for tc in tool_calls if tc.get("name") != "responder_usuario"]
                
                if other_tools:
                    tool_names = [tc.get("name", "unknown") for tc in other_tools]
                    st.success(f"🔧 Tools: {', '.join(tool_names)}")
                    
                    with st.expander("🔧 Ver detalhes das Tool Calls", expanded=False):
                        for tc in other_tools:
                            st.markdown(f"**{tc.get('name', 'unknown')}**")
                            st.code(f"Args: {tc.get('args', {})}", language="python")
                            if tc.get("result"):
                                st.code(f"Result: {tc.get('result', {})}", language="python")
                            st.markdown("---")
            else:
                st.success(f"🔧 Tools: {', '.join(tool_calls)}")
        
        # System prompt, prompt do usuário e resposta em expanders
        if debug.get("system_prompt"):
            with st.expander("🧠 Ver System Prompt", expanded=False):
                st.code(debug.get("system_prompt", "N/A"), language="text")
        
        with st.expander("📤 Ver Mensagem do Usuário", expanded=False):
            st.code(debug.get("prompt", "N/A"), language="text")
        
        if debug.get("erro"):
            st.error(f"❌ {debug['erro']}")
        else:
            with st.expander("📥 Ver Resposta", expanded=True):
                st.code(debug.get("resposta", "N/A"), language="text")
    else:
        st.info("ℹ️ Nenhuma chamada à IA ainda.")
    
    st.markdown("---")
    
    if st.button("🔄 Reiniciar Conversa"):
        st.session_state.orchestrator.resetar()
        st.session_state.mensagens = []
        st.session_state.encerrado = False
        st.session_state.debug_info = []
        st.session_state.debug_idx = 0
        st.session_state.ultimo_resultado = {}
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
        
        # Processa mensagem (passa config de Chain-of-Thought)
        with st.spinner("Processando..."):
            cot_config = {"chain_of_thought": st.session_state.get("chain_of_thought", False)}
            resultado = st.session_state.orchestrator.processar_mensagem(mensagem_usuario, config=cot_config)
        
        # Armazena informações de debug (acumula se já existir)
        if resultado.get("debug_info"):
            # Se já existe debug_info, adiciona ao final (acumula histórico)
            if st.session_state.debug_info:
                st.session_state.debug_info.extend(resultado["debug_info"])
            else:
                st.session_state.debug_info = resultado["debug_info"]
            # Move índice para a última chamada
            st.session_state.debug_idx = len(st.session_state.debug_info) - 1
        
        # Salva resultado para mostrar score/limite no sidebar
        st.session_state.ultimo_resultado = resultado
        
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

