"""
Agente de Entrevista de Crédito - Coleta dados e recalcula score
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from utils.csv_handler import atualizar_score_cliente, obter_cliente_por_cpf
from utils.score_calculator import calcular_score
from utils.saudacoes import detectar_saudacao, gerar_resposta_saudacao, extrair_mensagem_sem_saudacao


class EntrevistaAgent(BaseAgent):
    """Agente responsável por conduzir entrevista financeira e recalcular score"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.cliente = None
        self.estado = {
            "etapa": "inicio",  # inicio, renda, emprego, despesas, dependentes, dividas, finalizado
            "dados_coletados": {
                "renda_mensal": None,
                "tipo_emprego": None,
                "despesas_fixas": None,
                "num_dependentes": None,
                "tem_dividas": None
            }
        }
    
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mensagem na entrevista de crédito
        
        Returns:
            Dict com resposta e informações de controle
        """
        # Obtém dados do cliente
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
        
        # Detecta saudações primeiro
        saudacao_detectada = detectar_saudacao(mensagem)
        
        # Se está na etapa "inicio" e recebeu uma mensagem, usa LLM para determinar se deve iniciar
        if self.estado["etapa"] == "inicio":
            # Se há saudação no início, responde e continua
            if saudacao_detectada:
                resposta_saudacao = gerar_resposta_saudacao(saudacao_detectada)
                mensagem_sem_saudacao = extrair_mensagem_sem_saudacao(mensagem)
                if not mensagem_sem_saudacao.strip():
                    # Apenas saudação, responde e inicia entrevista
                    resposta, proximo_agente = self._processar_etapa("")
                    resposta = f"{resposta_saudacao} {resposta}"
                    self.adicionar_mensagem(resposta, "ai")
                    return {
                        "resposta": resposta,
                        "proximo_agente": proximo_agente,
                        "encerrar": False
                    }
                else:
                    # Saudação + conteúdo, processa sem saudação
                    mensagem = mensagem_sem_saudacao
            
            # Usa sistema de comandos para determinar se deve iniciar a entrevista
            try:
                prompt = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados:
- Agente de Entrevista (você): Entrevista financeira para atualizar score de crédito
- Agente de Crédito: Consulta de limite, solicitação de aumento de limite
- Agente de Câmbio: Consulta de cotações de moedas
- Agente de Triagem: Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
Você é o Agente de Entrevista, especializado em conduzir entrevistas financeiras para atualizar o score de crédito do cliente.

SITUAÇÃO ATUAL:
Você está iniciando uma entrevista de crédito. O cliente respondeu: "{mensagem}"

SISTEMA DE COMANDOS:
Você pode responder de duas formas:

1. TEXTO NORMAL: Se você responder com texto normal, esse texto será passado diretamente para o cliente.
   Use isso quando o cliente está questionando, recusando ou precisa de esclarecimento.

2. COMANDO: Se o cliente está aceitando/pronto para começar a entrevista, responda APENAS: "INICIAR_ENTREVISTA"

INSTRUÇÕES:
- Se o cliente disse "sim", "ok", "quero", "vamos", "pode ser", "por favor", ou qualquer forma de aceitação → responda "INICIAR_ENTREVISTA"
- Se o cliente disse "não", "não quero", ou qualquer forma de recusa → responda com texto explicando e perguntando se quer continuar
- Se a mensagem não é clara → responda com texto pedindo esclarecimento
- Se o cliente perguntar sobre algo fora do escopo da entrevista (ex: cotação de moedas, limite atual) → responda com texto mencionando que pode ajudar após a entrevista

IMPORTANTE: 
- Se você usar o comando "INICIAR_ENTREVISTA", a entrevista começará automaticamente
- Se você responder com texto, esse texto será passado diretamente para o cliente
- Seja natural e conversacional quando responder com texto"""

                resposta_final, comando, dados_comando = self.processar_com_comandos(
                    prompt, 
                    contexto_adicional="EntrevistaAgent.processar - Iniciar entrevista",
                    usar_historico=False
                )
                
                if comando == "INICIAR_ENTREVISTA":
                    # Inicia a entrevista diretamente
                    resposta, proximo_agente = self._processar_etapa("")
                    self.adicionar_mensagem(resposta, "ai")
                    return {
                        "resposta": resposta,
                        "proximo_agente": proximo_agente,
                        "encerrar": False
                    }
                else:
                    # Resposta normal da IA (esclarecimento ou recusa)
                    resposta = resposta_final or "Entendi. Gostaria de iniciar a entrevista para atualizar seu score de crédito?"
                    self.adicionar_mensagem(resposta, "ai")
                    return {
                        "resposta": resposta,
                        "proximo_agente": None,
                        "encerrar": False
                    }
            except Exception as e:
                # FALLBACK COMENTADO: Mantido apenas para referência futura
                # Se quiser reativar em produção, descomente abaixo
                # mensagem_lower = mensagem.lower().strip()
                # palavras_simples = ["sim", "ok", "okay", "quero", "vamos", "pode ser"]
                # if any(palavra in mensagem_lower for palavra in palavras_simples):
                #     resposta, proximo_agente = self._processar_etapa("")
                #     self.adicionar_mensagem(resposta, "ai")
                #     return {
                #         "resposta": resposta,
                #         "proximo_agente": proximo_agente,
                #         "encerrar": False
                #     }
                
                # Se o LLM falhar, retorna erro explícito para debug
                print(f"ERRO ao usar LLM para iniciar entrevista: {e}")
                raise Exception(f"Falha na interpretação da IA para iniciar entrevista: {str(e)}")
        
        self.adicionar_mensagem(mensagem, "human")
        
        # Se a entrevista já foi finalizada, verifica se o cliente quer fazer outras coisas
        if self.estado["etapa"] == "finalizado":
            # Verifica se o cliente quer fazer outras coisas (crédito, câmbio, etc.)
            prompt_redirecionamento = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados:
