"""
Agente de Entrevista de Crédito - 100% LLM-Driven
O LLM decide tudo, Python só fornece as tools
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from agents.tools import get_tools_entrevista
from utils.csv_handler import obter_cliente_por_cpf


class EntrevistaAgent(BaseAgent):
    """Agente responsável por conduzir entrevista financeira e recalcular score"""
    
    SYSTEM_PROMPT = """Você está conduzindo uma entrevista de crédito para um banco digital.

DADOS DO CLIENTE:
{dados_cliente}

DADOS JÁ COLETADOS NA ENTREVISTA:
{dados_coletados}

SUAS FERRAMENTAS:
1. registrar_renda_mensal(valor) - Registra renda mensal (número)
2. registrar_tipo_emprego(tipo) - "formal", "autônomo" ou "desempregado"
3. registrar_despesas_fixas(valor) - Registra despesas (número, pode ser 0)
4. registrar_dependentes(quantidade) - Número de dependentes (0, 1, 2, 3...)
5. registrar_dividas(possui_dividas) - True ou False
6. calcular_novo_score(...) - Calcula o novo score
7. redirecionar_para_credito() - Quando cliente quer ver/solicitar limite
8. redirecionar_para_cambio() - Quando cliente quer cotação de moedas

REGRAS OBRIGATÓRIAS:
1. Quando o cliente responder, SEMPRE: chame a tool + faça a PRÓXIMA pergunta na mesma resposta
2. NUNCA deixe a resposta vazia após uma tool call
3. Verifique DADOS JÁ COLETADOS - se não é None, NÃO pergunte novamente
4. Após CADA tool call bem-sucedida, confirme brevemente e faça a próxima pergunta

MAPEAMENTO:
- "CLT", "carteira assinada" → tipo = "formal"
- "PJ", "MEI", "freelancer" → tipo = "autônomo"
- "desempregado" → tipo = "desempregado"
- "zero", "nenhum", "não tenho" (despesas) → valor = 0
- "não", "nenhum" (dependentes) → quantidade = 0
- "não" (dívidas) → possui_dividas = False
- "sim" (dívidas) → possui_dividas = True

FLUXO:
1. RENDA → registrar_renda_mensal → "Ok! E qual seu tipo de emprego?"
2. EMPREGO → registrar_tipo_emprego → "Entendi! Quais suas despesas fixas mensais?"
3. DESPESAS → registrar_despesas_fixas → "Certo! Quantos dependentes você possui?"
4. DEPENDENTES → registrar_dependentes → "Ok! Você possui alguma dívida ativa?"
5. DÍVIDAS → registrar_dividas → calcular_novo_score
6. Após calcular → "Seu novo score é X! Gostaria de solicitar um aumento de limite agora?"
7. Se cliente aceitar → use redirecionar_para_credito (SEM dizer que está transferindo)

PROIBIDO:
- NUNCA mencione "transferir", "outro agente", "área de crédito", "redirecionar"
- NUNCA deixe resposta vazia - SEMPRE confirme e faça próxima pergunta
- A transição deve ser INVISÍVEL para o cliente

