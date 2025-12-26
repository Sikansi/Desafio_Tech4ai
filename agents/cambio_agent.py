"""
Agente de Câmbio - Consulta de cotação de moedas
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from utils.cotacao_api import buscar_cotacao_moeda
from utils.saudacoes import detectar_saudacao, gerar_resposta_saudacao, extrair_mensagem_sem_saudacao


class CambioAgent(BaseAgent):
    """Agente responsável por consultar cotações de moedas"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
    
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mensagem relacionada a câmbio
        
        Returns:
            Dict com resposta e informações de controle
        """
        # Detecta saudações primeiro
        saudacao_detectada = detectar_saudacao(mensagem)
        
        # Se há saudação, responde adequadamente e processa o resto da mensagem
        if saudacao_detectada:
            resposta_saudacao = gerar_resposta_saudacao(saudacao_detectada)
            mensagem_sem_saudacao = extrair_mensagem_sem_saudacao(mensagem)
            
            # Se após remover saudação não sobrou nada, apenas responde a saudação
            if not mensagem_sem_saudacao.strip():
                self.adicionar_mensagem(mensagem, "human")
                resposta = f"{resposta_saudacao} Posso ajudá-lo com consulta de cotações de moedas. Qual moeda você gostaria de consultar?"
                self.adicionar_mensagem(resposta, "ai")
                return {
                    "resposta": resposta,
                    "proximo_agente": None,
                    "encerrar": False
                }
            else:
                # Processa a mensagem sem a saudação
                mensagem = mensagem_sem_saudacao
        
        self.adicionar_mensagem(mensagem, "human")
        
        # Verifica encerramento
        if self._verificar_encerramento(mensagem):
            return {
                "resposta": "Foi um prazer ajudá-lo! Até logo!",
                "proximo_agente": None,
                "encerrar": True
            }
        
        # Usa sistema de comandos para processar a mensagem
        prompt = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados:
- Agente de Câmbio (você): Consulta de cotações de moedas
- Agente de Crédito: Consulta de limite, solicitação de aumento de limite
- Agente de Entrevista: Entrevista financeira para atualizar score
- Agente de Triagem: Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
Você é o Agente de Câmbio, especializado APENAS em consulta de cotações de moedas.

Mensagem do cliente: "{mensagem}"

SISTEMA DE COMANDOS:
Você pode responder de duas formas:

1. TEXTO NORMAL: Se você responder com texto normal, esse texto será passado diretamente para o cliente.

2. COMANDOS: Se você precisar chamar uma função, responda APENAS com o comando em maiúsculas:
   - CREDITO → Redireciona para agente de crédito
   - ENTREVISTA → Redireciona para agente de entrevista
   - DOLAR → Busca cotação do dólar americano (USD)
   - EURO → Busca cotação do euro (EUR)
   - LIBRA → Busca cotação da libra esterlina (GBP)
   - IENE → Busca cotação do iene japonês (JPY)
   - FRANCO → Busca cotação do franco suíço (CHF)
   - DOLAR_CANADENSE ou CAD → Busca cotação do dólar canadense
   - DOLAR_AUSTRALIANO ou AUD → Busca cotação do dólar australiano
   - YUAN → Busca cotação do yuan chinês (CNY)
   - PESO_ARGENTINO ou ARS → Busca cotação do peso argentino
   - PESO_CHILENO ou CLP → Busca cotação do peso chileno
   - PESO_MEXICANO ou MXN → Busca cotação do peso mexicano

INSTRUÇÕES:
1. PRIMEIRO: Verifique se a mensagem é sobre câmbio ou sobre outro assunto
   - Se for sobre limite, crédito, cartão → use comando CREDITO
   - Se for sobre entrevista, score → use comando ENTREVISTA
   - Se for sobre cotação de moedas → identifique a moeda e use o comando correspondente

2. SE FOR SOBRE MOEDAS: Identifique qual moeda o cliente quer consultar e use o comando correspondente.
   Se não conseguir identificar claramente, responda com texto pedindo esclarecimento.

3. SE NÃO FOR SOBRE MOEDAS: Use o comando de redirecionamento apropriado (CREDITO ou ENTREVISTA).

IMPORTANTE: 
- Se você usar um comando (ex: DOLAR), o sistema executará a função e retornará o resultado para você construir uma resposta natural
- Se você responder com texto, esse texto será passado diretamente para o cliente
- Seja natural e conversacional quando responder com texto"""

        resposta_final, comando, dados_comando = self.processar_com_comandos(
            prompt, 
            contexto_adicional="CambioAgent.processar",
            usar_historico=False  # Não usa histórico para identificar moeda - prompt específico
        )
        
        # Se retornou um comando, processa
        if comando:
            # Comandos de redirecionamento
            if comando == "CREDITO":
                return {
                    "resposta": "",
                    "proximo_agente": "credito",
                    "encerrar": False
                }
            elif comando == "ENTREVISTA":
                return {
                    "resposta": "",
                    "proximo_agente": "entrevista",
                    "encerrar": False
                }
            # Comandos de moedas
            elif comando in ["DOLAR", "USD"]:
                moeda = "USD"
            elif comando in ["EURO", "EUR"]:
                moeda = "EUR"
            elif comando in ["LIBRA", "GBP"]:
                moeda = "GBP"
            elif comando in ["IENE", "JPY"]:
                moeda = "JPY"
            elif comando in ["FRANCO", "CHF"]:
                moeda = "CHF"
            elif comando in ["DOLAR_CANADENSE", "CAD"]:
                moeda = "CAD"
            elif comando in ["DOLAR_AUSTRALIANO", "AUD"]:
                moeda = "AUD"
            elif comando in ["YUAN", "CNY"]:
                moeda = "CNY"
            elif comando in ["PESO_ARGENTINO", "ARS"]:
                moeda = "ARS"
            elif comando in ["PESO_CHILENO", "CLP"]:
                moeda = "CLP"
            elif comando in ["PESO_MEXICANO", "MXN"]:
                moeda = "MXN"
            else:
                # Comando desconhecido, pede esclarecimento
                resposta = f"Desculpe, não consegui identificar qual moeda você quer consultar. Poderia especificar? Posso consultar: dólar, euro, libra, iene, franco suíço, dólar canadense, dólar australiano, yuan, peso argentino, peso chileno ou peso mexicano."
                self.adicionar_mensagem(resposta, "ai")
                return {
                    "resposta": resposta,
                    "proximo_agente": None,
                    "encerrar": False
                }
            
            # Busca cotação da moeda identificada
            cotacao = buscar_cotacao_moeda(moeda)
            
            if cotacao.get("sucesso"):
                # Retorna resultado para a IA construir resposta final
                resultado_cotacao = self._formatar_resposta_cotacao(cotacao)
                prompt_final = f"""O cliente perguntou sobre a cotação de uma moeda. Você chamou a função e obteve o seguinte resultado:

{resultado_cotacao}

Agora construa uma resposta natural e conversacional para o cliente apresentando essa informação de forma amigável. Seja breve e direto."""
                
                resposta = self.gerar_resposta(prompt_final, contexto_adicional="CambioAgent.processar - Resposta final", usar_historico=False)
            else:
                resposta = f"Desculpe, não consegui obter a cotação no momento. {cotacao.get('erro', 'Tente novamente mais tarde.')}"
        else:
            # Resposta normal da IA
            resposta = resposta_final
        
        self.adicionar_mensagem(resposta, "ai")
        
        return {
            "resposta": resposta,
            "proximo_agente": None,
            "encerrar": False
        }
        
        self.adicionar_mensagem(resposta, "ai")
        
        return {
            "resposta": resposta,
            "proximo_agente": None,
            "encerrar": False
        }
    
    def _identificar_moeda(self, mensagem: str) -> str:
        """Identifica qual moeda o cliente quer consultar usando LLM"""
        try:
            prompt = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados. Cada agente tem um escopo específico:
- Agente de Câmbio (você): Consulta de cotações de moedas
- Agente de Crédito: Consulta de limite, solicitação de aumento de limite
- Agente de Entrevista: Entrevista financeira para atualizar score
- Agente de Triagem: Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
Você é o Agente de Câmbio, especializado APENAS em consulta de cotações de moedas.

Mensagem do cliente: "{mensagem}"

ANÁLISE NECESSÁRIA:
1. PRIMEIRO: Verifique se a mensagem é realmente sobre cotações de moedas
   - Se o cliente está perguntando sobre limite de crédito, crédito, cartão → NÃO é sua responsabilidade
   - Se o cliente está perguntando sobre entrevista, score → NÃO é sua responsabilidade
   - Se o cliente está perguntando sobre cotações, dólar, euro, moedas → É sua responsabilidade

2. SE FOR SOBRE MOEDAS: Identifique qual moeda o cliente quer consultar. Moedas disponíveis:
   - USD (Dólar Americano)
   - EUR (Euro)
   - GBP (Libra Esterlina)
   - JPY (Iene Japonês)
   - CHF (Franco Suíço)
   - CAD (Dólar Canadense)
   - AUD (Dólar Australiano)
   - CNY (Yuan Chinês)
   - ARS (Peso Argentino)
   - CLP (Peso Chileno)
   - MXN (Peso Mexicano)

