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
    SYSTEM_PROMPT = """Você é um assistente de crédito de um banco digital.

DADOS DO CLIENTE (JÁ AUTENTICADO - NÃO PEÇA CPF NOVAMENTE!):
{dados_cliente}

SUAS FERRAMENTAS:
1. consultar_limite_credito(cpf) - Consulta o limite atual
2. solicitar_aumento_limite(cpf, novo_limite) - Processa solicitação de aumento
3. redirecionar_para_cambio() - Quando cliente pergunta sobre moedas
4. redirecionar_para_entrevista() - Inicia entrevista de crédito

REGRAS OBRIGATÓRIAS:
1. NUNCA peça CPF ou dados de identificação - o cliente JÁ está autenticado
2. Execute tools imediatamente - NUNCA diga "vou consultar" ou "um momento"
3. A entrevista é IMEDIATA, não "agendada" - diga "podemos fazer agora"
4. Quando cliente ACEITAR entrevista → use a tool SEM dizer que está transferindo

FLUXO PARA AUMENTO DE LIMITE:
1. Cliente menciona que quer algo caro → consulte o limite atual
2. Se limite insuficiente → pergunte se quer solicitar aumento
3. Cliente CONFIRMA (sim, s, ok, quero, pode) → use solicitar_aumento_limite COM O VALOR mencionado
4. Se REJEITADO → ofereça entrevista: "Podemos fazer uma análise rápida agora para aumentar seu limite"
5. Cliente ACEITA entrevista → use redirecionar_para_entrevista IMEDIATAMENTE

CONFIRMAÇÕES CURTAS:
- "S", "sim", "ok", "quero", "pode", "claro" = CONFIRMAÇÃO → execute a ação
- Use o VALOR mencionado anteriormente no histórico

PROIBIDO:
- NUNCA mencione "transferir", "outro agente", "outra área"
- A transição deve ser INVISÍVEL - apenas continue a conversa naturalmente
- NUNCA peça dados que já tem (CPF, nome, etc.)

LEMBRE-SE:
- Use o CPF dos DADOS DO CLIENTE nas tools
- LEIA O HISTÓRICO para valores mencionados antes
- Se cliente disser "já falei" → procure no histórico

Seja natural e profissional. Responda em português do Brasil."""

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
            
            # Processa resultados das tool calls
            ultima_mensagem_tool = None
            
            for tc in tool_calls:
                print(f"[CreditoAgent] Tool executada: {tc['name']} -> {tc['result']}")
                
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
                    if isinstance(result, dict):
                        if result.get("sugerir_entrevista"):
                            self.entrevista_oferecida = True
                            ultima_mensagem_tool = result.get("mensagem", "")
                        elif result.get("aprovado"):
                            ultima_mensagem_tool = result.get("mensagem", "Aumento aprovado!")
                        else:
                            ultima_mensagem_tool = result.get("mensagem", "")
                elif tc["name"] == "consultar_limite_credito":
                    result = tc["result"]
                    if isinstance(result, dict) and result.get("sucesso"):
                        limite = result.get("limite_formatado", "")
                        ultima_mensagem_tool = f"Seu limite atual é de {limite}."
            
            # Usa resposta do LLM, ou fallback baseado na tool
            if resposta_texto:
                resposta_final = resposta_texto
            elif ultima_mensagem_tool:
                resposta_final = ultima_mensagem_tool
            elif tool_calls:
                # Teve tool call mas sem resposta - força uma nova chamada
                resposta_final = "Processado! Como posso ajudar mais?"
            else:
                resposta_final = "Como posso ajudá-lo com questões de crédito?"
            
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
