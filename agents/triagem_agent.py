"""
Agente de Triagem - Porta de entrada do sistema
Refatorado com Tool Calling nativo
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from agents.tools import get_tools_triagem
from utils.csv_handler import autenticar_cliente


class TriagemAgent(BaseAgent):
    """Agente responsável por autenticar clientes e direcionar para outros agentes"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.estado = {
            "etapa": "saudacao",  # saudacao, coletando_cpf, coletando_nascimento, autenticado, falha
            "tentativas_falha": 0,
            "cpf": None,
            "data_nascimento": None,
            "cliente": None
        }
        
        # Registra as tools disponíveis para este agente
        self.registrar_tools(get_tools_triagem())
    
    def _get_system_prompt(self) -> str:
        """Gera o prompt de sistema baseado na etapa atual"""
        etapa = self.estado["etapa"]
        
        base_prompt = """Você é o Agente de Triagem de um banco digital.

SUAS RESPONSABILIDADES:
- Receber e autenticar clientes
- Identificar a necessidade do cliente após autenticação
- Direcionar para o agente especializado correto

FERRAMENTAS DISPONÍVEIS:
- validar_cpf(cpf) - Valida CPF
- validar_data_nascimento(data) - Valida data de nascimento
- autenticar_cliente_tool(cpf, data_nascimento) - Autentica o cliente
- redirecionar_para_credito() - Para questões de crédito/limite
- redirecionar_para_cambio() - Para cotação de moedas
- redirecionar_para_entrevista() - Para entrevista de crédito
- encerrar_conversa(mensagem_despedida) - Encerra a conversa quando o cliente quiser sair

"""
        
        if etapa == "saudacao" or etapa == "coletando_cpf":
            prompt = base_prompt + """ETAPA ATUAL: COLETA DE CPF

INSTRUÇÕES:
1. Dê as boas-vindas ao cliente de forma amigável
2. Peça o CPF para autenticação
3. Quando o cliente informar o CPF, use validar_cpf para extraí-lo
4. Se o CPF for válido (11 dígitos), informe e peça a data de nascimento
5. Se inválido, peça novamente de forma educada

IMPORTANTE: Se o cliente informar CPF E data de nascimento juntos na mesma mensagem:
1. Use validar_cpf para extrair o CPF
2. Use validar_data_nascimento para extrair a data
3. Use autenticar_cliente_tool com ambos os dados para autenticar diretamente
4. Se autenticado, cumprimente pelo nome e pergunte como pode ajudar

NUNCA responda apenas com números ou dados concatenados. Sempre responda com frases completas e amigáveis.

Seja natural e acolhedor. Responda em português do Brasil."""

        elif etapa == "coletando_nascimento":
            cpf_formatado = self.estado.get("cpf", "")
            if cpf_formatado and len(cpf_formatado) == 11:
                cpf_formatado = f"{cpf_formatado[:3]}.{cpf_formatado[3:6]}.{cpf_formatado[6:9]}-{cpf_formatado[9:]}"
            
            prompt = base_prompt + f"""ETAPA ATUAL: COLETA DE DATA DE NASCIMENTO

CPF JÁ INFORMADO: {cpf_formatado}

INSTRUÇÕES:
1. Quando o cliente informar a data de nascimento, use validar_data_nascimento para extrair e normalizar a data
2. Aceite formatos: DD/MM/AAAA ou AAAA-MM-DD
3. Se válida, use autenticar_cliente_tool(cpf="{self.estado.get('cpf', '')}", data_nascimento=DATA_EXTRAIDA) para autenticar
4. Se autenticação bem sucedida, cumprimente pelo nome e pergunte como pode ajudar
5. Se falhar, informe e peça para tentar novamente

IMPORTANTE: Você DEVE chamar autenticar_cliente_tool após validar a data. Não apenas responda que vai validar - execute a autenticação!

Tentativas restantes: {3 - self.estado['tentativas_falha']}

Responda em português do Brasil."""

        else:  # autenticado
            nome = self.estado.get("cliente", {}).get("nome", "cliente")
            
            prompt = base_prompt + f"""ETAPA ATUAL: CLIENTE AUTENTICADO

CLIENTE AUTENTICADO: {nome}

INSTRUÇÕES:
1. O cliente já está autenticado
2. Identifique a necessidade do cliente:
   - Se mencionar limite, crédito, cartão → use redirecionar_para_credito()
   - Se mencionar cotação, dólar, euro, moeda → use redirecionar_para_cambio()
   - Se mencionar entrevista, score → use redirecionar_para_entrevista()
3. Se não entender claramente, pergunte como pode ajudar

PROIBIDO:
- NUNCA mencione "transferir", "outro agente", "redirecionar", "outra área"
- A transição deve ser INVISÍVEL para o cliente
- Apenas continue a conversa naturalmente após usar a tool

Seja natural e prestativo. Responda em português do Brasil."""

        return prompt
    
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Processa mensagem do usuário no fluxo de triagem"""
        
        # Encerramento agora é controlado pelo LLM via tool encerrar_conversa
        
        try:
            # Verifica se Chain-of-Thought está ativado
            cot_enabled = contexto.get("config", {}).get("chain_of_thought", False)
            
            # Processa usando Tool Calling
            resposta_texto, tool_calls, encerrar_flag, mensagem_despedida = self.processar_com_tools(
                prompt_sistema=self._get_system_prompt(),
                mensagem_usuario=mensagem,
                contexto_debug=f"TriagemAgent.processar - etapa: {self.estado['etapa']}",
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
            
            # Processa resultados das tools
            proximo_agente = None
            
            for tc in tool_calls:
                result = tc["result"]
                
                # Tools de redirecionamento
                if tc["name"] == "redirecionar_para_credito":
                    proximo_agente = "credito"
                elif tc["name"] == "redirecionar_para_cambio":
                    proximo_agente = "cambio"
                elif tc["name"] == "redirecionar_para_entrevista":
                    proximo_agente = "entrevista"
                
                # Validação de CPF
                elif tc["name"] == "validar_cpf" and isinstance(result, dict):
                    if result.get("sucesso"):
                        self.estado["cpf"] = result.get("cpf")
                        self.estado["etapa"] = "coletando_nascimento"
                
                # Validação de data
                elif tc["name"] == "validar_data_nascimento" and isinstance(result, dict):
                    if result.get("sucesso"):
                        self.estado["data_nascimento"] = result.get("data")
                
                # Autenticação
                elif tc["name"] == "autenticar_cliente_tool" and isinstance(result, dict):
                    if result.get("autenticado"):
                        self.estado["cliente"] = result.get("cliente")
                        self.estado["etapa"] = "autenticado"
                        self.estado["tentativas_falha"] = 0
                    else:
                        self.estado["tentativas_falha"] += 1
                        if self.estado["tentativas_falha"] >= 3:
                            self.estado["etapa"] = "falha"
                            return {
                                "resposta": "Lamento, mas não foi possível autenticar após várias tentativas. Por favor, entre em contato com nosso suporte.",
                                "proximo_agente": None,
                                "autenticado": False,
                                "cliente": None,
                                "encerrar": True
                            }
                        else:
                            # Reseta CPF e data para nova tentativa
                            self.estado["cpf"] = None
                            self.estado["data_nascimento"] = None
                            self.estado["etapa"] = "coletando_cpf"
            
            # Monta resposta final - usa a resposta do LLM diretamente
            if resposta_texto and resposta_texto.strip():
                resposta_final = resposta_texto
            else:
                # Log para debug - resposta vazia do LLM
                print(f"[TriagemAgent] Resposta vazia do LLM na etapa '{self.estado['etapa']}', gerando resposta apropriada...")
                
                # Gera resposta baseada no estado atual (sem chamar LLM novamente)
                if self.estado["etapa"] == "autenticado":
                    cliente = self.estado.get("cliente", {})
                    nome = cliente.get("nome", "")
                    resposta_final = f"Autenticação realizada com sucesso! Olá, {nome}! Como posso ajudá-lo hoje? Posso ajudar com consultas de crédito, cotações de moedas ou entrevista de crédito."
                elif self.estado["etapa"] == "coletando_nascimento":
                    resposta_final = "Agora, por favor, me informe sua data de nascimento para completar a autenticação."
                elif self.estado["etapa"] == "coletando_cpf":
                    resposta_final = "Por favor, me informe seu CPF para que eu possa autenticá-lo."
                else:
                    resposta_final = "Olá! Bem-vindo ao Banco Ágil. Como posso ajudá-lo? Para começar, informe seu CPF."
            
            # Avança etapa se necessário (primeira interação)
            if self.estado["etapa"] == "saudacao":
                self.estado["etapa"] = "coletando_cpf"
            
            # Salva na memória
            self.adicionar_a_memoria(mensagem, resposta_final)
            
            # Se houve redirecionamento, usa a resposta montada (não vazia!)
            if proximo_agente:
                return {
                    "resposta": resposta_final,
                    "proximo_agente": proximo_agente,
                    "autenticado": self.estado["etapa"] == "autenticado",
                    "cliente": self.estado.get("cliente"),
                    "encerrar": False
                }
            
            return {
                "resposta": resposta_final,
                "proximo_agente": None,
                "autenticado": self.estado["etapa"] == "autenticado",
                "cliente": self.estado.get("cliente"),
                "encerrar": False
            }
            
        except Exception as e:
            erro = f"Erro ao processar: {str(e)}"
            print(f"[TriagemAgent] {erro}")
            return {
                "resposta": f"Desculpe, ocorreu um erro. {self._get_resposta_padrao()}",
                "proximo_agente": None,
                "autenticado": False,
                "cliente": None,
                "encerrar": False,
                "erro": erro
            }
    
    def _get_resposta_padrao(self) -> str:
        """Retorna resposta padrão baseada na etapa"""
        etapa = self.estado["etapa"]
        
        respostas = {
            "saudacao": "Olá! Bem-vindo ao Banco Ágil. Para começar, por favor informe seu CPF.",
            "coletando_cpf": "Por favor, informe seu CPF (apenas números).",
            "coletando_nascimento": "Agora preciso da sua data de nascimento (DD/MM/AAAA).",
            "autenticado": f"Como posso ajudá-lo, {self.estado.get('cliente', {}).get('nome', 'cliente')}?",
            "falha": "Não foi possível autenticar. Entre em contato com o suporte."
        }
        
        return respostas.get(etapa, "Como posso ajudá-lo?")
    
    def _verificar_encerramento(self, mensagem: str) -> bool:
        """Verifica se o usuário quer encerrar"""
        mensagem_lower = mensagem.lower().strip()
        
        frases_encerramento = [
            "encerrar", "sair", "tchau", "até logo", "fim", "terminar"
        ]
        
        if mensagem_lower in ["não", "nao", "n"]:
            return False
        
        for frase in frases_encerramento:
            if frase in mensagem_lower and len(mensagem_lower.split()) <= 3:
                return True
        
        return False
    
    def resetar(self, limpar_memoria_compartilhada: bool = False):
        """Reseta o estado do agente (preserva memória por padrão)"""
        self.estado = {
            "etapa": "saudacao",
            "tentativas_falha": 0,
            "cpf": None,
            "data_nascimento": None,
            "cliente": None
        }
        # Só limpa memória se explicitamente solicitado
        # (orquestrador já limpa a memória compartilhada diretamente)
        if limpar_memoria_compartilhada:
            self.limpar_memoria()
