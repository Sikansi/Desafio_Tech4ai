"""
Classe base para todos os agentes
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class BaseAgent(ABC):
    """Classe base abstrata para todos os agentes do sistema"""
    
    # Cache compartilhado de modelos esgotados (compartilhado entre todas as instâncias)
    _modelos_esgotados_compartilhado = set()
    
    # Lista ordenada de modelos por preferência (do melhor para o pior)
    # Ordem baseada em: qualidade, estabilidade, velocidade e limites de quota
    # ATUALIZADO: Apenas modelos que realmente existem na API (verificado com listar_modelos.py)
    MODELOS_FALLBACK = [
        # Modelos mais recentes e estáveis (prioridade máxima)
        "gemini-2.5-flash",           # Mais recente, rápido, estável (recomendado)
        "gemini-2.5-pro",             # Mais recente Pro, muito capaz
        
        # Modelos 2.0 estáveis
        "gemini-2.0-flash-001",       # Estável, rápido
        "gemini-2.0-flash",           # Versão atual, rápido
        
        # Modelos "latest" (sempre atualizados)
        "gemini-pro-latest",          # Última versão Pro
        "gemini-flash-latest",        # Última versão Flash
        
        # Modelos Flash Lite (mais leves, podem ter limites maiores)
        "gemini-2.5-flash-lite",      # Versão lite 2.5, mais leve
        "gemini-2.0-flash-lite-001",  # Flash Lite estável
        "gemini-2.0-flash-lite",      # Flash Lite atual
        "gemini-flash-lite-latest",   # Última versão Flash Lite
        
        # Modelos Gemma (open source, podem ter limites diferentes)
        "gemma-3-27b-it",            # Maior modelo Gemma
        "gemma-3-12b-it",            # Modelo médio Gemma
        "gemma-3-4b-it",             # Modelo pequeno Gemma
        "gemma-3-1b-it",             # Modelo muito pequeno Gemma
    ]
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Inicializa o agente base
        
        Args:
            api_key: Chave da API do Google Gemini
            model: Nome do modelo a ser usado (padrão: gemini-2.5-flash ou da variável GEMINI_MODEL)
                   Use o script listar_modelos.py para ver modelos disponíveis
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
            # Adiciona no início da lista se não estiver
            self.MODELOS_FALLBACK.insert(0, model)
        
        # Usa cache compartilhado de modelos esgotados (compartilhado entre todas as instâncias)
        self.modelos_esgotados = BaseAgent._modelos_esgotados_compartilhado
        
        # Índice do modelo atual na lista de fallback
        # Se o modelo inicial já está esgotado, procura o primeiro disponível
        if model in self.MODELOS_FALLBACK:
            idx_inicial = self.MODELOS_FALLBACK.index(model)
        else:
            idx_inicial = 0
        
        # Procura o primeiro modelo disponível (não esgotado) a partir do índice inicial
        modelo_encontrado = False
        for idx in range(idx_inicial, len(self.MODELOS_FALLBACK)):
            modelo_candidato = self.MODELOS_FALLBACK[idx]
            if modelo_candidato not in self.modelos_esgotados:
                self.modelo_atual_idx = idx
                self.modelo_atual = modelo_candidato
                modelo_encontrado = True
                break
        
        # Se não encontrou nenhum disponível, usa o primeiro mesmo (vai tentar e falhar)
        if not modelo_encontrado:
            self.modelo_atual_idx = idx_inicial
            self.modelo_atual = self.MODELOS_FALLBACK[idx_inicial]
        
        # Inicializa o LLM com o modelo escolhido
        self.llm = self._criar_llm(self.modelo_atual)
        
        self.historico = []
        self.debug_info = []  # Armazena informações de debug (prompts e respostas do LLM)
    
    def _criar_llm(self, model: str) -> ChatGoogleGenerativeAI:
        """Cria uma instância do LLM com o modelo especificado"""
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self.api_key,
            temperature=0.7
        )
    
    def _trocar_modelo(self) -> bool:
        """
        Tenta trocar para o próximo modelo disponível da lista de fallback.
        Pula modelos que já estão esgotados (cache compartilhado).
        
        Returns:
            True se conseguiu trocar, False se não há mais modelos disponíveis
        """
        # Marca o modelo atual como esgotado no cache compartilhado
        modelo_anterior = self.modelo_atual
        self.modelos_esgotados.add(self.modelo_atual)
        
        # Procura o próximo modelo disponível (não esgotado)
        for idx in range(self.modelo_atual_idx + 1, len(self.MODELOS_FALLBACK)):
            modelo_candidato = self.MODELOS_FALLBACK[idx]
            if modelo_candidato not in self.modelos_esgotados:
                self.modelo_atual_idx = idx
                self.modelo_atual = modelo_candidato
                self.llm = self._criar_llm(self.modelo_atual)
                print(f"[GATEWAY] Modelo trocado de {modelo_anterior} para: {self.modelo_atual} (modelos esgotados: {len(self.modelos_esgotados)})")
                return True
        
        return False
    
    def _is_quota_exceeded_error(self, error: Exception) -> bool:
        """Verifica se o erro é de quota excedida (429 RESOURCE_EXHAUSTED)"""
        error_str = str(error)
        return "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()
    
    def adicionar_mensagem(self, mensagem: str, tipo: str = "human"):
        """Adiciona mensagem ao histórico"""
        if tipo == "human":
            self.historico.append(HumanMessage(content=mensagem))
        else:
            self.historico.append(AIMessage(content=mensagem))
    
    def limpar_historico(self):
        """Limpa o histórico de mensagens"""
        self.historico = []
        self.debug_info = []
        # Não limpa modelos_esgotados - mantém durante toda a sessão
    
    def resetar_debug_info(self):
        """Limpa apenas as informações de debug (mantém histórico e modelos esgotados)"""
        self.debug_info = []
    
    def obter_debug_info(self) -> list:
        """Retorna informações de debug (prompts e respostas do LLM)"""
        return self.debug_info
    
    @abstractmethod
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa uma mensagem do usuário
        
        Args:
            mensagem: Mensagem do usuário
            contexto: Contexto da conversa (dados do cliente, estado, etc)
            
        Returns:
            Dict com resposta e informações de controle
        """
        pass
    
    def gerar_resposta(self, prompt: str, contexto_adicional: str = "", usar_historico: bool = True) -> str:
        """
        Gera resposta usando o LLM com fallback automático de modelos.
        Se o modelo atual atingir o limite de quota, tenta automaticamente o próximo modelo da lista.
        
        Args:
            prompt: Prompt a ser enviado ao LLM
            contexto_adicional: Informação adicional para debug (ex: nome da função que chamou)
            usar_historico: Se True, usa o histórico de mensagens. Se False, envia apenas o prompt atual.
        """
        # Prepara mensagens: usa histórico apenas se solicitado e se não estiver vazio
        if usar_historico and self.historico:
            mensagens = self.historico + [HumanMessage(content=prompt)]
        else:
            # Envia apenas o prompt atual, sem histórico
            mensagens = [HumanMessage(content=prompt)]
        
        tentativas = 0
        max_tentativas = len(self.MODELOS_FALLBACK)
        
        while tentativas < max_tentativas:
            try:
                # Verifica se o modelo atual já está esgotado antes de tentar
                if self.modelo_atual in self.modelos_esgotados:
                    if not self._trocar_modelo():
                        raise Exception("Todos os modelos disponíveis estão esgotados.")
                    continue
                
                resposta = self.llm.invoke(mensagens)
                resposta_content = resposta.content
                
                # Armazena informações de debug
                self.debug_info.append({
                    "contexto": contexto_adicional,
                    "prompt": prompt,
                    "resposta": resposta_content,
                    "modelo_usado": self.modelo_atual,
                    "erro": None
                })
                
                return resposta_content
                
            except Exception as e:
                tentativas += 1
                
                # Verifica se é erro de quota excedida
                if self._is_quota_exceeded_error(e):
                    # Marca modelo como esgotado e tenta trocar imediatamente
                    if self._trocar_modelo():
                        # Tenta novamente com o novo modelo (sem delay)
                        continue
                    else:
                        # Não há mais modelos disponíveis
                        erro_final = f"Todos os modelos atingiram o limite de quota. Modelos esgotados: {', '.join(self.modelos_esgotados)}"
                        self.debug_info.append({
                            "contexto": contexto_adicional,
                            "prompt": prompt,
                            "resposta": None,
                            "modelo_usado": self.modelo_atual,
                            "erro": erro_final
                        })
                        raise Exception(f"Erro ao chamar LLM: {erro_final}")
                else:
                    # Erro não relacionado a quota, não tenta trocar modelo
                    self.debug_info.append({
                        "contexto": contexto_adicional,
                        "prompt": prompt,
                        "resposta": None,
                        "modelo_usado": self.modelo_atual,
                        "erro": str(e)
                    })
                    raise Exception(f"Erro ao chamar LLM: {str(e)}")
        
        # Se chegou aqui, esgotou todas as tentativas
        raise Exception(f"Erro ao chamar LLM: Não foi possível obter resposta após {max_tentativas} tentativas com diferentes modelos.")
    
    def processar_com_comandos(self, prompt: str, contexto_adicional: str = "", usar_historico: bool = False) -> tuple:
        """
        Processa um prompt com suporte a comandos tipo MCP.
        
        Se a IA responder com texto normal, retorna o texto.
        Se a IA responder com um comando (palavra única em maiúsculas), retorna o comando
        para ser processado pelo agente específico.
        
        Args:
            prompt: Prompt a ser enviado ao LLM
            contexto_adicional: Informação adicional para debug
            usar_historico: Se True, usa histórico de mensagens. Se False (padrão), envia apenas o prompt atual.
                           Use False para prompts específicos (ex: extrair CPF, identificar moeda).
                           Use True para conversas normais que precisam de contexto.
        
        Returns:
            tuple: (resposta_texto: Optional[str], comando: Optional[str], dados_comando: Optional[Dict])
                   - resposta_texto: Resposta em texto da IA (se não for comando)
                   - comando: Nome do comando em maiúsculas (se for comando)
                   - dados_comando: Dados adicionais do comando (se houver, formato COMANDO:dados)
        """
        resposta_llm = self.gerar_resposta(prompt, contexto_adicional=contexto_adicional, usar_historico=usar_historico)
        resposta_stripped = resposta_llm.strip()
        
        # Remove espaços extras e normaliza
        resposta_normalizada = " ".join(resposta_stripped.split())
        
        # Verifica se é um comando com dados (formato: COMANDO:dados ou COMANDO: dados)
        # Verifica ANTES do comando simples para pegar comandos com dados
        if ":" in resposta_normalizada:
            partes = resposta_normalizada.split(":", 1)
            comando = partes[0].strip().upper()
            dados = partes[1].strip() if len(partes) > 1 else ""
            # Verifica se o comando é apenas letras e números (permite números após letras, ex: SOLICITAR_AUMENTO)
            if comando.replace("_", "").isalnum() and len(comando.split()) == 1:
                return (None, comando, {"dados": dados})
        
        # Verifica se é um comando simples (palavra única em maiúsculas, apenas letras e underscore)
        # Remove underscores para verificar se é alfanumérico
        comando_candidato = resposta_normalizada.upper()
        if comando_candidato.replace("_", "").isalnum() and len(comando_candidato.split()) == 1:
            return (None, comando_candidato, None)
        
        # Se não é comando, retorna a resposta normalmente
        return (resposta_llm, None, None)

