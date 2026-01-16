"""
Agente de Câmbio - Consulta de cotação de moedas
Refatorado com Tool Calling nativo
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from agents.tools import get_tools_cambio


class CambioAgent(BaseAgent):
    """Agente responsável por consultar cotações de moedas"""
    
    # Prompt de sistema que explica o contexto e responsabilidades
    SYSTEM_PROMPT = """Você é um assistente de câmbio de um banco digital.

SUAS FERRAMENTAS (USE IMEDIATAMENTE - não prometa, EXECUTE):
1. consultar_cotacao_moeda(moeda) - Consulta cotação de uma moeda
2. redirecionar_para_credito() - Quando cliente quer falar sobre limite/crédito
3. redirecionar_para_entrevista() - Quando cliente quer fazer entrevista

MOEDAS DISPONÍVEIS:
USD (Dólar), EUR (Euro), GBP (Libra), JPY (Iene), CHF (Franco Suíço), 
CAD (Dólar Canadense), AUD (Dólar Australiano), CNY (Yuan), ARS (Peso Argentino)

REGRAS OBRIGATÓRIAS:
1. Execute tools IMEDIATAMENTE - NUNCA diga "vou consultar" ou "um momento"
2. LEIA O HISTÓRICO para informações já mencionadas
3. País mencionado → use a moeda correspondente (Japão=JPY, EUA=USD)
4. Cliente diz "já falei" → procure no histórico

INSTRUÇÕES:
- Cotação solicitada → use consultar_cotacao_moeda e responda com resultado
- Cliente quer limite/crédito → use redirecionar_para_credito
- "dólar" sem especificar → assume USD

PROIBIDO:
- NUNCA mencione "transferir", "outro agente", "outra área"
- A transição deve ser INVISÍVEL - continue a conversa naturalmente

Seja natural e prestativo. Responda em português do Brasil."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        
        # Registra as tools disponíveis para este agente
        self.registrar_tools(get_tools_cambio())
    
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Processa mensagem relacionada a câmbio"""
        
        # Verifica encerramento
        if self._verificar_encerramento(mensagem):
            return {
                "resposta": "Foi um prazer ajudá-lo! Até logo!",
                "proximo_agente": None,
                "encerrar": True
            }
        
        try:
            # Processa usando Tool Calling
            resposta_texto, tool_calls = self.processar_com_tools(
                prompt_sistema=self.SYSTEM_PROMPT,
                mensagem_usuario=mensagem,
                contexto_debug="CambioAgent.processar",
                usar_memoria=True
            )
            
            # Verifica se houve redirecionamento
            for tc in tool_calls:
                if tc["name"] == "redirecionar_para_credito":
                    return {
                        "resposta": "",
                        "proximo_agente": "credito",
                        "encerrar": False
                    }
                elif tc["name"] == "redirecionar_para_entrevista":
                    return {
                        "resposta": "",
                        "proximo_agente": "entrevista",
                        "encerrar": False
                    }
            
            # Usa a resposta do LLM diretamente
            resposta_final = resposta_texto if resposta_texto else "Qual moeda você gostaria de consultar?"
            
            # Salva na memória
            self.adicionar_a_memoria(mensagem, resposta_final)
            
            return {
                "resposta": resposta_final,
                "proximo_agente": None,
                "encerrar": False
            }
            
        except Exception as e:
            erro = f"Erro ao processar: {str(e)}"
            print(f"[CambioAgent] {erro}")
            return {
                "resposta": f"Desculpe, ocorreu um erro ao consultar a cotação. Por favor, tente novamente.",
                "proximo_agente": None,
                "encerrar": False,
                "erro": erro
            }
    
    def _verificar_encerramento(self, mensagem: str) -> bool:
        """Verifica se o usuário quer encerrar"""
        mensagem_lower = mensagem.lower().strip()
        
        frases_encerramento = [
            "encerrar", "sair", "tchau", "até logo", "fim", "terminar", "finalizar"
        ]
        
        if mensagem_lower in ["não", "nao", "n"]:
            return False
        
        for frase in frases_encerramento:
            if frase in mensagem_lower and len(mensagem_lower.split()) <= 3:
                return True
        
        return False