- Agente de Entrevista (você): Entrevista financeira para atualizar score de crédito
- Agente de Crédito: Consulta de limite, solicitação de aumento de limite
- Agente de Câmbio: Consulta de cotações de moedas
- Agente de Triagem: Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
A entrevista já foi concluída. O cliente disse: "{mensagem}"

SISTEMA DE COMANDOS:
Você pode responder de duas formas:

1. TEXTO NORMAL: Se você responder com texto normal, esse texto será passado diretamente para o cliente.

2. COMANDOS: Se o cliente quer fazer algo específico, responda APENAS com o comando:
   - CREDITO → Redireciona para agente de crédito (se mencionar limite, crédito, aumento)
   - CAMBIO → Redireciona para agente de câmbio (se mencionar cotação, dólar, moeda)
   - OUTRO → Se não conseguir identificar claramente

INSTRUÇÕES:
- Se o cliente mencionar limite, crédito, aumento → use comando CREDITO
- Se o cliente mencionar cotação, dólar, euro, moeda → use comando CAMBIO
- Se não está claro → responda com texto explicando que a entrevista terminou e perguntando como pode ajudar

IMPORTANTE: 
- Se você usar um comando (ex: CREDITO), o sistema redirecionará automaticamente
- Se você responder com texto, esse texto será passado diretamente para o cliente"""

            try:
                resposta_final, comando, dados_comando = self.processar_com_comandos(
                    prompt_redirecionamento,
                    contexto_adicional="EntrevistaAgent.processar - Após entrevista",
                    usar_historico=False
                )
                
                if comando == "CREDITO":
                    return {
                        "resposta": "",
                        "proximo_agente": "credito",
                        "encerrar": False
                    }
                elif comando == "CAMBIO":
                    return {
                        "resposta": "",
                        "proximo_agente": "cambio",
                        "encerrar": False
                    }
                else:
                    # Resposta normal da IA
                    resposta = resposta_final or "A entrevista já foi concluída. Como posso ajudá-lo?"
                    self.adicionar_mensagem(resposta, "ai")
                    return {
                        "resposta": resposta,
                        "proximo_agente": None,
                        "encerrar": False
                    }
            except Exception as e:
                # Fallback: redireciona para crédito se mencionar limite/aumento
                mensagem_lower = mensagem.lower()
                if any(palavra in mensagem_lower for palavra in ["limite", "aumento", "crédito", "credito"]):
                    return {
                        "resposta": "",
                        "proximo_agente": "credito",
                        "encerrar": False
                    }
                elif any(palavra in mensagem_lower for palavra in ["dólar", "dolar", "cotação", "cotacao", "moeda"]):
                    return {
                        "resposta": "",
                        "proximo_agente": "cambio",
                        "encerrar": False
                    }
                else:
                    resposta = "A entrevista já foi concluída. Como posso ajudá-lo?"
                    self.adicionar_mensagem(resposta, "ai")
                    return {
                        "resposta": resposta,
                        "proximo_agente": None,
                        "encerrar": False
                    }
        
        # Verifica encerramento
        if self._verificar_encerramento(mensagem):
            return {
                "resposta": "Entendido. A entrevista foi cancelada. Posso ajudá-lo com mais alguma coisa?",
                "proximo_agente": None,
                "encerrar": False
            }
        
        # Processa etapa atual
        resposta, proximo_agente = self._processar_etapa(mensagem)
        
        self.adicionar_mensagem(resposta, "ai")
        
        return {
            "resposta": resposta,
            "proximo_agente": proximo_agente,
            "encerrar": False
        }
    
    def _processar_etapa(self, mensagem: str) -> tuple:
        """Processa a etapa atual da entrevista"""
        etapa = self.estado["etapa"]
        dados = self.estado["dados_coletados"]
        
        if etapa == "inicio":
            self.estado["etapa"] = "renda"
            return "Ótimo! Vamos começar a entrevista para atualizar sua avaliação de crédito. Primeira pergunta: qual é a sua renda mensal? (Informe apenas o valor numérico, ex: 5000, 250000 ou 1 milhão)", None
        
        elif etapa == "renda":
            renda = self._extrair_valor(mensagem)
            if renda and renda > 0:
                # Confirma o valor antes de prosseguir
                valor_formatado = f"R$ {renda:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                dados["renda_mensal"] = renda
                self.estado["etapa"] = "emprego"
                return f"Entendi! Sua renda mensal é de {valor_formatado}. Agora, qual é o seu tipo de emprego? (formal, autônomo ou desempregado)", None
            else:
                return "Por favor, informe sua renda mensal em valores numéricos (ex: 5000, 250000 ou 1 milhão).", None
        
        elif etapa == "emprego":
            # Usa IA para extrair o tipo de emprego
            prompt = f"""Você está coletando o tipo de emprego do cliente para uma entrevista de crédito.

