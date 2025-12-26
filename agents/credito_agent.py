"""
Agente de Crédito - Consulta e solicitação de aumento de limite
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from utils.csv_handler import (
    obter_cliente_por_cpf,
    verificar_limite_permitido,
    registrar_solicitacao_aumento
)
from utils.saudacoes import detectar_saudacao, gerar_resposta_saudacao, extrair_mensagem_sem_saudacao


class CreditoAgent(BaseAgent):
    """Agente responsável por consultas de crédito e solicitações de aumento"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.cliente = None
        self.entrevista_oferecida = False  # Rastreia se ofereceu entrevista na última interação
    
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mensagem relacionada a crédito
        
        Returns:
            Dict com resposta e informações de controle
        """
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
        
        # Detecta saudações primeiro
        saudacao_detectada = detectar_saudacao(mensagem)
        
        # Se há saudação, responde adequadamente e processa o resto da mensagem
        if saudacao_detectada:
            resposta_saudacao = gerar_resposta_saudacao(saudacao_detectada)
            mensagem_sem_saudacao = extrair_mensagem_sem_saudacao(mensagem)
            
            # Se após remover saudação não sobrou nada, apenas responde a saudação
            if not mensagem_sem_saudacao.strip():
                self.adicionar_mensagem(mensagem, "human")
                resposta = f"{resposta_saudacao} Como posso ajudá-lo com questões de crédito?"
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
        limite_atual = float(self.cliente.get('limite_credito', 0))
        
        # Verifica se está aceitando entrevista oferecida
        if self.entrevista_oferecida and self._aceitou_entrevista(mensagem):
            self.entrevista_oferecida = False
            return {
                "resposta": "",
                "proximo_agente": "entrevista",
                "encerrar": False
            }
        
        prompt = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados:
- Agente de Crédito (você): Consulta de limite, solicitação de aumento de limite
- Agente de Câmbio: Consulta de cotações de moedas (dólar, euro, libra, etc.)
- Agente de Entrevista: Entrevista financeira para atualizar score de crédito
- Agente de Triagem: Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
Você é o Agente de Crédito, especializado em questões relacionadas a limite de crédito e solicitações de aumento.

DADOS DO CLIENTE:
- Limite atual: R$ {limite_atual:,.2f}

Mensagem do cliente: "{mensagem}"

SISTEMA DE COMANDOS:
Você pode responder de duas formas:

1. TEXTO NORMAL: Se você responder com texto normal, esse texto será passado diretamente para o cliente.

2. COMANDOS: Se você precisar chamar uma função, responda APENAS com o comando:
   - CAMBIO → Redireciona para agente de câmbio
   - ENTREVISTA → Redireciona para agente de entrevista
   - CONSULTAR_LIMITE → Consulta o limite atual do cliente
   - SOLICITAR_AUMENTO:valor → Processa solicitação de aumento (ex: SOLICITAR_AUMENTO:10000)

INSTRUÇÕES:
1. PRIMEIRO: Verifique se a mensagem é sobre crédito ou outro assunto
   - Se for sobre cotação de moedas → use comando CAMBIO
   - Se for sobre entrevista, score → use comando ENTREVISTA
   - Se for sobre limite ou crédito → continue análise

2. SE FOR SOBRE CRÉDITO:
   - Se quer saber quanto tem de limite → use comando CONSULTAR_LIMITE
   - Se menciona um valor numérico maior que o limite atual → use comando SOLICITAR_AUMENTO:valor
   - Se não está claro → responda com texto pedindo esclarecimento

3. SE NÃO FOR SOBRE CRÉDITO: Use o comando de redirecionamento apropriado (CAMBIO ou ENTREVISTA)

IMPORTANTE: 
- Se você usar um comando (ex: CONSULTAR_LIMITE), o sistema executará a função e retornará o resultado para você construir uma resposta natural
- Se você responder com texto, esse texto será passado diretamente para o cliente
- Seja natural e conversacional quando responder com texto"""

        try:
            resposta_final, comando, dados_comando = self.processar_com_comandos(
                prompt, 
                contexto_adicional="CreditoAgent.processar",
                usar_historico=False  # Não usa histórico para interpretar intenção - prompt específico
            )
            
            # Se retornou um comando, processa
            if comando:
                # Comandos de redirecionamento
                if comando == "CAMBIO":
                    return {
                        "resposta": "",
                        "proximo_agente": "cambio",
                        "encerrar": False
                    }
                elif comando == "ENTREVISTA":
                    self.entrevista_oferecida = False
                    return {
                        "resposta": "",
                        "proximo_agente": "entrevista",
                        "encerrar": False
                    }
                # Comando de consultar limite
                elif comando == "CONSULTAR_LIMITE":
                    resultado = f"Limite atual: R$ {limite_atual:,.2f}"
                    prompt_final = f"""O cliente perguntou sobre seu limite de crédito. Você chamou a função CONSULTAR_LIMITE e obteve:

{resultado}

Agora construa uma resposta natural e conversacional para o cliente apresentando essa informação de forma amigável."""
                    resposta = self.gerar_resposta(prompt_final, contexto_adicional="CreditoAgent.processar - Resposta final", usar_historico=False)
                    self.entrevista_oferecida = False
                    self.adicionar_mensagem(resposta, "ai")
                    return {
                        "resposta": resposta,
                        "proximo_agente": None,
                        "encerrar": False
                    }
                # Comando de solicitar aumento
                elif comando == "SOLICITAR_AUMENTO":
                    if dados_comando and "dados" in dados_comando:
                        # Tenta extrair valor dos dados ou da mensagem original
                        valor_str = dados_comando["dados"]
                        valor = self._extrair_valor(valor_str) or self._extrair_valor(mensagem)
                    else:
                        valor = self._extrair_valor(mensagem)
                    
                    if valor and valor > limite_atual:
                        resposta_func, status, redirecionar = self._processar_solicitacao_aumento(valor)
                        self.entrevista_oferecida = redirecionar
                        
                        # Retorna resultado para IA construir resposta final
                        prompt_final = f"""O cliente solicitou aumento de limite. Você chamou a função SOLICITAR_AUMENTO e obteve:

{resposta_func}

Agora construa uma resposta natural e conversacional para o cliente baseada nesse resultado."""
                        resposta = self.gerar_resposta(prompt_final, contexto_adicional="CreditoAgent.processar - Resposta final", usar_historico=False)
                        
                        self.adicionar_mensagem(resposta, "ai")
                        return {
                            "resposta": resposta,
                            "proximo_agente": "entrevista" if redirecionar else None,
                            "encerrar": False,
                            "status_solicitacao": status
                        }
                    else:
                        resposta = f"Desculpe, não consegui identificar o valor do aumento solicitado. Por favor, informe o valor desejado (ex: 10000 ou 10 mil)."
                        self.entrevista_oferecida = False
                else:
                    # Comando desconhecido, usa resposta direta
                    resposta = resposta_final or "Como posso ajudá-lo com questões de crédito?"
                    self.entrevista_oferecida = False
            else:
                # Resposta normal da IA
                # Verifica se a resposta não é um comando não processado
                resposta_stripped = resposta_final.strip() if resposta_final else ""
                # Se parece ser um comando mas não foi processado, pede esclarecimento
                if resposta_stripped.isupper() and len(resposta_stripped.split()) == 1:
                    resposta = "Desculpe, não consegui processar sua solicitação. Poderia reformular sua pergunta?"
                elif ":" in resposta_stripped and resposta_stripped.split(":")[0].strip().isupper():
                    resposta = "Desculpe, não consegui processar sua solicitação. Poderia reformular sua pergunta?"
                else:
                    resposta = resposta_final
                self.entrevista_oferecida = False
                    
        except Exception as e:
            print(f"ERRO ao usar LLM para interpretar mensagem: {e}")
            raise Exception(f"Falha na interpretação da IA: {str(e)}")
        
        self.adicionar_mensagem(resposta, "ai")
        
        return {
            "resposta": resposta,
            "proximo_agente": None,
            "encerrar": False
        }
    
    def _consultar_limite(self) -> str:
        """Consulta limite atual do cliente"""
        limite = float(self.cliente.get('limite_credito', 0))
        # Score não é mencionado na documentação como informação a ser exibida ao cliente
        # Removido para manter sigilo (boa prática bancária)
        return f"Seu limite de crédito atual é de R$ {limite:,.2f}. Posso ajudá-lo com alguma solicitação de aumento?"
    
    def _processar_solicitacao_aumento(self, novo_limite: float) -> tuple:
        """
        Processa solicitação de aumento de limite
        
        Returns:
            (resposta, status, redirecionar_entrevista)
        """
        limite_atual = float(self.cliente.get('limite_credito', 0))
        score = float(self.cliente.get('score', 0))
        cpf = str(self.cliente.get('cpf', ''))
        
        # Verifica se o limite solicitado é permitido
        permitido = verificar_limite_permitido(score, novo_limite)
        
        if permitido:
            status = "aprovado"
            resposta = f"Excelente notícia! Sua solicitação de aumento de limite de R$ {limite_atual:,.2f} para R$ {novo_limite:,.2f} foi APROVADA. O novo limite já está disponível para uso."
        else:
            status = "rejeitado"
            # Não menciona o score específico ao cliente (sigilo)
            resposta = f"Infelizmente, sua solicitação de aumento de limite para R$ {novo_limite:,.2f} não pôde ser aprovada no momento com base na análise do seu perfil de crédito. "
            resposta += "No entanto, posso oferecer uma entrevista de crédito para tentarmos melhorar sua avaliação. Gostaria de fazer a entrevista?"
        
        # Registra solicitação
        try:
            registrar_solicitacao_aumento(cpf, limite_atual, novo_limite, status)
        except Exception as e:
            resposta += f"\n\n(Nota: Houve um problema ao registrar a solicitação: {str(e)})"
        
        redirecionar = (status == "rejeitado")
        
        return resposta, status, redirecionar
    
    def _extrair_valor(self, texto: str) -> Optional[float]:
        """Extrai valor numérico do texto, incluindo palavras como 'milhão', 'mil'"""
        import re
        
        texto_lower = texto.lower()
        
        # Remove pontos de milhar e substitui vírgula por ponto
        texto_limpo = texto.replace('.', '').replace(',', '.')
        
        # Procura por números
        numeros = re.findall(r'\d+\.?\d*', texto_limpo)
        
        valor_base = None
        if numeros:
            try:
                valor_base = float(numeros[0])
            except:
                pass
        
        # Multiplicadores por palavras
        multiplicador = 1.0
        if "milhão" in texto_lower or "milhao" in texto_lower or "milhões" in texto_lower or "milhoes" in texto_lower:
            multiplicador = 1000000.0
        elif "mil" in texto_lower and "milhão" not in texto_lower and "milhao" not in texto_lower:
            # Verifica se não é parte de "milhão"
            multiplicador = 1000.0
        
        if valor_base:
            return valor_base * multiplicador
        
        # Se não encontrou número mas encontrou palavra de quantidade
        if multiplicador > 1.0:
            # Assume 1 se não encontrou número explícito
            return multiplicador
        
        return None
    
    def _identificar_intencao(self, mensagem: str) -> str:
        """
        DEPRECATED: Esta função não é mais usada como método principal.
        Mantida apenas para compatibilidade. O LLM agora é usado diretamente no processar().
        """
        # Esta função não é mais usada - o LLM interpreta diretamente
        return "outro"
    
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
        # Isso evita que "não, eu quero..." seja interpretado como encerramento
        if mensagem_lower in ["não", "nao", "n"]:
            return False  # "Não" sozinho não é encerramento, pode ser negação/clarificação
        
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
    
    def _aceitou_entrevista(self, mensagem: str) -> bool:
        """Verifica se o usuário aceitou a entrevista oferecida usando LLM"""
        try:
            prompt = f"""Você ofereceu uma entrevista de crédito ao cliente para melhorar a avaliação dele. Ele respondeu: "{mensagem}"

IMPORTANTE: 
- Se a mensagem é sobre fazer a ENTREVISTA (ex: "sim quero fazer", "vamos fazer a entrevista", "ok faço") → responda "SIM"
- Se a mensagem é sobre LIMITE, AUMENTO, CRÉDITO ou qualquer outra coisa que NÃO seja sobre fazer entrevista → responda "NÃO"
- Se a mensagem menciona valores, limites, aumentos → é NÃO (não é sobre entrevista)

Determine se o cliente está aceitando fazer a ENTREVISTA especificamente. Se ele disse "sim quero fazer a entrevista", "vamos fazer", "ok faço a entrevista", ou qualquer forma de aceitação EXPLÍCITA da entrevista, responda "SIM".
Se ele disse "não", "não quero", ou se a mensagem é sobre outra coisa (limite, aumento, etc.), responda "NÃO".

Responda APENAS com "SIM" ou "NÃO"."""

            resposta_llm = self.gerar_resposta(prompt, contexto_adicional="CreditoAgent._aceitou_entrevista", usar_historico=False).upper().strip()
            return "SIM" in resposta_llm
        except Exception as e:
            # FALLBACK COMENTADO: Mantido apenas para referência futura
            # Se quiser reativar em produção, descomente abaixo
            # mensagem_lower = mensagem.lower().strip()
            # return mensagem_lower in ["sim", "yes", "ok", "okay", "quero", "vamos"]
            
            # Se o LLM falhar, retorna erro explícito para debug
            print(f"ERRO ao usar LLM para verificar aceitação de entrevista: {e}")
            raise Exception(f"Falha na interpretação da IA para verificar aceitação: {str(e)}")
    
    def _quer_fazer_entrevista(self, mensagem: str) -> bool:
        """Verifica se o usuário quer fazer entrevista usando LLM como método principal"""
        try:
            prompt = f"""Analise a seguinte mensagem e determine se o cliente quer fazer uma ENTREVISTA DE CRÉDITO.

Mensagem: "{mensagem}"

Uma entrevista de crédito é quando o cliente quer atualizar/melhorar seu score através de perguntas sobre renda, despesas, etc.

Responda APENAS com "SIM" se quer fazer entrevista, ou "NÃO" caso contrário."""

            resposta_llm = self.gerar_resposta(prompt, contexto_adicional="CreditoAgent._quer_fazer_entrevista").upper().strip()
            return "SIM" in resposta_llm or "ENTREVISTA" in resposta_llm
        except Exception as e:
            # FALLBACK COMENTADO: Mantido apenas para referência futura
            # Se quiser reativar em produção, descomente abaixo
            # return False
            
            # Se o LLM falhar, retorna erro explícito para debug
            print(f"ERRO ao usar LLM para verificar se quer fazer entrevista: {e}")
            raise Exception(f"Falha na interpretação da IA: {str(e)}")
    
    def _identificar_necessidade_outro_agente(self, mensagem: str) -> Optional[str]:
        """Identifica se o usuário quer algo fora do escopo de crédito usando LLM como método principal"""
        try:
            prompt = f"""CONTEXTO DO SISTEMA:
Você faz parte de um sistema bancário com múltiplos agentes especializados. Cada agente tem um escopo específico:
- Agente de Crédito (você): Consulta de limite, solicitação de aumento de limite
- Agente de Câmbio: Consulta de cotações de moedas (dólar, euro, libra, etc.)
- Agente de Entrevista: Entrevista financeira para atualizar score de crédito
- Agente de Triagem: Autenticação e direcionamento inicial

SUA RESPONSABILIDADE:
Você é o Agente de Crédito, especializado APENAS em questões relacionadas a limite de crédito e solicitações de aumento.

Mensagem do cliente: "{mensagem}"

ANÁLISE NECESSÁRIA:
Determine se a mensagem do cliente é sobre:
1. CÂMBIO/MOEDAS: Cotação de moedas (dólar, euro, libra, etc.), taxa de câmbio → NÃO é sua responsabilidade, redirecione para Agente de Câmbio
2. ENTREVISTA: Entrevista de crédito, atualizar score, melhorar avaliação → NÃO é sua responsabilidade, redirecione para Agente de Entrevista
3. CRÉDITO: Consulta de limite, aumento de limite, crédito → É sua responsabilidade, mantenha no agente atual
4. OUTRO: Qualquer outra coisa → Mantenha no agente atual

INSTRUÇÕES:
- Se a mensagem é sobre cotação de moedas → responda "cambio"
- Se a mensagem é sobre entrevista ou score → responda "entrevista"
- Se a mensagem é sobre limite ou crédito → responda "credito"
- Se a mensagem não é sobre nenhum dos acima → responda "outro"

IMPORTANTE: 
- Se o cliente perguntar "quanto é o dólar" ou "cotação do euro" → é CÂMBIO
- Se o cliente perguntar "quanto é meu limite" ou "aumentar limite" → é CRÉDITO (sua responsabilidade)
- Se o cliente perguntar sobre entrevista ou atualizar score → é ENTREVISTA

Responda APENAS com uma palavra: cambio, entrevista, credito, ou outro"""

            resposta_llm = self.gerar_resposta(prompt, contexto_adicional="CreditoAgent._identificar_necessidade_outro_agente").lower().strip()
            
            # Extrai a intenção da resposta do LLM
            if "cambio" in resposta_llm or "câmbio" in resposta_llm or "moeda" in resposta_llm:
                return "cambio"
            elif "entrevista" in resposta_llm:
                return "entrevista"
            elif "credito" in resposta_llm or "crédito" in resposta_llm:
                return None  # É crédito, mantém no agente atual
            else:
                return None  # Não identificou necessidade específica
                
        except Exception as e:
            # FALLBACK COMENTADO: Mantido apenas para referência futura
            # Se quiser reativar em produção, descomente abaixo
            # mensagem_lower = mensagem.lower()
            # if any(palavra in mensagem_lower for palavra in ["cotação", "cotacao", "câmbio", "cambio", "dólar", "dolar", "euro"]) and "limite" not in mensagem_lower:
            #     return "cambio"
            # return None
            
            # Se o LLM falhar, retorna erro explícito para debug
            print(f"ERRO ao usar LLM para identificar necessidade de outro agente: {e}")
            raise Exception(f"Falha na interpretação da IA para identificar necessidade: {str(e)}")
    
    def _gerar_resposta_esclarecimento(self, mensagem: str, limite_atual: float) -> str:
        """Gera resposta pedindo esclarecimento de forma natural e contextual"""
        try:
            prompt = f"""Você é um agente bancário especializado em crédito. O cliente tem limite atual de R$ {limite_atual:,.2f}.

O cliente disse: "{mensagem}"

Você não conseguiu entender claramente o que o cliente precisa.

IMPORTANTE:
- NÃO diga "Entendi" se você não entendeu
- NÃO diga "Como posso ajudá-lo?" de forma genérica
- Seja específico: mencione o que o cliente disse e peça esclarecimento
- Seja natural e conversacional, como uma pessoa real
- Se a mensagem parece ser uma saudação, responda adequadamente
- Se a mensagem parece ser sobre crédito mas não está claro, ofereça opções específicas

Responda de forma natural e específica, mencionando o que o cliente disse e pedindo esclarecimento sobre o que ele precisa relacionado a crédito."""

            resposta = self.gerar_resposta(prompt, contexto_adicional="CreditoAgent._gerar_resposta_esclarecimento")
            return resposta
        except:
            # Fallback: resposta específica baseada na mensagem
            return f"Desculpe, não consegui entender exatamente o que você precisa quando disse '{mensagem}'. Poderia me explicar melhor? Posso ajudá-lo a consultar seu limite atual (R$ {limite_atual:,.2f}) ou solicitar um aumento de limite."
    
    def definir_cliente(self, cliente: Dict[str, Any]):
        """Define o cliente atual"""
        self.cliente = cliente
        self.entrevista_oferecida = False  # Reseta ao definir novo cliente