3. SE NÃO FOR SOBRE MOEDAS: Responda "OUTRO" para indicar que precisa redirecionar

INSTRUÇÕES:
- Se a mensagem é sobre cotação de moedas → responda APENAS com o código da moeda em maiúsculas (ex: USD, EUR, GBP)
- Se a mensagem NÃO é sobre moedas → responda "OUTRO"
- Se não conseguir identificar a moeda mas é sobre câmbio → responda "USD" (padrão)

IMPORTANTE: Se o cliente perguntar sobre limite, crédito, cartão, entrevista ou qualquer coisa que não seja cotação de moedas, você DEVE responder "OUTRO" para que o sistema redirecione para o agente correto."""

            resposta_llm = self.gerar_resposta(prompt, contexto_adicional="CambioAgent._identificar_moeda").upper().strip()
            
            # Se a resposta indica que não é sobre moedas, retorna None para sinalizar redirecionamento
            if "OUTRO" in resposta_llm:
                return None
            
            # Extrai código da moeda da resposta
            moedas_validas = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "ARS", "CLP", "MXN"]
            for moeda in moedas_validas:
                if moeda in resposta_llm:
                    return moeda
            
            # Se não encontrou código válido, tenta identificar pelo nome na resposta
            resposta_lower = resposta_llm.lower()
            if "euro" in resposta_lower or "eur" in resposta_lower:
                return "EUR"
            elif "libra" in resposta_lower or "gbp" in resposta_lower:
                return "GBP"
            elif "iene" in resposta_lower or "yen" in resposta_lower or "jpy" in resposta_lower:
                return "JPY"
            elif "franco" in resposta_lower or "chf" in resposta_lower:
                return "CHF"
            elif "canadense" in resposta_lower or "cad" in resposta_lower:
                return "CAD"
            elif "australiano" in resposta_lower or "aud" in resposta_lower:
                return "AUD"
            elif "yuan" in resposta_lower or "cny" in resposta_lower:
                return "CNY"
            elif "argentino" in resposta_lower or "ars" in resposta_lower:
                return "ARS"
            elif "chileno" in resposta_lower or "clp" in resposta_lower:
                return "CLP"
            elif "mexicano" in resposta_lower or "mxn" in resposta_lower:
                return "MXN"
            else:
                # Por padrão, retorna USD
                return "USD"
        
        except Exception as e:
            # FALLBACK COMENTADO: Mantido apenas para referência futura
            # Se quiser reativar em produção, descomente abaixo
            # mensagem_lower = mensagem.lower()
            # mapeamento_moedas = {
            #     "dólar": "USD", "dolar": "USD", "usd": "USD", "dollar": "USD",
            #     "euro": "EUR", "eur": "EUR",
            #     "libra": "GBP", "gbp": "GBP",
            #     "iene": "JPY", "yen": "JPY", "jpy": "JPY",
            #     "franco": "CHF", "chf": "CHF",
            #     "dólar canadense": "CAD", "dolar canadense": "CAD", "cad": "CAD",
            #     "dólar australiano": "AUD", "dolar australiano": "AUD", "aud": "AUD",
            #     "yuan": "CNY", "cny": "CNY",
            #     "peso argentino": "ARS", "ars": "ARS",
            #     "peso chileno": "CLP", "clp": "CLP",
            #     "peso mexicano": "MXN", "mxn": "MXN",
            # }
            # for palavra, codigo in mapeamento_moedas.items():
            #     if palavra in mensagem_lower:
            #         return codigo
            # return "USD"
            
            # Se o LLM falhar, retorna erro explícito para debug
            print(f"ERRO ao usar LLM para identificar moeda: {e}")
            raise Exception(f"Falha na interpretação da IA para identificar moeda: {str(e)}")
    
    def _formatar_resposta_cotacao(self, cotacao: Dict[str, Any]) -> str:
        """Formata resposta da cotação de forma amigável"""
        moeda = cotacao.get("moeda", "USD")
        moeda_destino = cotacao.get("moeda_destino", "BRL")
        valor = cotacao.get("valor_medio", cotacao.get("valor_compra", 0))
        
        nome_moeda = {
            "USD": "Dólar Americano",
            "EUR": "Euro",
            "GBP": "Libra Esterlina",
            "JPY": "Iene Japonês",
            "CHF": "Franco Suíço",
            "CAD": "Dólar Canadense",
            "AUD": "Dólar Australiano",
            "CNY": "Yuan Chinês",
            "ARS": "Peso Argentino",
            "CLP": "Peso Chileno",
            "MXN": "Peso Mexicano"
        }.get(moeda, moeda)
        
        resposta = f"📊 Cotação do {nome_moeda} ({moeda}):\n\n"
        resposta += f"💵 Valor: R$ {valor:,.4f}\n"
        
        if cotacao.get("valor_compra") and cotacao.get("valor_venda"):
            resposta += f"📈 Compra: R$ {cotacao['valor_compra']:,.4f}\n"
            resposta += f"📉 Venda: R$ {cotacao['valor_venda']:,.4f}\n"
        
        return resposta
    
    def _identificar_necessidade_outro_agente(self, mensagem: str) -> Optional[str]:
        """Identifica se o usuário quer algo fora do escopo de câmbio usando LLM"""
        try:
            prompt = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados. Cada agente tem um escopo específico:
- Agente de Câmbio (você): Consulta de cotações de moedas
- Agente de Crédito: Consulta de limite, solicitação de aumento de limite
- Agente de Entrevista: Entrevista financeira para atualizar score
- Agente de Triagem: Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
Você é o Agente de Câmbio, especializado APENAS em consulta de cotações de moedas.

Mensagem do cliente: "{mensagem}"

ANÁLISE NECESSÁRIA:
Determine se a mensagem do cliente é sobre:
1. CÂMBIO/MOEDAS: Cotação de moedas (dólar, euro, libra, etc.) → É sua responsabilidade
2. CRÉDITO: Limite de crédito, aumento de limite, cartão → NÃO é sua responsabilidade, redirecione para Agente de Crédito
3. ENTREVISTA: Entrevista de crédito, atualizar score → NÃO é sua responsabilidade, redirecione para Agente de Entrevista
4. OUTRO: Qualquer outra coisa → NÃO é sua responsabilidade

INSTRUÇÕES:
- Se a mensagem é sobre cotação de moedas → responda "cambio"
- Se a mensagem é sobre limite, crédito, cartão → responda "credito"
- Se a mensagem é sobre entrevista, score → responda "entrevista"
- Se a mensagem não é sobre nenhum dos acima → responda "outro"

Responda APENAS com uma palavra: cambio, credito, entrevista, ou outro"""

            resposta_llm = self.gerar_resposta(prompt, contexto_adicional="CambioAgent._identificar_necessidade_outro_agente").lower().strip()
            
            # Extrai a intenção da resposta do LLM
            if "credito" in resposta_llm or "crédito" in resposta_llm or "limite" in resposta_llm:
                return "credito"
            elif "entrevista" in resposta_llm:
                return "entrevista"
            elif "cambio" in resposta_llm or "câmbio" in resposta_llm or "moeda" in resposta_llm:
                return None  # É câmbio, mantém no agente atual
            else:
                return None  # Não identificou necessidade específica, mantém no agente atual
                
        except Exception as e:
            # FALLBACK COMENTADO: Mantido apenas para referência futura
            # Se quiser reativar em produção, descomente abaixo
            # mensagem_lower = mensagem.lower()
            # if any(palavra in mensagem_lower for palavra in ["limite", "crédito", "credito", "cartão"]) and "moeda" not in mensagem_lower:
            #     return "credito"
            # return None
            
            # Se o LLM falhar, retorna erro explícito para debug
            print(f"ERRO ao usar LLM para identificar necessidade de outro agente: {e}")
            raise Exception(f"Falha na interpretação da IA para identificar necessidade: {str(e)}")
    
    def _identificar_necessidade_outro_agente(self, mensagem: str) -> Optional[str]:
        """Identifica se o usuário quer algo fora do escopo de câmbio usando LLM"""
        try:
            prompt = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados. Cada agente tem um escopo específico:
- Agente de Câmbio (você): Consulta de cotações de moedas
- Agente de Crédito: Consulta de limite, solicitação de aumento de limite
- Agente de Entrevista: Entrevista financeira para atualizar score
- Agente de Triagem: Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
Você é o Agente de Câmbio, especializado APENAS em consulta de cotações de moedas.

Mensagem do cliente: "{mensagem}"

ANÁLISE NECESSÁRIA:
Determine se a mensagem do cliente é sobre:
1. CÂMBIO/MOEDAS: Cotação de moedas (dólar, euro, libra, etc.) → É sua responsabilidade
2. CRÉDITO: Limite de crédito, aumento de limite, cartão → NÃO é sua responsabilidade, redirecione para Agente de Crédito
3. ENTREVISTA: Entrevista de crédito, atualizar score → NÃO é sua responsabilidade, redirecione para Agente de Entrevista
4. OUTRO: Qualquer outra coisa → Mantenha no agente atual

INSTRUÇÕES:
- Se a mensagem é sobre cotação de moedas → responda "cambio"
- Se a mensagem é sobre limite, crédito, cartão → responda "credito"
- Se a mensagem é sobre entrevista, score → responda "entrevista"
- Se a mensagem não é sobre nenhum dos acima → responda "outro"

IMPORTANTE: 
- Se o cliente perguntar "quanto é meu limite" ou "aumentar limite" → é CRÉDITO
- Se o cliente perguntar "cotação do dólar" ou "valor do euro" → é CÂMBIO (sua responsabilidade)
- Se o cliente perguntar sobre entrevista ou atualizar score → é ENTREVISTA