Mensagem do cliente: "{mensagem}"

Sua tarefa:
1. Identifique o tipo de emprego e responda APENAS com um dos comandos:
   - TIPO:formal (se mencionar CLT, carteira assinada, formal, empregado)
   - TIPO:autônomo (se mencionar autônomo, PJ, MEI, freelancer)
   - TIPO:desempregado (se mencionar desempregado, sem emprego, não trabalha)
2. Se não conseguir identificar claramente, responda com texto pedindo esclarecimento

IMPORTANTE:
- Se identificar o tipo, responda APENAS no formato "TIPO:tipo" (sem espaços após os dois pontos)
- Se não conseguir identificar, responda com texto natural pedindo esclarecimento"""

            try:
                resposta_llm, comando, dados_comando = self.processar_com_comandos(
                    prompt,
                    contexto_adicional="EntrevistaAgent._processar_etapa - Emprego",
                    usar_historico=False
                )
                
                if comando == "TIPO" and dados_comando and "dados" in dados_comando:
                    tipo = dados_comando["dados"].lower()
                    if tipo in ["formal", "autônomo", "autonomo", "desempregado"]:
                        if tipo == "autonomo":
                            tipo = "autônomo"
                        dados["tipo_emprego"] = tipo
                        self.estado["etapa"] = "despesas"
                        return "Entendido! Qual é o valor das suas despesas fixas mensais? (aluguel, contas, etc.)", None
                
                # Fallback: tenta extrair tipo diretamente
                tipo = self._extrair_tipo_emprego(mensagem)
                if tipo:
                    dados["tipo_emprego"] = tipo
                    self.estado["etapa"] = "despesas"
                    return "Entendido! Qual é o valor das suas despesas fixas mensais? (aluguel, contas, etc.)", None
                else:
                    return resposta_llm or "Por favor, informe se você trabalha de forma formal, autônoma ou se está desempregado.", None
            except Exception as e:
                # Fallback para extração direta
                tipo = self._extrair_tipo_emprego(mensagem)
                if tipo:
                    dados["tipo_emprego"] = tipo
                    self.estado["etapa"] = "despesas"
                    return "Entendido! Qual é o valor das suas despesas fixas mensais? (aluguel, contas, etc.)", None
                else:
                    return "Por favor, informe se você trabalha de forma formal, autônoma ou se está desempregado.", None
        
        elif etapa == "despesas":
            # Usa IA para extrair o valor das despesas
            prompt = f"""Você está coletando o valor das despesas fixas mensais do cliente para uma entrevista de crédito.

