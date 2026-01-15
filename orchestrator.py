"""
Orquestrador principal - Gerencia o fluxo entre agentes
"""
from typing import Dict, Any, Optional
from agents.triagem_agent import TriagemAgent
from agents.credito_agent import CreditoAgent
from agents.entrevista_agent import EntrevistaAgent
from agents.cambio_agent import CambioAgent


class Orchestrator:
    """Gerencia o fluxo de conversação entre os diferentes agentes"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o orquestrador e todos os agentes
        
        Args:
            api_key: Chave da API do Google Gemini
        """
        self.api_key = api_key
        self.agente_atual = None
        self.agente_triagem = TriagemAgent(api_key)
        self.agente_credito = CreditoAgent(api_key)
        self.agente_entrevista = EntrevistaAgent(api_key)
        self.agente_cambio = CambioAgent(api_key)
        
        # Estado da conversa
        self.contexto = {
            "cliente": None,
            "cpf": None,
            "autenticado": False,
            "historico": []
        }
        
        # Inicia com agente de triagem
        self.agente_atual = self.agente_triagem
    
    def processar_mensagem(self, mensagem: str) -> Dict[str, Any]:
        """
        Processa mensagem do usuário e retorna resposta
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            Dict com:
                - resposta: str - Resposta do agente
                - encerrar: bool - Se deve encerrar a conversa
                - agente_atual: str - Nome do agente atual
                - debug_info: list - Informações de debug (prompts e respostas do LLM)
                - erro: str - Mensagem de erro se houver
        """
        debug_info = []
        erro = None
        
        try:
            # Limpa debug_info do agente antes de processar (evita acumulação de chamadas antigas)
            if hasattr(self.agente_atual, 'resetar_debug_info'):
                self.agente_atual.resetar_debug_info()
            
            # Processa mensagem no agente atual
            resultado = self.agente_atual.processar(mensagem, self.contexto)
            
            # Coleta informações de debug do agente ANTES de qualquer processamento adicional
            if hasattr(self.agente_atual, 'obter_debug_info'):
                debug_info_temp = self.agente_atual.obter_debug_info()
                if debug_info_temp:
                    debug_info.extend(debug_info_temp)
            
            # Atualiza contexto
            if resultado.get("cliente"):
                self.contexto["cliente"] = resultado["cliente"]
                self.contexto["cpf"] = resultado["cliente"].get("cpf")
                self.contexto["autenticado"] = True
            
            # Verifica se precisa trocar de agente
            proximo_agente_nome = resultado.get("proximo_agente")
            
            if proximo_agente_nome:
                self._trocar_agente(proximo_agente_nome, resultado.get("cliente"))
                # Reprocessa a mensagem com o novo agente para que ele possa responder adequadamente
                # Apenas reprocessa se a resposta anterior estava vazia (indicando redirecionamento)
                if not resultado.get("resposta") or resultado.get("resposta").strip() == "":
                    # Limpa debug_info do novo agente antes de processar
                    if hasattr(self.agente_atual, 'resetar_debug_info'):
                        self.agente_atual.resetar_debug_info()
                    
                    resultado = self.agente_atual.processar(mensagem, self.contexto)
                    # Coleta informações de debug do novo agente também
                    if hasattr(self.agente_atual, 'obter_debug_info'):
                        debug_info_temp = self.agente_atual.obter_debug_info()
                        if debug_info_temp:
                            debug_info.extend(debug_info_temp)
            
            # Adiciona ao histórico
            self.contexto["historico"].append({
                "usuario": mensagem,
                "agente": resultado.get("resposta", ""),
                "agente_atual": self._obter_nome_agente_atual()
            })
            
            return {
                "resposta": resultado.get("resposta", "Desculpe, ocorreu um erro."),
                "encerrar": resultado.get("encerrar", False),
                "agente_atual": self._obter_nome_agente_atual(),
                "debug_info": debug_info,
                "erro": None,
                "score_calculado": resultado.get("score_calculado"),
                "limite_maximo": resultado.get("limite_maximo")
            }
        
        except Exception as e:
            erro = str(e)
            # Coleta informações de debug mesmo em caso de erro
            if hasattr(self.agente_atual, 'obter_debug_info'):
                debug_info_temp = self.agente_atual.obter_debug_info()
                if debug_info_temp:
                    debug_info.extend(debug_info_temp)
            
            return {
                "resposta": f"❌ Erro na interpretação da IA: {erro}",
                "encerrar": False,
                "agente_atual": self._obter_nome_agente_atual(),
                "debug_info": debug_info if debug_info else [],
                "erro": erro
            }
    
    def _trocar_agente(self, nome_agente: str, cliente: Optional[Dict[str, Any]] = None):
        """
        Troca o agente atual
        
        Args:
            nome_agente: Nome do próximo agente
            cliente: Dados do cliente (se disponível)
        """
        mapeamento = {
            "triagem": self.agente_triagem,
            "credito": self.agente_credito,
            "entrevista": self.agente_entrevista,
            "cambio": self.agente_cambio
        }
        
        novo_agente = mapeamento.get(nome_agente)
        
        if novo_agente:
            # Transfere contexto do cliente para o novo agente
            if cliente and hasattr(novo_agente, "definir_cliente"):
                novo_agente.definir_cliente(cliente)
            elif cliente and hasattr(novo_agente, "cliente"):
                novo_agente.cliente = cliente
            
            self.agente_atual = novo_agente
    
    def _obter_nome_agente_atual(self) -> str:
        """Retorna o nome do agente atual"""
        if self.agente_atual == self.agente_triagem:
            return "Triagem"
        elif self.agente_atual == self.agente_credito:
            return "Crédito"
        elif self.agente_atual == self.agente_entrevista:
            return "Entrevista de Crédito"
        elif self.agente_atual == self.agente_cambio:
            return "Câmbio"
        else:
            return "Sistema"
    
    def resetar(self):
        """Reseta o orquestrador para nova conversa"""
        # Limpa memória compartilhada
        from agents.base_agent import BaseAgent
        if BaseAgent._memoria_compartilhada:
            BaseAgent._memoria_compartilhada.clear()
        
        # Reseta agentes
        self.agente_triagem.resetar()
        self.agente_entrevista.resetar()
        self.agente_atual = self.agente_triagem
        self.contexto = {
            "cliente": None,
            "cpf": None,
            "autenticado": False,
            "historico": []
        }
        self.agente_credito.cliente = None
        self.agente_credito.entrevista_oferecida = False
        self.agente_cambio.debug_info = []

