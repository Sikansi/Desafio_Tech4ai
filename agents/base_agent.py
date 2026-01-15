"""
Classe base para todos os agentes - Refatorada com Tool Calling nativo e Memória
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.tools import tool
import time


class BaseAgent(ABC):
    """Classe base abstrata para todos os agentes do sistema"""
    
    # Cache compartilhado de modelos esgotados (compartilhado entre todas as instâncias)
    _modelos_esgotados_compartilhado = set()
    
    # Memória compartilhada entre agentes (para manter contexto na troca)
    _memoria_compartilhada = None
    
    # Lista ordenada de modelos - vai direto para lite quando quota esgota
    # Modelos da mesma família compartilham quota, então pulamos para lite direto
    MODELOS_FALLBACK = [
        "gemini-2.5-flash",           # Principal
        "gemini-2.5-flash-lite",      # Fallback direto (lite tem quota separada)
        "gemini-2.0-flash",           # Alternativa
        "gemini-2.0-flash-lite",      # Alternativa lite
    ]
    
    # Timeout em segundos para chamadas à API
    # Gemini exige mínimo de 10 segundos
    REQUEST_TIMEOUT = 10
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Inicializa o agente base
        
        Args:
            api_key: Chave da API do Google Gemini
            model: Nome do modelo a ser usado
        """
        import os
        
        # Obtém API key
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY não encontrada. Configure no arquivo .env")
        
        self.api_key = api_key
        
        # Obtém modelo inicial da variável de ambiente ou usa padrão
        if not model:
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Garante que o modelo inicial está na lista de fallback
        if model not in self.MODELOS_FALLBACK:
            self.MODELOS_FALLBACK.insert(0, model)
        
        # Usa cache compartilhado de modelos esgotados
        self.modelos_esgotados = BaseAgent._modelos_esgotados_compartilhado
        
        # Procura o primeiro modelo disponível (não esgotado)
        self.modelo_atual = self._encontrar_modelo_disponivel(model)
        self.modelo_atual_idx = self.MODELOS_FALLBACK.index(self.modelo_atual) if self.modelo_atual in self.MODELOS_FALLBACK else 0
        
        # Inicializa o LLM com timeout curto
        self.llm = self._criar_llm(self.modelo_atual)
        
        # LLM com tools (será configurado por cada agente)
        self.llm_with_tools = None
        self.tools = []
        self.tools_by_name = {}
        
        # Inicializa memória compartilhada se não existir
        if BaseAgent._memoria_compartilhada is None:
            BaseAgent._memoria_compartilhada = InMemoryChatMessageHistory()
        self.memory = BaseAgent._memoria_compartilhada
        
        # Debug info (apenas para a sessão atual)
        self.debug_info = []
    
    def _encontrar_modelo_disponivel(self, modelo_preferido: str) -> str:
        """Encontra o primeiro modelo disponível que não está esgotado"""
        # Tenta o modelo preferido primeiro
        if modelo_preferido not in self.modelos_esgotados:
            return modelo_preferido
        
        # Procura na lista de fallback
        for modelo in self.MODELOS_FALLBACK:
            if modelo not in self.modelos_esgotados:
                return modelo
        
        # Se todos estão esgotados, retorna o preferido mesmo (vai falhar mas é melhor que nada)
        return modelo_preferido
    
    def _criar_llm(self, model: str) -> ChatGoogleGenerativeAI:
        """Cria uma instância do LLM com o modelo especificado e timeout curto"""
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self.api_key,
            temperature=0.7,
            request_timeout=self.REQUEST_TIMEOUT,  # Timeout curto!
        )
    
    def registrar_tools(self, tools: List[Callable]):
        """
        Registra ferramentas (tools) para o agente usar.
        Deve ser chamado após __init__ por cada agente específico.
        
        Args:
            tools: Lista de funções decoradas com @tool
        """
        self.tools = tools
        self.tools_by_name = {t.name: t for t in tools}
        self.llm_with_tools = self.llm.bind_tools(tools)
    
    def _trocar_modelo(self) -> bool:
        """
        Tenta trocar para o próximo modelo disponível da lista de fallback.
        Retorna True se conseguiu trocar, False se não há mais modelos.
        """
        # Marca o modelo atual como esgotado
        modelo_anterior = self.modelo_atual
        self.modelos_esgotados.add(self.modelo_atual)
        
        # Procura o próximo modelo disponível
        for idx in range(self.modelo_atual_idx + 1, len(self.MODELOS_FALLBACK)):
            modelo_candidato = self.MODELOS_FALLBACK[idx]
            if modelo_candidato not in self.modelos_esgotados:
                self.modelo_atual_idx = idx
                self.modelo_atual = modelo_candidato
                self.llm = self._criar_llm(self.modelo_atual)
                
                # Atualiza LLM com tools se existirem
                if self.tools:
                    self.llm_with_tools = self.llm.bind_tools(self.tools)
                
                print(f"[GATEWAY] Modelo trocado: {modelo_anterior} → {self.modelo_atual}")
                return True
        
        return False
    
    def _is_quota_exceeded_error(self, error: Exception) -> bool:
        """Verifica se o erro é de quota excedida (429 RESOURCE_EXHAUSTED)"""
        error_str = str(error)
        return "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()
    
    def obter_historico_memoria(self) -> List:
        """Obtém histórico de mensagens da memória"""
        return self.memory.messages if self.memory.messages else []
    
    def adicionar_a_memoria(self, mensagem_usuario: str, resposta_ia: str):
        """Adiciona interação à memória compartilhada"""
        self.memory.add_user_message(mensagem_usuario)
        self.memory.add_ai_message(resposta_ia)
    
    def limpar_memoria(self):
        """Limpa a memória de conversa"""
        self.memory.clear()
        self.debug_info = []
    
    def resetar_debug_info(self):
        """Limpa apenas as informações de debug"""
        self.debug_info = []
    
    def obter_debug_info(self) -> list:
        """Retorna informações de debug"""
        return self.debug_info
    
    @abstractmethod
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma mensagem do usuário"""
        pass
    
    def _extrair_texto_resposta(self, content: Any) -> str:
        """
        Extrai texto da resposta do LLM, que pode vir em diferentes formatos.
        
        Args:
            content: Conteúdo da resposta (pode ser str, list, ou None)
            
        Returns:
            Texto extraído como string
        """
        if content is None:
            return ""
        
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            # Formato: [{'type': 'text', 'text': '...'}, ...]
            textos = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    textos.append(item.get("text", ""))
                elif isinstance(item, str):
                    textos.append(item)
            return " ".join(textos)
        
        # Tenta converter para string
        return str(content)
    
    def invocar_llm(self, mensagens: List, contexto_debug: str = "") -> Any:
        """
        Invoca o LLM com fallback automático de modelos.
        Usa timeout curto para falhar rápido em erros de quota.
        
        Args:
            mensagens: Lista de mensagens para enviar ao LLM
            contexto_debug: Contexto para debug
            
        Returns:
            Resposta do LLM
        """
        max_tentativas = len(self.MODELOS_FALLBACK)
        tentativas = 0
        
        while tentativas < max_tentativas:
            # Verifica se modelo atual está esgotado antes de tentar
            if self.modelo_atual in self.modelos_esgotados:
                if not self._trocar_modelo():
                    raise Exception("Todos os modelos estão esgotados.")
                continue
            
            try:
                inicio = time.time()
                
                # Usa LLM com tools se disponível, senão usa LLM normal
                llm_to_use = self.llm_with_tools if self.llm_with_tools else self.llm
                resposta = llm_to_use.invoke(mensagens)
                
                tempo = time.time() - inicio
                
                # Extrai texto da resposta de forma segura
                texto_resposta = self._extrair_texto_resposta(resposta.content)
                
                # Log de debug
                prompt_resumo = str(mensagens[-1].content)[:200] if mensagens else ""
                self.debug_info.append({
                    "contexto": contexto_debug,
                    "prompt": prompt_resumo,
                    "resposta": texto_resposta[:200] if texto_resposta else "[tool_calls]",
                    "tool_calls": [tc["name"] for tc in resposta.tool_calls] if resposta.tool_calls else [],
                    "modelo_usado": self.modelo_atual,
                    "tempo_ms": int(tempo * 1000),
                    "erro": None
                })
                
                return resposta
                
            except Exception as e:
                tentativas += 1
                
                if self._is_quota_exceeded_error(e):
                    # Troca de modelo é instantânea
                    if self._trocar_modelo():
                        continue
                    else:
                        erro = f"Todos os modelos esgotados: {', '.join(self.modelos_esgotados)}"
                        self.debug_info.append({
                            "contexto": contexto_debug,
                            "prompt": str(mensagens[-1].content)[:200] if mensagens else "",
                            "resposta": None,
                            "tool_calls": [],
                            "modelo_usado": self.modelo_atual,
                            "tempo_ms": 0,
                            "erro": erro
                        })
                        raise Exception(erro)
                else:
                    # Erro não relacionado a quota
                    self.debug_info.append({
                        "contexto": contexto_debug,
                        "prompt": str(mensagens[-1].content)[:200] if mensagens else "",
                        "resposta": None,
                        "tool_calls": [],
                        "modelo_usado": self.modelo_atual,
                        "tempo_ms": 0,
                        "erro": str(e)
                    })
                    raise Exception(f"Erro ao chamar LLM: {str(e)}")
        
        raise Exception("Máximo de tentativas excedido.")
    
    def processar_com_tools(
        self, 
        prompt_sistema: str, 
        mensagem_usuario: str,
        contexto_debug: str = "",
        usar_memoria: bool = True
    ) -> tuple:
        """
        Processa mensagem usando o sistema de Tool Calling nativo.
        
        Args:
            prompt_sistema: Prompt de sistema explicando contexto e responsabilidades
            mensagem_usuario: Mensagem do usuário
            contexto_debug: Contexto para debug
            usar_memoria: Se deve incluir histórico da memória
            
        Returns:
            tuple: (resposta_texto, tool_calls_executados)
                - resposta_texto: Texto final da resposta
                - tool_calls_executados: Lista de dicts com {name, args, result}
        """
        mensagens = [SystemMessage(content=prompt_sistema)]
        
        # Adiciona histórico da memória se solicitado
        if usar_memoria:
            historico = self.obter_historico_memoria()
            # Limita histórico para não exceder contexto
            mensagens.extend(historico[-10:])  # Últimas 10 mensagens
        
        mensagens.append(HumanMessage(content=mensagem_usuario))
        
        # Primeira chamada ao LLM
        resposta = self.invocar_llm(mensagens, contexto_debug)
        
        tool_calls_executados = []
        
        # Se tem tool_calls, executa as ferramentas
        while resposta.tool_calls:
            # Adiciona resposta da IA com tool_calls
            mensagens.append(resposta)
            
            for tool_call in resposta.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Executa a ferramenta
                if tool_name in self.tools_by_name:
                    try:
                        tool_result = self.tools_by_name[tool_name].invoke(tool_args)
                    except Exception as e:
                        tool_result = f"Erro ao executar {tool_name}: {str(e)}"
                else:
                    tool_result = f"Ferramenta {tool_name} não encontrada"
                
                tool_calls_executados.append({
                    "name": tool_name,
                    "args": tool_args,
                    "result": tool_result
                })
                
                # Adiciona resultado da ferramenta às mensagens
                mensagens.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"]
                ))
            
            # Chama LLM novamente para gerar resposta final
            resposta = self.invocar_llm(mensagens, f"{contexto_debug} - após tools")
        
        # Extrai texto da resposta de forma segura
        texto_resposta = self._extrair_texto_resposta(resposta.content)
        return (texto_resposta, tool_calls_executados)
    
    # ==================== MÉTODOS LEGADOS (para compatibilidade) ====================
    
    def adicionar_mensagem(self, mensagem: str, tipo: str = "human"):
        """LEGADO: Adiciona mensagem ao histórico (mantido para compatibilidade)"""
        if tipo == "human":
            self.memory.add_user_message(mensagem)
        else:
            self.memory.add_ai_message(mensagem)
    
    def limpar_historico(self):
        """LEGADO: Limpa o histórico (agora limpa a memória)"""
        self.limpar_memoria()
    
    def gerar_resposta(self, prompt: str, contexto_adicional: str = "", usar_historico: bool = True) -> str:
        """
        LEGADO: Método antigo mantido para compatibilidade.
        Recomendado usar processar_com_tools() para novos desenvolvimentos.
        """
        mensagens = []
        
        if usar_historico:
            mensagens.extend(self.obter_historico_memoria()[-6:])
        
        mensagens.append(HumanMessage(content=prompt))
        
        resposta = self.invocar_llm(mensagens, contexto_adicional)
        return self._extrair_texto_resposta(resposta.content)
    
    def processar_com_comandos(self, prompt: str, contexto_adicional: str = "", usar_historico: bool = False) -> tuple:
        """
        LEGADO: Método antigo de comandos textuais.
        Mantido para compatibilidade durante migração.
        """
        resposta_llm = self.gerar_resposta(prompt, contexto_adicional=contexto_adicional, usar_historico=usar_historico)
        resposta_stripped = resposta_llm.strip()
        resposta_normalizada = " ".join(resposta_stripped.split())
        
        # Verifica comando com dados (COMANDO:dados)
        if ":" in resposta_normalizada:
            partes = resposta_normalizada.split(":", 1)
            comando = partes[0].strip().upper()
            dados = partes[1].strip() if len(partes) > 1 else ""
            if comando.replace("_", "").isalnum() and len(comando.split()) == 1:
                return (None, comando, {"dados": dados})
        
        # Verifica comando simples
        comando_candidato = resposta_normalizada.upper()
        if comando_candidato.replace("_", "").isalnum() and len(comando_candidato.split()) == 1:
            return (None, comando_candidato, None)
        
        return (resposta_llm, None, None)