Mensagem do cliente: "{mensagem}"

Sua tarefa:
1. Se a mensagem contém um valor numérico (ex: "0", "zero", "3000", "3 mil", "não gasto nada"), extraia APENAS o valor numérico e responda no formato: "VALOR:0" ou "VALOR:3000"
2. Se mencionar "zero", "não gasto", "nada", "não tenho despesas" → responda "VALOR:0"
3. Se não conseguiu identificar um valor numérico, responda com texto pedindo esclarecimento

IMPORTANTE:
- Aceite valores como "0", "zero", "não gasto nada", "3000", "3 mil", etc.
- Se extrair o valor, responda APENAS no formato "VALOR:numero" (sem espaços após os dois pontos)
- Se não conseguir extrair, responda com texto natural pedindo o valor"""

            try:
                resposta_llm, comando, dados_comando = self.processar_com_comandos(
                    prompt,
                    contexto_adicional="EntrevistaAgent._processar_etapa - Despesas",
                    usar_historico=False
                )
                
                if comando == "VALOR" and dados_comando and "dados" in dados_comando:
                    try:
                        despesas = float(dados_comando["dados"])
                        # Aceita 0 explicitamente ou valores maiores que 0
                        if despesas == 0.0 or despesas > 0:
                            valor_formatado = f"R$ {despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            dados["despesas_fixas"] = despesas
                            self.estado["etapa"] = "dependentes"
                            return f"Entendi! Suas despesas fixas mensais são de {valor_formatado}. Quantos dependentes você possui? (Informe um número: 0, 1, 2, 3 ou mais)", None
                    except:
                        pass
                
                # Fallback: verifica explicitamente se é zero antes de extrair valor
                mensagem_lower = mensagem.lower().strip()
                if mensagem_lower == "zero" or mensagem_lower == "0" or mensagem_lower == "0.0" or mensagem_lower == "0,0" or "não gasto" in mensagem_lower or "nada" in mensagem_lower:
                    despesas = 0.0
                else:
                    despesas = self._extrair_valor(mensagem)
                
                # Aceita 0 explicitamente ou valores maiores que 0
                if despesas is not None and (despesas == 0.0 or despesas > 0):
                    valor_formatado = f"R$ {despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    dados["despesas_fixas"] = despesas
                    self.estado["etapa"] = "dependentes"
                    return f"Entendi! Suas despesas fixas mensais são de {valor_formatado}. Quantos dependentes você possui? (Informe um número: 0, 1, 2, 3 ou mais)", None
                else:
                    return resposta_llm or "Por favor, informe o valor das suas despesas fixas mensais em valores numéricos (ex: 3000 ou 0).", None
            except Exception as e:
                # Fallback para extração direta
                mensagem_lower = mensagem.lower().strip()
                if mensagem_lower == "zero" or mensagem_lower == "0" or mensagem_lower == "0.0" or mensagem_lower == "0,0" or "não gasto" in mensagem_lower or "nada" in mensagem_lower:
                    despesas = 0.0
                else:
                    despesas = self._extrair_valor(mensagem)
                
                if despesas is not None and (despesas == 0.0 or despesas > 0):
                    valor_formatado = f"R$ {despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    dados["despesas_fixas"] = despesas
                    self.estado["etapa"] = "dependentes"
                    return f"Entendi! Suas despesas fixas mensais são de {valor_formatado}. Quantos dependentes você possui? (Informe um número: 0, 1, 2, 3 ou mais)", None
                else:
                    return "Por favor, informe o valor das suas despesas fixas mensais em valores numéricos (ex: 3000 ou 0).", None
        
        elif etapa == "dependentes":
            # Usa IA para extrair número de dependentes
            prompt = f"""Você está coletando o número de dependentes do cliente para uma entrevista de crédito.

