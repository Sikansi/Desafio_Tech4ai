"""
Agente de Crédito - Consulta e solicitação de aumento de limite
Refatorado com Tool Calling nativo
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from agents.tools import get_tools_credito
from utils.csv_handler import obter_cliente_por_cpf


class CreditoAgent(BaseAgent):
    """Agente responsável por consultas de crédito e solicitações de aumento"""
    
    # Prompt de sistema que explica o contexto e responsabilidades
    SYSTEM_PROMPT = """Você é o Agente de Crédito de um banco digital. Você é responsável por:
- Consultar limite de crédito do cliente
- Processar solicitações de aumento de limite
- Redirecionar para outros agentes quando necessário

CONTEXTO DO SISTEMA BANCÁRIO:
O sistema possui múltiplos agentes especializados:
- Você (Agente de Crédito): Limite e aumento de crédito
- Agente de Câmbio: Cotações de moedas (dólar, euro, etc.)
- Agente de Entrevista: Entrevista para atualizar score de crédito

SUAS FERRAMENTAS DISPONÍVEIS:
1. consultar_limite_credito(cpf) - Consulta o limite atual do cliente
2. solicitar_aumento_limite(cpf, novo_limite) - Processa solicitação de aumento
3. redirecionar_para_cambio() - Quando cliente quer cotação de moedas
4. redirecionar_para_entrevista() - Quando cliente quer fazer entrevista

INSTRUÇÕES:
1. Se o cliente pergunta sobre seu limite → use consultar_limite_credito
2. Se o cliente quer aumentar o limite → extraia o valor e use solicitar_aumento_limite
3. Se o cliente pergunta sobre moedas/cotação → use redirecionar_para_cambio
4. Se o cliente quer fazer entrevista/melhorar score → use redirecionar_para_entrevista
5. Se não entendeu claramente → pergunte educadamente

DADOS DO CLIENTE ATUAL:
{dados_cliente}

Seja natural, amigável e profissional. Responda em português do Brasil."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.cliente = None
        self.entrevista_oferecida = False
        
        # Registra as tools disponíveis para este agente
        self.registrar_tools(get_tools_credito())
    
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Processa mensagem relacionada a crédito"""
        
        # Obtém dados do cliente do contexto
        if not self.cliente and contexto.get("cliente"):
            self.cliente = contexto["cliente"]
        elif not self.cliente and contexto.get("cpf"):
            self.cliente = obter_cliente_por_cpf(contexto["cpf"])
        
        if not self.cliente:
            return {
                "resposta": "Desculpe, não foi possível identificar seus dados. Por favor, faça login novamente.",
                "proximo_agente": "triagem",
                "encerrar": False
            }
        
        # Verifica encerramento
        if self._verificar_encerramento(mensagem):
            return {
                "resposta": "Foi um prazer ajudá-lo! Até logo!",
                "proximo_agente": None,
                "encerrar": True
            }
        
        # Monta dados do cliente para o prompt
        limite_atual = float(self.cliente.get('limite_credito', 0))
        cpf = str(self.cliente.get('cpf', ''))
        nome = self.cliente.get('nome', 'Cliente')
        
        dados_cliente = f"""- Nome: {nome}
- CPF: {cpf}
- Limite atual: R$ {limite_atual:,.2f}"""
        
        prompt_sistema = self.SYSTEM_PROMPT.format(dados_cliente=dados_cliente)
        
        try:
            # Processa usando Tool Calling
            resposta_texto, tool_calls = self.processar_com_tools(
                prompt_sistema=prompt_sistema,
                mensagem_usuario=mensagem,
                contexto_debug="CreditoAgent.processar",
                usar_memoria=True
            )
            
            # Verifica se houve redirecionamento
            for tc in tool_calls:
                if tc["name"] == "redirecionar_para_cambio":
                    return {
                        "resposta": "",
                        "proximo_agente": "cambio",
                        "encerrar": False
                    }
                elif tc["name"] == "redirecionar_para_entrevista":
                    return {
                        "resposta": "",
                        "proximo_agente": "entrevista",
                        "encerrar": False
                    }
                elif tc["name"] == "solicitar_aumento_limite":
                    result = tc["result"]
                    if isinstance(result, dict) and result.get("sugerir_entrevista"):
                        self.entrevista_oferecida = True
            
            # Usa a resposta do LLM diretamente
            resposta_final = resposta_texto if resposta_texto else "Como posso ajudá-lo com questões de crédito?"
            
            # Salva na memória
            self.adicionar_a_memoria(mensagem, resposta_final)
            
            return {
                "resposta": resposta_final,
                "proximo_agente": None,
                "encerrar": False
            }
            
        except Exception as e:
            erro = f"Erro ao processar: {str(e)}"
            print(f"[CreditoAgent] {erro}")
            return {
                "resposta": f"Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente.",
                "proximo_agente": None,
                "encerrar": False,
                "erro": erro
            }
    
    def _verificar_encerramento(self, mensagem: str) -> bool:
        """Verifica se o usuário quer encerrar"""
        mensagem_lower = mensagem.lower().strip()
        
        frases_encerramento = [
            "encerrar", "sair", "tchau", "até logo", "fim", "terminar", "finalizar",
            "encerrar conversa", "tchau tchau", "até mais"
        ]
        
        if mensagem_lower in ["não", "nao", "n"]:
            return False
        
        for frase in frases_encerramento:
            if frase in mensagem_lower and len(mensagem_lower.split()) <= 3:
                return True
        
        return False
    
    def definir_cliente(self, cliente: Dict[str, Any]):
        """Define o cliente atual"""
        self.cliente = cliente
        self.entrevista_oferecida = False
