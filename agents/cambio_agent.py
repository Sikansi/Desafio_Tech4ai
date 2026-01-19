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

FERRAMENTAS DISPONÍVEIS:
- consultar_cotacao_moeda(moeda) - Consulta cotação de uma moeda
- redirecionar_para_credito() - Para questões de limite/crédito
- redirecionar_para_entrevista() - Para entrevista de crédito
- encerrar_conversa(mensagem_despedida) - Encerra a conversa quando o cliente quiser sair

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

IMPORTANTE - NÃO INVENTAR FUNCIONALIDADES:
- Você só pode fazer o que as FERRAMENTAS DISPONÍVEIS permitem
- O sistema só oferece: consulta de cotação de moedas
- NÃO existe compra/venda de moeda, transferência internacional, etc.
- Se o cliente pedir algo que não existe, diga que não está disponível

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
        
        # Encerramento agora é controlado pelo LLM via tool encerrar_conversa
        
        try:
            # Verifica se Chain-of-Thought está ativado
            cot_enabled = contexto.get("config", {}).get("chain_of_thought", False)
            
            # Processa usando Tool Calling
            resposta_texto, tool_calls, encerrar_flag, mensagem_despedida = self.processar_com_tools(
                prompt_sistema=self.SYSTEM_PROMPT,
                mensagem_usuario=mensagem,
                contexto_debug="CambioAgent.processar",
                usar_memoria=True,
                chain_of_thought=cot_enabled
            )
            
            # Se a tool encerrar_conversa foi chamada, retorna imediatamente
            if encerrar_flag:
                self.adicionar_a_memoria(mensagem, mensagem_despedida or resposta_texto)
                return {
                    "resposta": mensagem_despedida or resposta_texto or "Foi um prazer ajudá-lo! Até logo!",
                    "proximo_agente": None,
                    "encerrar": True
                }
            
            # Processa tool calls - primeiro coleta tudo
            proximo_agente = None
            ultima_mensagem_tool = None
            
            for tc in tool_calls:
                print(f"[CambioAgent] Tool executada: {tc['name']} -> {tc['result']}")
                
                if tc["name"] == "redirecionar_para_credito":
                    proximo_agente = "credito"
                elif tc["name"] == "redirecionar_para_entrevista":
                    proximo_agente = "entrevista"
                elif tc["name"] == "consultar_cotacao_moeda":
                    result = tc["result"]
                    if isinstance(result, dict) and result.get("sucesso"):
                        ultima_mensagem_tool = result.get("mensagem", "")
            
            # Monta resposta final
            if resposta_texto:
                resposta_final = resposta_texto
            elif ultima_mensagem_tool:
                resposta_final = ultima_mensagem_tool
            elif tool_calls:
                resposta_final = "Cotação consultada!"
            else:
                resposta_final = "Qual moeda você gostaria de consultar?"
            
            # Se houve redirecionamento, usa a resposta (não vazia!)
            if proximo_agente:
                self.adicionar_a_memoria(mensagem, resposta_final)
                return {
                    "resposta": resposta_final,
                    "proximo_agente": proximo_agente,
                    "encerrar": False
                }
            
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