Mensagem do cliente: "{mensagem}"

Sua tarefa:
1. Se a mensagem contém um número de dependentes (0, 1, 2, 3 ou mais), extraia e responda: "DEPENDENTES:numero"
2. Se mencionar "nenhum", "zero", "não tenho" → responda "DEPENDENTES:0"
3. Se não conseguir identificar, responda com texto pedindo esclarecimento

IMPORTANTE:
- Se extrair o número, responda APENAS no formato "DEPENDENTES:numero" (sem espaços após os dois pontos)
- Se não conseguir extrair, responda com texto natural pedindo o número"""

            try:
                resposta_llm, comando, dados_comando = self.processar_com_comandos(
                    prompt,
                    contexto_adicional="EntrevistaAgent._processar_etapa - Dependentes",
                    usar_historico=False
                )
                
                if comando == "DEPENDENTES" and dados_comando and "dados" in dados_comando:
                    try:
                        num_dep = int(dados_comando["dados"])
                        dados["num_dependentes"] = num_dep
                        self.estado["etapa"] = "dividas"
                        return "Obrigado! Última pergunta: você possui dívidas ativas? (sim ou não)", None
                    except:
                        pass
                
                # Fallback: tenta extrair número diretamente
                num_dep = self._extrair_numero_dependentes(mensagem)
                if num_dep is not None:
                    dados["num_dependentes"] = num_dep
                    self.estado["etapa"] = "dividas"
                    return "Obrigado! Última pergunta: você possui dívidas ativas? (sim ou não)", None
                else:
                    return resposta_llm or "Por favor, informe o número de dependentes (0, 1, 2, 3 ou mais).", None
            except Exception as e:
                # Fallback para extração direta
                num_dep = self._extrair_numero_dependentes(mensagem)
                if num_dep is not None:
                    dados["num_dependentes"] = num_dep
                    self.estado["etapa"] = "dividas"
                    return "Obrigado! Última pergunta: você possui dívidas ativas? (sim ou não)", None
                else:
                    return "Por favor, informe o número de dependentes (0, 1, 2, 3 ou mais).", None
        
        elif etapa == "dividas":
            # Usa IA para extrair resposta sim/não sobre dívidas
            prompt = f"""Você está coletando se o cliente possui dívidas ativas para uma entrevista de crédito.

Mensagem do cliente: "{mensagem}"

Sua tarefa:
1. Se o cliente disse "sim", "tenho", "possui", "tem dívidas" → responda "DIVIDAS:sim"
2. Se o cliente disse "não", "não tenho", "não possui", "não tem" → responda "DIVIDAS:não"
3. Se não conseguir identificar claramente, responda com texto pedindo esclarecimento