Seja natural e objetivo. Responda em português do Brasil."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.cliente = None
        # Estado para rastrear dados coletados (usado apenas para o prompt)
        self.dados_entrevista = {
            "renda_mensal": None,
            "tipo_emprego": None,
            "despesas_fixas": None,
            "num_dependentes": None,
            "tem_dividas": None,
            "score_calculado": None,
            "limite_maximo": None
        }
        
        # Registra TODAS as tools da entrevista
        self.registrar_tools(get_tools_entrevista())
    
    def _formatar_dados_cliente(self) -> str:
        """Formata dados do cliente para o prompt"""
        if not self.cliente:
            return "Cliente não identificado"
        
        return f"""- Nome: {self.cliente.get('nome', 'N/A')}
- CPF: {self.cliente.get('cpf', 'N/A')}
- Limite atual: R$ {float(self.cliente.get('limite_credito', 0)):,.2f}"""
    
    def _formatar_dados_coletados(self) -> str:
        """Formata dados já coletados para o prompt"""
        dados = self.dados_entrevista
        linhas = []
        
        if dados["renda_mensal"] is not None:
            linhas.append(f"✅ Renda mensal: R$ {dados['renda_mensal']:,.2f}")
        else:
            linhas.append("❌ Renda mensal: (não coletado)")
        
        if dados["tipo_emprego"]:
            linhas.append(f"✅ Tipo de emprego: {dados['tipo_emprego']}")
        else:
            linhas.append("❌ Tipo de emprego: (não coletado)")
        
        if dados["despesas_fixas"] is not None:
            linhas.append(f"✅ Despesas fixas: R$ {dados['despesas_fixas']:,.2f}")
        else:
            linhas.append("❌ Despesas fixas: (não coletado)")
        
        if dados["num_dependentes"] is not None:
            linhas.append(f"✅ Dependentes: {dados['num_dependentes']}")
        else:
            linhas.append("❌ Dependentes: (não coletado)")
        
        if dados["tem_dividas"] is not None:
            linhas.append(f"✅ Possui dívidas: {'Sim' if dados['tem_dividas'] else 'Não'}")
        else:
            linhas.append("❌ Possui dívidas: (não coletado)")
        
        if dados["score_calculado"]:
            linhas.append(f"\n🎯 SCORE CALCULADO: {dados['score_calculado']} pontos")
            if dados["limite_maximo"]:
                linhas.append(f"💰 LIMITE MÁXIMO: R$ {dados['limite_maximo']:,.2f}")
        
        return "\n".join(linhas)
    
    def processar(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Processa mensagem - 100% via LLM e tools"""
        
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
        
        # Verifica cancelamento
        if self._verificar_encerramento(mensagem):
            return {
                "resposta": "Entendido. A entrevista foi cancelada. Posso ajudá-lo com mais alguma coisa?",
                "proximo_agente": None,
                "encerrar": False
            }
        
        try:
            # Monta prompt com contexto atual
            prompt_sistema = self.SYSTEM_PROMPT.format(
                dados_cliente=self._formatar_dados_cliente(),
                dados_coletados=self._formatar_dados_coletados()
            )
            
            # Processa via LLM com tools
            resposta_texto, tool_calls = self.processar_com_tools(
                prompt_sistema=prompt_sistema,
                mensagem_usuario=mensagem,
                contexto_debug="EntrevistaAgent.processar",
                usar_memoria=True
            )
            
            # Processa resultados das tools
            proximo_agente = None
            ultima_proxima_pergunta = None
            
            for tc in tool_calls:
                result = tc["result"]
                
                # Redirecionamentos
                if tc["name"] == "redirecionar_para_credito":
                    proximo_agente = "credito"
                elif tc["name"] == "redirecionar_para_cambio":
                    proximo_agente = "cambio"
                
                # Registros - atualiza estado local e captura próxima pergunta
                elif tc["name"] == "registrar_renda_mensal" and isinstance(result, dict) and result.get("sucesso"):
                    self.dados_entrevista["renda_mensal"] = result.get("valor")
                    ultima_proxima_pergunta = result.get("proxima_pergunta")
                    print(f"[EntrevistaAgent] ✅ Renda registrada: {result.get('valor')}")
                
                elif tc["name"] == "registrar_tipo_emprego" and isinstance(result, dict) and result.get("sucesso"):
                    self.dados_entrevista["tipo_emprego"] = result.get("valor")
                    ultima_proxima_pergunta = result.get("proxima_pergunta")
                    print(f"[EntrevistaAgent] ✅ Tipo emprego registrado: {result.get('valor')}")
                
                elif tc["name"] == "registrar_despesas_fixas" and isinstance(result, dict) and result.get("sucesso"):
                    self.dados_entrevista["despesas_fixas"] = result.get("valor")
                    ultima_proxima_pergunta = result.get("proxima_pergunta")
                    print(f"[EntrevistaAgent] ✅ Despesas registradas: {result.get('valor')}")
                
                elif tc["name"] == "registrar_dependentes" and isinstance(result, dict) and result.get("sucesso"):
                    self.dados_entrevista["num_dependentes"] = result.get("valor")
                    ultima_proxima_pergunta = result.get("proxima_pergunta")
                    print(f"[EntrevistaAgent] ✅ Dependentes registrado: {result.get('valor')}")
                
                elif tc["name"] == "registrar_dividas" and isinstance(result, dict) and result.get("sucesso"):
                    self.dados_entrevista["tem_dividas"] = result.get("valor")
                    ultima_proxima_pergunta = result.get("proxima_pergunta")
                    print(f"[EntrevistaAgent] ✅ Dívidas registrado: {result.get('valor')}")
                
                elif tc["name"] == "calcular_novo_score" and isinstance(result, dict) and result.get("sucesso"):
                    self.dados_entrevista["score_calculado"] = result.get("novo_score")
                    # Calcula limite máximo
                    self.dados_entrevista["limite_maximo"] = self._obter_limite_maximo(result.get("novo_score", 0))
                    # Atualiza cliente local
                    if self.cliente:
                        self.cliente["score"] = result.get("novo_score")
                    print(f"[EntrevistaAgent] ✅ Score calculado: {result.get('novo_score')}")
            
            # Se houve redirecionamento, não deixa resposta vazia
            if proximo_agente:
                # Não precisa de resposta - a transição deve ser invisível
                return {
                    "resposta": resposta_texto if resposta_texto else "",
                    "proximo_agente": proximo_agente,
                    "encerrar": False,
                    "score_calculado": self.dados_entrevista.get("score_calculado"),
                    "limite_maximo": self.dados_entrevista.get("limite_maximo")
                }
            
            # Resposta final - usa resposta da LLM, ou fallback inteligente
            if resposta_texto:
                resposta_final = resposta_texto
            elif ultima_proxima_pergunta:
                # Se a LLM não gerou texto mas houve tool call, usa a próxima pergunta
                resposta_final = f"Registrado! {ultima_proxima_pergunta}"
            else:
                resposta_final = "Entendi! Como posso ajudar?"
            
            self.adicionar_a_memoria(mensagem, resposta_final)
            
            return {
                "resposta": resposta_final,
                "proximo_agente": None,
                "encerrar": False,
                "score_calculado": self.dados_entrevista.get("score_calculado"),
                "limite_maximo": self.dados_entrevista.get("limite_maximo")
            }
            
        except Exception as e:
            print(f"[EntrevistaAgent] Erro: {e}")
            return {
                "resposta": f"Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
                "proximo_agente": None,
                "encerrar": False,
                "erro": str(e)
            }
    
    def _obter_limite_maximo(self, score: float) -> float:
        """Obtém limite máximo permitido para o score"""
        import pandas as pd
        try:
            df = pd.read_csv("data/score_limite.csv")
            for _, row in df.iterrows():
                if row['score_minimo'] <= score <= row['score_maximo']:
                    return float(row['limite_maximo'])
        except:
            pass
        
        # Fallback
        if score >= 800:
            return 500000.0
        elif score >= 600:
            return 200000.0
        elif score >= 400:
            return 50000.0
        elif score >= 200:
            return 20000.0
        else:
            return 5000.0
    
    def _verificar_encerramento(self, mensagem: str) -> bool:
        """Verifica se quer cancelar"""
        msg = mensagem.lower()
        return any(p in msg for p in ["cancelar entrevista", "desistir da entrevista", "parar entrevista"])
    
    def resetar(self, limpar_memoria_compartilhada: bool = False):
        """Reseta o estado do agente (mas preserva memória por padrão)"""
        self.dados_entrevista = {
            "renda_mensal": None,
            "tipo_emprego": None,
            "despesas_fixas": None,
            "num_dependentes": None,
            "tem_dividas": None,
            "score_calculado": None,
            "limite_maximo": None
        }
        # Só limpa memória se explicitamente solicitado
        if limpar_memoria_compartilhada:
            self.limpar_memoria()
    
    def definir_cliente(self, cliente: Dict[str, Any]):
        """Define o cliente (preserva memória para manter contexto)"""
        self.cliente = cliente
        # Reseta dados da entrevista mas NÃO limpa a memória compartilhada
        self.resetar(limpar_memoria_compartilhada=False)
