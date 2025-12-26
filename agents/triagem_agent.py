"""
Agente de Triagem - Porta de entrada do sistema
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from utils.csv_handler import autenticar_cliente
from utils.saudacoes import detectar_saudacao, gerar_resposta_saudacao, extrair_mensagem_sem_saudacao


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
    
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mensagem do usuário no fluxo de triagem
        
        Returns:
            Dict com:
                - resposta: str - Resposta do agente
                - proximo_agente: str - Próximo agente a ser chamado (ou None)
                - autenticado: bool - Se o cliente foi autenticado
                - cliente: dict - Dados do cliente (se autenticado)
                - encerrar: bool - Se deve encerrar a conversa
        """
        # Detecta saudações e responde adequadamente
        saudacao_detectada = detectar_saudacao(mensagem)
        
        self.adicionar_mensagem(mensagem, "human")
        
        # Verifica se usuário quer encerrar
        if self._verificar_encerramento(mensagem):
            return {
                "resposta": "Entendido! Foi um prazer atendê-lo. Até logo!",
                "proximo_agente": None,
                "autenticado": False,
                "cliente": None,
                "encerrar": True
            }
        
        # Fluxo de autenticação
        if self.estado["etapa"] == "saudacao":
            # Se detectou saudação, responde adequadamente
            if saudacao_detectada:
                resposta_saudacao = gerar_resposta_saudacao(saudacao_detectada)
                resposta = f"{resposta_saudacao} Bem-vindo ao Banco Ágil. Sou seu assistente virtual e estou aqui para ajudá-lo. Para começarmos, preciso fazer sua autenticação. Por favor, informe seu CPF (apenas os números)."
            else:
                resposta = self._iniciar_saudacao()
            self.estado["etapa"] = "coletando_cpf"
            
        elif self.estado["etapa"] == "coletando_cpf":
            # Usa sistema de comandos para processar CPF
            try:
                prompt = f"""Você é um agente bancário coletando o CPF do cliente para autenticação.

Mensagem do cliente: "{mensagem}"

SISTEMA DE COMANDOS:
Você pode responder de duas formas:

1. TEXTO NORMAL: Se você responder com texto normal, esse texto será passado diretamente para o cliente.
   Use isso quando o cliente está questionando, recusando ou precisa de esclarecimento.

2. COMANDO: Se você identificar um CPF (11 dígitos), responda APENAS no formato: "CPF:12345678900"
   (sem espaços após os dois pontos)

INSTRUÇÕES:
- Se a mensagem contém um CPF (11 dígitos) → extraia e responda "CPF:12345678900"
- Se o cliente está questionando ou recusando → responda com texto explicando por que a autenticação é necessária
- Se não conseguiu identificar CPF → responda com texto pedindo educadamente que informe o CPF

IMPORTANTE: 
- CPF tem sempre 11 dígitos
- Extraia apenas números, removendo pontos, traços e espaços
- Seja natural e conversacional quando responder com texto"""

                resposta_final, comando, dados_comando = self.processar_com_comandos(
                    prompt, 
                    contexto_adicional="TriagemAgent.processar - Coletando CPF",
                    usar_historico=False  # Não usa histórico para extrair CPF - prompt específico
                )
                
                # Se retornou comando CPF
                if comando == "CPF" and dados_comando and "dados" in dados_comando:
                    cpf = dados_comando["dados"].replace(" ", "").replace(".", "").replace("-", "")
                    if len(cpf) == 11 and cpf.isdigit():
                        self.estado["cpf"] = cpf
                        self.estado["etapa"] = "coletando_nascimento"
                        resposta = "Obrigado! Agora preciso da sua data de nascimento no formato DD/MM/AAAA ou AAAA-MM-DD."
                    else:
                        resposta = resposta_final or "Por favor, informe um CPF válido com 11 dígitos."
                else:
                    # Tenta extrair CPF diretamente da mensagem original também
                    cpf = self._extrair_cpf(mensagem)
                    if cpf:
                        self.estado["cpf"] = cpf
                        self.estado["etapa"] = "coletando_nascimento"
                        resposta = "Obrigado! Agora preciso da sua data de nascimento no formato DD/MM/AAAA ou AAAA-MM-DD."
                    else:
                        # Usa a resposta do LLM para questionamentos ou pedidos
                        resposta = resposta_final or "Por favor, informe seu CPF (apenas os números, 11 dígitos)."
            except Exception as e:
                # Fallback: tenta extrair CPF diretamente
                cpf = self._extrair_cpf(mensagem)
                if cpf:
                    self.estado["cpf"] = cpf
                    self.estado["etapa"] = "coletando_nascimento"
                    resposta = "Obrigado! Agora preciso da sua data de nascimento no formato DD/MM/AAAA ou AAAA-MM-DD."
                else:
                    resposta = f"❌ Erro na interpretação da IA: {str(e)}. Por favor, informe seu CPF (11 dígitos)."
        
        elif self.estado["etapa"] == "coletando_nascimento":
            # Usa sistema de comandos para processar data de nascimento
            try:
                prompt = f"""Você é um agente bancário coletando a data de nascimento do cliente para autenticação.

Mensagem do cliente: "{mensagem}"

SISTEMA DE COMANDOS:
Você pode responder de duas formas:

1. TEXTO NORMAL: Se você responder com texto normal, esse texto será passado diretamente para o cliente.
   Use isso quando não conseguiu identificar a data ou precisa pedir esclarecimento.

2. COMANDO: Se você identificar uma data de nascimento, responda APENAS no formato: "DATA:1990-05-15"
   (formato AAAA-MM-DD, sem espaços após os dois pontos)

INSTRUÇÕES:
- Se a mensagem contém uma data → extraia e normalize no formato AAAA-MM-DD e responda "DATA:AAAA-MM-DD"
- Se não conseguiu identificar a data → responda com texto pedindo educadamente que informe no formato DD/MM/AAAA ou AAAA-MM-DD

Formatos aceitos:
- DD/MM/AAAA (ex: 15/05/1990)
- AAAA-MM-DD (ex: 1990-05-15)

IMPORTANTE: 
- Seja natural e conversacional quando responder com texto
- Se extrair a data, responda APENAS no formato "DATA:AAAA-MM-DD" """

                resposta_final, comando, dados_comando = self.processar_com_comandos(
                    prompt, 
                    contexto_adicional="TriagemAgent.processar - Coletando Data de Nascimento",
                    usar_historico=False  # Não usa histórico para extrair data - prompt específico
                )
                
                # Se retornou comando DATA
                if comando == "DATA" and dados_comando and "dados" in dados_comando:
                    data_nasc = dados_comando["dados"].strip()
                    # Valida formato
                    import re
                    if not re.match(r'\d{4}-\d{2}-\d{2}', data_nasc):
                        # Tenta converter de DD/MM/AAAA para AAAA-MM-DD
                        data_nasc = self._extrair_data_nascimento(mensagem)
                else:
                    # Tenta extrair data diretamente da mensagem original também
                    data_nasc = self._extrair_data_nascimento(mensagem)
                
                if data_nasc:
                    self.estado["data_nascimento"] = data_nasc
                    # Tenta autenticar
                    cliente = autenticar_cliente(self.estado["cpf"], data_nasc)
                    
                    if cliente:
                        self.estado["cliente"] = cliente
                        self.estado["etapa"] = "autenticado"
                        self.estado["tentativas_falha"] = 0
                        resposta = f"Ótimo! Autenticação realizada com sucesso, {cliente.get('nome', 'cliente')}. Como posso ajudá-lo hoje?"
                    else:
                        self.estado["tentativas_falha"] += 1
                        if self.estado["tentativas_falha"] >= 3:
                            self.estado["etapa"] = "falha"
                            resposta = "Lamento, mas não foi possível autenticar após várias tentativas. Por favor, entre em contato com nosso suporte para verificar seus dados. Tenha um ótimo dia!"
                            return {
                                "resposta": resposta,
                                "proximo_agente": None,
                                "autenticado": False,
                                "cliente": None,
                                "encerrar": True
                            }
                        else:
                            tentativas_restantes = 3 - self.estado["tentativas_falha"]
                            resposta = f"Dados não conferem. Você tem {tentativas_restantes} tentativa(s) restante(s). Por favor, informe novamente seu CPF."
                            self.estado["etapa"] = "coletando_cpf"
                            self.estado["cpf"] = None
                            self.estado["data_nascimento"] = None
                else:
                    # Usa a resposta do LLM se não conseguiu extrair data
                    resposta = resposta_llm
            except Exception as e:
                # Fallback: tenta extrair data diretamente
                data_nasc = self._extrair_data_nascimento(mensagem)
                if data_nasc:
                    self.estado["data_nascimento"] = data_nasc
                    cliente = autenticar_cliente(self.estado["cpf"], data_nasc)
                    if cliente:
                        self.estado["cliente"] = cliente
                        self.estado["etapa"] = "autenticado"
                        self.estado["tentativas_falha"] = 0
                        resposta = f"Ótimo! Autenticação realizada com sucesso, {cliente.get('nome', 'cliente')}. Como posso ajudá-lo hoje?"
                    else:
                        self.estado["tentativas_falha"] += 1
                        tentativas_restantes = 3 - self.estado["tentativas_falha"]
                        resposta = f"Dados não conferem. Você tem {tentativas_restantes} tentativa(s) restante(s). Por favor, informe novamente seu CPF."
                        self.estado["etapa"] = "coletando_cpf"
                        self.estado["cpf"] = None
                        self.estado["data_nascimento"] = None
                else:
                    resposta = f"❌ Erro na interpretação da IA: {str(e)}. Por favor, informe sua data de nascimento no formato DD/MM/AAAA ou AAAA-MM-DD."
        
        elif self.estado["etapa"] == "autenticado":
            # Detecta se há saudação na mensagem
            if saudacao_detectada:
                resposta_saudacao = gerar_resposta_saudacao(saudacao_detectada, f"Como posso ajudá-lo hoje, {self.estado['cliente'].get('nome', 'cliente')}?")
                self.adicionar_mensagem(resposta_saudacao, "ai")
                return {
                    "resposta": resposta_saudacao,
                    "proximo_agente": None,
                    "autenticado": True,
                    "cliente": self.estado["cliente"],
                    "encerrar": False
                }
            
            # Cliente autenticado - usa sistema de comandos para identificar necessidade
            prompt = f"""CONTEXTO DO SISTEMA:
Você é o Agente de Triagem, responsável por identificar a necessidade do cliente e direcioná-lo para o agente especializado correto.

O sistema bancário possui múltiplos agentes especializados:
- Agente de Crédito: Consulta de limite de crédito, solicitação de aumento de limite, questões sobre cartão de crédito
- Agente de Câmbio: Consulta de cotações de moedas (dólar, euro, libra, iene, etc.), taxa de câmbio
- Agente de Entrevista: Entrevista financeira para atualizar score de crédito, melhorar avaliação de crédito
- Agente de Triagem (você): Autenticação e direcionamento inicial

Mensagem do cliente: "{mensagem}"

SISTEMA DE COMANDOS:
Você pode responder de duas formas:

1. TEXTO NORMAL: Se você responder com texto normal, esse texto será passado diretamente para o cliente.
   Use isso quando não conseguiu identificar claramente a necessidade ou precisa pedir esclarecimento.

2. COMANDOS: Se você identificar a necessidade, responda APENAS com o comando:
   - CREDITO → Direciona para Agente de Crédito
   - CAMBIO → Direciona para Agente de Câmbio
   - ENTREVISTA → Direciona para Agente de Entrevista

INSTRUÇÕES:
- Analise o contexto completo da mensagem
- Se a mensagem menciona "limite", "crédito", "cartão" → use comando CREDITO
- Se a mensagem menciona "cotação", "dólar", "euro", "moeda" → use comando CAMBIO
- Se a mensagem menciona "entrevista", "score", "avaliação" → use comando ENTREVISTA
- Se não está claro → responda com texto pedindo esclarecimento

IMPORTANTE: 
- Se você usar um comando (ex: CREDITO), o sistema redirecionará automaticamente
- Se você responder com texto, esse texto será passado diretamente para o cliente"""

            resposta_final, comando, dados_comando = self.processar_com_comandos(
                prompt, 
                contexto_adicional="TriagemAgent.processar - Identificar necessidade",
                usar_historico=False  # Não usa histórico para identificar necessidade - prompt específico
            )
            
            # Se retornou um comando, redireciona
            if comando:
                proximo_agente = comando.lower()
                if proximo_agente in ["credito", "cambio", "entrevista"]:
                    return {
                        "resposta": "",
                        "proximo_agente": proximo_agente,
                        "autenticado": True,
                        "cliente": self.estado["cliente"],
                        "encerrar": False
                    }
            
            # Se não identificou necessidade específica, usa resposta da IA ou pede esclarecimento
            resposta = resposta_final or self._gerar_resposta_esclarecimento(mensagem)
            self.adicionar_mensagem(resposta, "ai")
            return {
                "resposta": resposta,
                "proximo_agente": None,
                "autenticado": True,
                "cliente": self.estado["cliente"],
                "encerrar": False
            }
        
        else:
            resposta = "Desculpe, ocorreu um erro. Vamos começar novamente?"
            self.estado["etapa"] = "saudacao"
        
        self.adicionar_mensagem(resposta, "ai")
        
        return {
            "resposta": resposta,
            "proximo_agente": None,
            "autenticado": self.estado["etapa"] == "autenticado",
            "cliente": self.estado.get("cliente"),
            "encerrar": False
        }
    
    def _iniciar_saudacao(self) -> str:
        """Gera saudação inicial"""
        return "Olá! Bem-vindo ao Banco Ágil. Sou seu assistente virtual e estou aqui para ajudá-lo. Para começarmos, preciso fazer sua autenticação. Por favor, informe seu CPF (apenas os números)."
    
    def _extrair_cpf(self, texto: str) -> Optional[str]:
        """Extrai CPF do texto"""
        import re
        # Remove tudo que não é número
        numeros = re.sub(r'\D', '', texto)
        # CPF tem 11 dígitos
        if len(numeros) == 11:
            return numeros
        return None
    
    def _extrair_data_nascimento(self, texto: str) -> Optional[str]:
        """Extrai e normaliza data de nascimento"""
        import re
        from datetime import datetime
        
        # Tenta formato DD/MM/AAAA
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto)
        if match:
            dia, mes, ano = match.groups()
            try:
                # Valida a data
                datetime(int(ano), int(mes), int(dia))
                return f"{ano}-{mes}-{dia}"
            except:
                pass
        
        # Tenta formato AAAA-MM-DD
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto)
        if match:
            ano, mes, dia = match.groups()
            try:
                datetime(int(ano), int(mes), int(dia))
                return f"{ano}-{mes}-{dia}"
            except:
                pass
        
        return None
    
    def _identificar_necessidade(self, mensagem: str) -> str:
        """Identifica a necessidade do cliente usando LLM como método principal"""
        try:
            prompt = f"""CONTEXTO DO SISTEMA:
Você é o Agente de Triagem, responsável por identificar a necessidade do cliente e direcioná-lo para o agente especializado correto.

O sistema bancário possui múltiplos agentes especializados:
- Agente de Crédito: Consulta de limite de crédito, solicitação de aumento de limite, questões sobre cartão de crédito
- Agente de Câmbio: Consulta de cotações de moedas (dólar, euro, libra, iene, etc.), taxa de câmbio
- Agente de Entrevista: Entrevista financeira para atualizar score de crédito, melhorar avaliação de crédito
- Agente de Triagem (você): Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
Identificar qual agente especializado deve atender o cliente baseado na necessidade expressa.

Mensagem do cliente: "{mensagem}"

ANÁLISE NECESSÁRIA:
Analise a mensagem do cliente e identifique qual é a necessidade principal:

1. CRÉDITO: 
   - Consulta de limite de crédito ("quanto tenho de limite", "meu limite", "limite do cartão")
   - Solicitação de aumento de limite ("quero aumentar", "preciso de mais limite")
   - Questões sobre cartão de crédito
   → Direcione para Agente de Crédito

2. ENTREVISTA:
   - Entrevista de crédito ("fazer entrevista", "atualizar score", "melhorar score")
   - Reajustar avaliação de crédito
   → Direcione para Agente de Entrevista

3. CÂMBIO:
   - Cotação de moedas ("cotação do dólar", "quanto está o euro", "valor da libra")
   - Taxa de câmbio
   - Consulta de moedas estrangeiras
   → Direcione para Agente de Câmbio

4. OUTRO:
   - Qualquer outra necessidade que não se encaixe nas categorias acima
   → Mantenha no Agente de Triagem para esclarecimento

INSTRUÇÕES:
- Analise o contexto completo da mensagem
- Se a mensagem menciona "limite", "crédito", "cartão" → é CRÉDITO
- Se a mensagem menciona "cotação", "dólar", "euro", "moeda" → é CÂMBIO
- Se a mensagem menciona "entrevista", "score", "avaliação" → é ENTREVISTA
- Se não está claro → é OUTRO

Responda APENAS com uma das palavras: credito, entrevista, cambio, ou outro"""

            resposta_llm = self.gerar_resposta(prompt, contexto_adicional="TriagemAgent._identificar_necessidade", usar_historico=False)
            resposta_llm = resposta_llm.lower().strip()
            
            if "credito" in resposta_llm or "crédito" in resposta_llm:
                return "credito"
            elif "entrevista" in resposta_llm:
                return "entrevista"
            elif "cambio" in resposta_llm or "câmbio" in resposta_llm:
                return "cambio"
            else:
                return "outro"
        
        except Exception as e:
            # FALLBACK COMENTADO: Mantido apenas para referência futura
            # Se quiser reativar em produção, descomente abaixo
            # mensagem_lower = mensagem.lower()
            # palavras_credito = ["limite", "crédito", "credito", "aumento", "quanto tenho", "meu limite", "consulta"]
            # palavras_entrevista = ["entrevista", "score", "atualizar", "melhorar", "reajustar"]
            # palavras_cambio = ["dólar", "dolar", "cotação", "cotacao", "câmbio", "cambio", "moeda", "taxa"]
            # if any(palavra in mensagem_lower for palavra in palavras_credito):
            #     return "credito"
            # elif any(palavra in mensagem_lower for palavra in palavras_entrevista):
            #     return "entrevista"
            # elif any(palavra in mensagem_lower for palavra in palavras_cambio):
            #     return "cambio"
            
            # Se o LLM falhar, retorna erro explícito para debug
            print(f"ERRO ao usar LLM para identificar necessidade: {e}")
            raise Exception(f"Falha na interpretação da IA: {str(e)}")
    
    def _determinar_agente(self, necessidade: str) -> Optional[str]:
        """Determina qual agente deve ser chamado"""
        mapeamento = {
            "credito": "credito",
            "entrevista": "entrevista",
            "cambio": "cambio"
        }
        return mapeamento.get(necessidade)
    
    def _gerar_resposta_direcionamento(self, necessidade: str, proximo_agente: Optional[str]) -> str:
        """Gera resposta de direcionamento"""
        if proximo_agente == "credito":
            return "Perfeito! Vou te ajudar com questões de crédito. Como posso ajudar?"
        elif proximo_agente == "entrevista":
            return "Entendi! Vou conduzir uma entrevista para atualizar seu score de crédito. Vamos começar?"
        elif proximo_agente == "cambio":
            return "Claro! Vou consultar a cotação de moedas para você."
        else:
            return "Como posso ajudá-lo hoje? Posso auxiliar com questões de crédito, entrevista de crédito ou consulta de câmbio."
    
    def _gerar_resposta_esclarecimento(self, mensagem: str) -> str:
        """Gera resposta pedindo esclarecimento de forma natural e contextual"""
        try:
            prompt = f"""Você é um agente bancário amigável. O cliente disse: "{mensagem}"

Você não conseguiu identificar claramente o que o cliente precisa. 

IMPORTANTE:
- NÃO diga "Entendi" se você não entendeu
- NÃO diga "Como posso ajudá-lo?" de forma genérica
- Seja específico: mencione o que o cliente disse e peça esclarecimento
- Seja natural e conversacional, como uma pessoa real
- Se a mensagem parece ser uma saudação, responda adequadamente

Responda de forma natural e específica, mencionando o que o cliente disse e pedindo esclarecimento sobre o que ele precisa."""

            resposta = self.gerar_resposta(prompt, contexto_adicional="TriagemAgent._gerar_resposta_esclarecimento", usar_historico=False)
            return resposta
        except:
            # Fallback: resposta específica baseada na mensagem
            return f"Desculpe, não consegui entender exatamente o que você precisa quando disse '{mensagem}'. Poderia me explicar melhor? Posso ajudá-lo com questões de crédito, entrevista de crédito ou consulta de câmbio."
    
    def _verificar_encerramento(self, mensagem: str) -> bool:
        """Verifica se o usuário quer encerrar"""
        mensagem_lower = mensagem.lower().strip()
        
        # Frases completas de encerramento (mais específicas)
        frases_encerramento = [
            "encerrar", "sair", "tchau", "até logo", "fim", "terminar", "finalizar",
            "encerrar conversa", "sair daqui", "tchau tchau", "até mais", "fim da conversa"
        ]
        
        # Verifica se a mensagem é APENAS uma palavra de encerramento
        # ou se contém uma frase completa de encerramento
        if mensagem_lower in ["não", "nao", "n"]:
            return False  # "Não" sozinho não é encerramento
        
        # Verifica frases completas
        for frase in frases_encerramento:
            if frase in mensagem_lower:
                # Se a mensagem começa ou termina com a frase de encerramento, é mais provável
                if mensagem_lower.startswith(frase) or mensagem_lower.endswith(frase):
                    return True
                # Se a mensagem é muito curta e contém a frase, também considera
                if len(mensagem_lower.split()) <= 3 and frase in mensagem_lower:
                    return True
        
        return False
    
    def resetar(self):
        """Reseta o estado do agente"""
        self.estado = {
            "etapa": "saudacao",
            "tentativas_falha": 0,
            "cpf": None,
            "data_nascimento": None,
            "cliente": None
        }
        self.limpar_historico()