IMPORTANTE:
- Se identificar a resposta, responda APENAS no formato "DIVIDAS:sim" ou "DIVIDAS:não" (sem espaços após os dois pontos)
- Se não conseguir identificar, responda com texto natural pedindo esclarecimento"""

            try:
                resposta_llm, comando, dados_comando = self.processar_com_comandos(
                    prompt,
                    contexto_adicional="EntrevistaAgent._processar_etapa - Dívidas",
                    usar_historico=False
                )
                
                if comando == "DIVIDAS" and dados_comando and "dados" in dados_comando:
                    resposta_dividas = dados_comando["dados"].lower()
                    if resposta_dividas in ["sim", "yes", "true", "1"]:
                        tem_dividas = True
                    elif resposta_dividas in ["não", "nao", "no", "false", "0"]:
                        tem_dividas = False
                    else:
                        tem_dividas = None
                    
                    if tem_dividas is not None:
                        dados["tem_dividas"] = tem_dividas
                        # Calcula novo score (sem mencionar ao cliente)
                        novo_score = self._calcular_e_atualizar_score()
                        self.estado["etapa"] = "finalizado"
                        # Não menciona score nem redirecionamento explícito (transição transparente)
                        resposta = "Perfeito! Concluí a entrevista e atualizei suas informações. Agora posso fazer uma nova análise do seu limite de crédito. Gostaria de solicitar um aumento?"
                        return resposta, "credito"
                
                # Fallback: tenta extrair booleano diretamente
                tem_dividas = self._extrair_booleano(mensagem)
                if tem_dividas is not None:
                    dados["tem_dividas"] = tem_dividas
                    novo_score = self._calcular_e_atualizar_score()
                    self.estado["etapa"] = "finalizado"
                    resposta = "Perfeito! Concluí a entrevista e atualizei suas informações. Agora posso fazer uma nova análise do seu limite de crédito. Gostaria de solicitar um aumento?"
                    return resposta, "credito"
                else:
                    return resposta_llm or "Por favor, responda se você possui dívidas ativas: sim ou não.", None
            except Exception as e:
                # Fallback para extração direta
                tem_dividas = self._extrair_booleano(mensagem)
                if tem_dividas is not None:
                    dados["tem_dividas"] = tem_dividas
                    novo_score = self._calcular_e_atualizar_score()
                    self.estado["etapa"] = "finalizado"
                    resposta = "Perfeito! Concluí a entrevista e atualizei suas informações. Agora posso fazer uma nova análise do seu limite de crédito. Gostaria de solicitar um aumento?"
                    return resposta, "credito"
                else:
                    return "Por favor, responda se você possui dívidas ativas: sim ou não.", None
        
        else:
            return "A entrevista já foi concluída. Posso ajudá-lo com mais alguma coisa?", None
    
    def _extrair_valor(self, texto: str) -> Optional[float]:
        """Extrai valor numérico do texto, incluindo palavras como 'milhão', 'mil', 'zero'"""
        import re
        
        texto_lower = texto.lower().strip()
        
        # Verifica se é "zero" ou "0"
        if texto_lower == "zero" or texto_lower == "0" or texto_lower == "0.0" or texto_lower == "0,0":
            return 0.0
        
        # Remove pontos de milhar e substitui vírgula por ponto
        texto_limpo = texto.replace('.', '').replace(',', '.')
        
        # Verifica "k" ou "k " no final (ex: "250k", "250 k", "250k por mês")
        multiplicador_k = 1.0
        if re.search(r'\d+\s*k\b', texto_lower) or re.search(r'\d+k\b', texto_lower):
            multiplicador_k = 1000.0
            # Remove "k" para extrair o número
            texto_limpo = re.sub(r'\d+\s*k\b', lambda m: m.group().replace('k', '').replace('K', ''), texto_limpo)
            texto_limpo = re.sub(r'\d+k\b', lambda m: m.group().replace('k', '').replace('K', ''), texto_limpo)
        
        # Procura por números
        numeros = re.findall(r'\d+\.?\d*', texto_limpo)
        
        valor_base = None
        if numeros:
            try:
                valor_base = float(numeros[0])
                # Se o valor extraído é 0, retorna 0
                if valor_base == 0:
                    return 0.0
            except:
                pass
        
        # Multiplicadores por palavras
        multiplicador = multiplicador_k  # Começa com multiplicador do "k" se encontrado
        if "milhão" in texto_lower or "milhao" in texto_lower or "milhões" in texto_lower or "milhoes" in texto_lower:
            multiplicador = 1000000.0
        elif "mil" in texto_lower and "milhão" not in texto_lower and "milhao" not in texto_lower:
            # Verifica se não é parte de "milhão"
            multiplicador = 1000.0
        
        if valor_base is not None:
            return valor_base * multiplicador
        
        # Se não encontrou número mas encontrou palavra de quantidade
        if multiplicador > 1.0:
            # Assume 1 se não encontrou número explícito
            return multiplicador
        
        return None
    
    def _extrair_tipo_emprego(self, texto: str) -> Optional[str]:
        """Extrai tipo de emprego"""
        texto_lower = texto.lower()
        
        if "formal" in texto_lower or "clt" in texto_lower or "carteira" in texto_lower:
            return "formal"
        elif "autônomo" in texto_lower or "autonomo" in texto_lower or "pj" in texto_lower:
            return "autônomo"
        elif "desempregado" in texto_lower or "sem emprego" in texto_lower or "desempregada" in texto_lower:
            return "desempregado"
        
        return None
    
    def _extrair_numero_dependentes(self, texto: str) -> Optional[int]:
        """Extrai número de dependentes"""
        import re
        
        texto_lower = texto.lower()
        
        # Verifica se tem "3 ou mais" ou "mais de 2"
        if "3" in texto or "mais" in texto_lower or "maior" in texto_lower:
            return 3  # Representa 3+
        
        # Procura por números
        numeros = re.findall(r'\d+', texto)
        if numeros:
            try:
                num = int(numeros[0])
                return min(num, 3)  # Limita a 3 para representar 3+
            except:
                pass
        
        # Verifica palavras
        if "zero" in texto_lower or "nenhum" in texto_lower or "não tenho" in texto_lower:
            return 0
        elif "um" in texto_lower or "uma" in texto_lower:
            return 1
        elif "dois" in texto_lower or "duas" in texto_lower:
            return 2
        
        return None
    
    def _extrair_booleano(self, texto: str) -> Optional[bool]:
        """Extrai resposta sim/não"""
        texto_lower = texto.lower()
        
        if any(palavra in texto_lower for palavra in ["sim", "yes", "tenho", "possui", "tem"]):
            return True
        elif any(palavra in texto_lower for palavra in ["não", "nao", "no", "não tenho", "não possui", "não tem"]):
            return False
        
        return None
    
    def _calcular_e_atualizar_score(self) -> float:
        """Calcula novo score e atualiza no banco de dados"""
        dados = self.estado["dados_coletados"]
        
        novo_score = calcular_score(
            renda_mensal=dados["renda_mensal"],
            tipo_emprego=dados["tipo_emprego"],
            despesas_fixas=dados["despesas_fixas"],
            num_dependentes=dados["num_dependentes"],
            tem_dividas=dados["tem_dividas"]
        )
        
        # Atualiza no CSV
        cpf = str(self.cliente.get('cpf', ''))
        atualizar_score_cliente(cpf, novo_score)
        
        # Atualiza cliente local
        self.cliente['score'] = novo_score
        
        return novo_score
    
    def _verificar_encerramento(self, mensagem: str) -> bool:
        """Verifica se o usuário quer encerrar"""
        mensagem_lower = mensagem.lower().strip()
        
        # Frases específicas de encerramento/cancelamento
        frases_encerramento = [
            "encerrar", "sair", "cancelar", "desistir", "cancelar entrevista",
            "não quero continuar", "parar", "desistir da entrevista"
        ]
        
        # Verifica se a mensagem contém uma frase de encerramento
        for frase in frases_encerramento:
            if frase in mensagem_lower:
                # Se a mensagem começa ou termina com a frase, é mais provável
                if mensagem_lower.startswith(frase) or mensagem_lower.endswith(frase):
                    return True
                # Se a mensagem é curta e contém a frase, também considera
                if len(mensagem_lower.split()) <= 4 and frase in mensagem_lower:
                    return True
        
        return False
    
    def resetar(self):
        """Reseta o estado da entrevista"""
        self.estado = {
            "etapa": "inicio",
            "dados_coletados": {
                "renda_mensal": None,
                "tipo_emprego": None,
                "despesas_fixas": None,
                "num_dependentes": None,
                "tem_dividas": None
            }
        }
        self.limpar_historico()
    
    def definir_cliente(self, cliente: Dict[str, Any]):
        """Define o cliente atual"""
        self.cliente = cliente
        self.resetar()