Responda APENAS com uma palavra: cambio, credito, entrevista, ou outro"""

            resposta_llm = self.gerar_resposta(prompt, contexto_adicional="CambioAgent._identificar_necessidade_outro_agente").lower().strip()
            
            # Extrai a intenção da resposta do LLM
            if "credito" in resposta_llm or "crédito" in resposta_llm or "limite" in resposta_llm:
                return "credito"
            elif "entrevista" in resposta_llm:
                return "entrevista"
            elif "cambio" in resposta_llm or "câmbio" in resposta_llm or "moeda" in resposta_llm:
                return None  # É câmbio, mantém no agente atual
            else:
                return None  # Não identificou necessidade específica, mantém no agente atual
                
        except Exception as e:
            # FALLBACK COMENTADO: Mantido apenas para referência futura
            # Se quiser reativar em produção, descomente abaixo
            # mensagem_lower = mensagem.lower()
            # if any(palavra in mensagem_lower for palavra in ["limite", "crédito", "credito", "cartão"]) and "moeda" not in mensagem_lower:
            #     return "credito"
            # return None
            
            # Se o LLM falhar, retorna erro explícito para debug
            print(f"ERRO ao usar LLM para identificar necessidade de outro agente: {e}")
            raise Exception(f"Falha na interpretação da IA para identificar necessidade: {str(e)}")
    
    def _gerar_resposta_esclarecimento(self, mensagem: str, erro: Optional[str] = None) -> str:
        """Gera resposta pedindo esclarecimento de forma natural e contextual"""
        try:
            prompt = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados:
- Agente de Câmbio (você): Consulta de cotações de moedas
- Agente de Crédito: Consulta de limite, solicitação de aumento de limite
- Agente de Entrevista: Entrevista financeira para atualizar score

SUA RESPONSABILIDADE:
Você é o Agente de Câmbio, especializado APENAS em consulta de cotações de moedas.

O cliente disse: "{mensagem}"

Você não conseguiu identificar claramente qual moeda o cliente quer consultar ou houve um erro ao buscar a cotação.

IMPORTANTE:
- NÃO diga "Entendi" se você não entendeu
- NÃO diga "Como posso ajudá-lo?" de forma genérica
- Seja específico: mencione o que o cliente disse
- Seja natural e conversacional, como uma pessoa real
- Se a mensagem parece ser sobre crédito ou limite, explique que você é especializado em câmbio e pode redirecionar
- Ofereça opções de moedas disponíveis se não identificou qual moeda

Moedas disponíveis: Dólar (USD), Euro (EUR), Libra (GBP), Iene (JPY), Franco Suíço (CHF), Dólar Canadense (CAD), Dólar Australiano (AUD), Yuan (CNY), Peso Argentino (ARS), Peso Chileno (CLP), Peso Mexicano (MXN).

Responda de forma natural e específica, mencionando o que o cliente disse e pedindo esclarecimento sobre qual moeda ele quer consultar."""

            resposta = self.gerar_resposta(prompt, contexto_adicional="CambioAgent._gerar_resposta_esclarecimento")
            return resposta
        except:
            # Fallback: resposta específica baseada na mensagem
            if erro:
                return f"Desculpe, não consegui obter a cotação. {erro} Poderia tentar novamente ou especificar qual moeda você gostaria de consultar? (ex: dólar, euro, libra)"
            else:
                return f"Desculpe, não consegui identificar qual moeda você quer consultar quando disse '{mensagem}'. Poderia especificar? Posso consultar: dólar, euro, libra, iene, franco suíço, dólar canadense, dólar australiano, yuan, peso argentino, peso chileno ou peso mexicano."
    
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

