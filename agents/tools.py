"""
Definição de Tools para os agentes - Sistema de Function Calling
"""
from langchain_core.tools import tool
from typing import Optional
from utils.csv_handler import (
    obter_cliente_por_cpf,
    verificar_limite_permitido,
    registrar_solicitacao_aumento,
    atualizar_score_cliente,
    atualizar_limite_cliente
)
from utils.cotacao_api import buscar_cotacao_moeda
from utils.score_calculator import calcular_score


# ==================== TOOL DE RESPOSTA (Chain-of-Thought estruturado) ====================

@tool
def responder_usuario(raciocinio: str, resposta: str) -> dict:
    """
    Envia uma resposta ao usuário após raciocinar sobre a situação.
    
    Args:
        raciocinio: Pensamento interno sobre o que fazer (não mostrado ao usuário)
        resposta: Texto final para o usuário
    """
    return {
        "tipo": "resposta_usuario",
        "raciocinio": raciocinio,
        "resposta": resposta
    }


# ==================== TOOLS DE NAVEGAÇÃO (usadas por todos os agentes) ====================

@tool
def redirecionar_para_credito() -> dict:
    """
    Redireciona o cliente para o Agente de Crédito.
    Use quando o cliente quer:
    - Consultar limite de crédito
    - Solicitar aumento de limite
    - Questões sobre cartão de crédito
    """
    return {"acao": "redirecionar", "agente": "credito"}


@tool
def redirecionar_para_cambio() -> dict:
    """
    Redireciona o cliente para o Agente de Câmbio.
    Use quando o cliente quer:
    - Consultar cotação de moedas (dólar, euro, libra, etc.)
    - Saber taxa de câmbio
    """
    return {"acao": "redirecionar", "agente": "cambio"}


@tool
def redirecionar_para_entrevista() -> dict:
    """
    Redireciona o cliente para o Agente de Entrevista.
    Use quando o cliente quer:
    - Fazer entrevista de crédito
    - Atualizar score
    - Melhorar avaliação de crédito
    """
    return {"acao": "redirecionar", "agente": "entrevista"}


@tool
def encerrar_conversa(mensagem_despedida: str = "Foi um prazer ajudá-lo! Até logo!") -> dict:
    """
    Encerra a conversa com o cliente.
    Use quando:
    - O cliente quiser sair (disser "tchau", "até logo", "encerrar", "sair", etc.)
    - O cliente agradecer e se despedir
    
    Args:
        mensagem_despedida: Mensagem de despedida personalizada (opcional)
    """
    return {"acao": "encerrar", "mensagem": mensagem_despedida}


# ==================== TOOLS DO AGENTE DE CRÉDITO ====================

@tool
def consultar_limite_credito(cpf: str) -> dict:
    """
    Consulta o limite de crédito atual do cliente.
    
    Args:
        cpf: CPF do cliente (11 dígitos)
    
    Returns:
        Informações do limite de crédito
    """
    cliente = obter_cliente_por_cpf(cpf)
    if cliente:
        limite = float(cliente.get('limite_credito', 0))
        return {
            "sucesso": True,
            "limite_atual": limite,
            "limite_formatado": f"R$ {limite:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        }
    return {"sucesso": False, "erro": "Cliente não encontrado"}


@tool
def solicitar_aumento_limite(cpf: str, novo_limite: float) -> dict:
    """
    Processa solicitação de aumento de limite de crédito.
    
    Args:
        cpf: CPF do cliente (11 dígitos)
        novo_limite: Valor do novo limite desejado em reais
    
    Returns:
        Resultado da solicitação (aprovado, rejeitado, ou pendente entrevista)
    """
    cliente = obter_cliente_por_cpf(cpf)
    if not cliente:
        return {"sucesso": False, "erro": "Cliente não encontrado"}
    
    limite_atual = float(cliente.get('limite_credito', 0))
    score = float(cliente.get('score', 0))
    
    # Verifica se o limite solicitado é permitido pelo score
    permitido = verificar_limite_permitido(score, novo_limite)
    
    if permitido:
        status = "aprovado"
        # ATUALIZA O LIMITE NO CSV quando aprovado!
        try:
            atualizar_limite_cliente(cpf, novo_limite)
            mensagem = f"Solicitação APROVADA! Seu novo limite de R$ {novo_limite:,.2f} já está ativo."
        except Exception as e:
            mensagem = f"Solicitação aprovada, mas houve um erro ao atualizar: {str(e)}"
    else:
        status = "rejeitado_sugerir_entrevista"
        mensagem = f"Limite de R$ {novo_limite:,.2f} não aprovado com o perfil atual. Sugerimos uma entrevista de crédito para melhorar a avaliação."
    
    # Registra solicitação no histórico
    try:
        registrar_solicitacao_aumento(cpf, limite_atual, novo_limite, status.replace("_sugerir_entrevista", ""))
    except Exception as e:
        pass  # Ignora erros de registro
    
    return {
        "sucesso": True,
        "status": status,
        "limite_anterior": limite_atual,
        "limite_novo": novo_limite if permitido else limite_atual,
        "limite_solicitado": novo_limite,
        "mensagem": mensagem,
        "sugerir_entrevista": status == "rejeitado_sugerir_entrevista"
    }


# ==================== TOOLS DO AGENTE DE CÂMBIO ====================

@tool
def consultar_cotacao_moeda(moeda: str) -> dict:
    """
    Consulta a cotação de uma moeda estrangeira em relação ao Real (BRL).
    
    Args:
        moeda: Código da moeda (USD, EUR, GBP, JPY, CHF, CAD, AUD, CNY, ARS, CLP, MXN)
              ou nome da moeda (dólar, euro, libra, iene, franco, yuan, peso)
    
    Returns:
        Cotação atual da moeda
    """
    # Mapeia nomes para códigos
    mapeamento = {
        "dolar": "USD", "dólar": "USD", "dollar": "USD",
        "euro": "EUR",
        "libra": "GBP",
        "iene": "JPY", "yen": "JPY",
        "franco": "CHF",
        "dolar canadense": "CAD", "dólar canadense": "CAD",
        "dolar australiano": "AUD", "dólar australiano": "AUD",
        "yuan": "CNY",
        "peso argentino": "ARS", "argentino": "ARS",
        "peso chileno": "CLP", "chileno": "CLP",
        "peso mexicano": "MXN", "mexicano": "MXN",
    }
    
    moeda_upper = moeda.upper().strip()
    moeda_lower = moeda.lower().strip()
    
    # Tenta código direto
    if moeda_upper in ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "ARS", "CLP", "MXN"]:
        codigo = moeda_upper
    # Tenta mapeamento por nome
    elif moeda_lower in mapeamento:
        codigo = mapeamento[moeda_lower]
    else:
        # Tenta buscar parcialmente
        codigo = "USD"  # Default
        for nome, cod in mapeamento.items():
            if nome in moeda_lower:
                codigo = cod
                break
    
    # Busca cotação
    cotacao = buscar_cotacao_moeda(codigo)
    
    if cotacao.get("sucesso"):
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
        }.get(codigo, codigo)
        
        return {
            "sucesso": True,
            "moeda": codigo,
            "nome": nome_moeda,
            "valor_compra": cotacao.get("valor_compra"),
            "valor_venda": cotacao.get("valor_venda"),
            "valor_medio": cotacao.get("valor_medio", cotacao.get("valor_compra"))
        }
    
    return {"sucesso": False, "erro": cotacao.get("erro", "Erro ao buscar cotação")}


# ==================== TOOLS DO AGENTE DE ENTREVISTA ====================

@tool
def registrar_renda_mensal(valor: float) -> dict:
    """
    Registra a renda mensal informada pelo cliente na entrevista.
    
    Args:
        valor: Valor da renda mensal em reais (ex: 5000.0, 250000.0)
    
    Returns:
        Confirmação do registro
    """
    if valor < 0:
        return {"sucesso": False, "erro": "Valor inválido"}
    
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return {
        "sucesso": True,
        "campo": "renda_mensal",
        "valor": valor,
        "valor_formatado": valor_formatado,
        "proxima_pergunta": "Qual é o seu tipo de emprego? (formal/CLT, autônomo/PJ, ou desempregado)"
    }


@tool
def registrar_tipo_emprego(tipo: str) -> dict:
    """
    Registra o tipo de emprego do cliente na entrevista.
    
    Args:
        tipo: Tipo de emprego (formal, autônomo, desempregado)
    
    Returns:
        Confirmação do registro
    """
    tipo_lower = tipo.lower().strip()
    
    if "formal" in tipo_lower or "clt" in tipo_lower or "carteira" in tipo_lower:
        tipo_normalizado = "formal"
    elif "autônomo" in tipo_lower or "autonomo" in tipo_lower or "pj" in tipo_lower or "mei" in tipo_lower:
        tipo_normalizado = "autônomo"
    elif "desempregado" in tipo_lower or "sem emprego" in tipo_lower:
        tipo_normalizado = "desempregado"
    else:
        return {"sucesso": False, "erro": "Tipo não reconhecido. Informe: formal, autônomo ou desempregado"}
    
    return {
        "sucesso": True,
        "campo": "tipo_emprego",
        "valor": tipo_normalizado,
        "proxima_pergunta": "Qual o valor das suas despesas fixas mensais? (aluguel, contas, etc.)"
    }


@tool
def registrar_despesas_fixas(valor: float) -> dict:
    """
    Registra o valor das despesas fixas mensais do cliente.
    
    Args:
        valor: Valor das despesas fixas em reais (ex: 2000.0, pode ser 0.0)
    
    Returns:
        Confirmação do registro
    """
    if valor < 0:
        return {"sucesso": False, "erro": "Valor inválido"}
    
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return {
        "sucesso": True,
        "campo": "despesas_fixas",
        "valor": valor,
        "valor_formatado": valor_formatado,
        "proxima_pergunta": "Quantos dependentes você possui? (0, 1, 2, 3 ou mais)"
    }


@tool
def registrar_dependentes(quantidade: int) -> dict:
    """
    Registra a quantidade de dependentes do cliente.
    
    Args:
        quantidade: Número de dependentes (0, 1, 2, 3+)
    
    Returns:
        Confirmação do registro
    """
    if quantidade < 0:
        return {"sucesso": False, "erro": "Quantidade inválida"}
    
    # Limita a 3 para representar 3+
    quantidade_normalizada = min(quantidade, 3)
    
    return {
        "sucesso": True,
        "campo": "num_dependentes",
        "valor": quantidade_normalizada,
        "proxima_pergunta": "Você possui dívidas ativas? (sim ou não)"
    }


@tool
def registrar_dividas(possui_dividas: bool) -> dict:
    """
    Registra se o cliente possui dívidas ativas.
    
    Args:
        possui_dividas: True se possui dívidas, False caso contrário
    
    Returns:
        Confirmação do registro
    """
    return {
        "sucesso": True,
        "campo": "tem_dividas",
        "valor": possui_dividas,
        "proxima_pergunta": None,  # Última pergunta
        "entrevista_completa": True
    }


@tool  
def calcular_novo_score(
    cpf: str,
    renda_mensal: float,
    tipo_emprego: str,
    despesas_fixas: float,
    num_dependentes: int,
    tem_dividas: bool
) -> dict:
    """
    Calcula e atualiza o score do cliente com base nos dados da entrevista.
    
    Args:
        cpf: CPF do cliente
        renda_mensal: Renda mensal em reais
        tipo_emprego: Tipo de emprego (formal, autônomo, desempregado)
        despesas_fixas: Despesas fixas mensais em reais
        num_dependentes: Número de dependentes (0-3+)
        tem_dividas: Se possui dívidas ativas
    
    Returns:
        Novo score calculado
    """
    # Calcula novo score
    novo_score = calcular_score(
        renda_mensal=renda_mensal,
        tipo_emprego=tipo_emprego,
        despesas_fixas=despesas_fixas,
        num_dependentes=num_dependentes,
        tem_dividas=tem_dividas
    )
    
    # Atualiza no CSV
    try:
        atualizar_score_cliente(cpf, novo_score)
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao atualizar score: {str(e)}"}
    
    return {
        "sucesso": True,
        "novo_score": novo_score,
        "mensagem": "Score atualizado com sucesso! Agora você pode solicitar um novo aumento de limite."
    }


# ==================== TOOLS DO AGENTE DE TRIAGEM ====================

@tool
def validar_cpf(cpf: str) -> dict:
    """
    Valida e extrai CPF da mensagem do cliente.
    
    Args:
        cpf: CPF informado (pode ter formatação)
    
    Returns:
        CPF validado ou erro
    """
    import re
    
    # Remove tudo que não é número
    numeros = re.sub(r'\D', '', cpf)
    
    if len(numeros) == 11:
        return {
            "sucesso": True,
            "cpf": numeros,
            "cpf_formatado": f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
        }
    
    return {"sucesso": False, "erro": "CPF inválido. Deve conter 11 dígitos."}


@tool
def validar_data_nascimento(data: str) -> dict:
    """
    Valida e normaliza data de nascimento.
    Aceita vários formatos: DD/MM/AAAA, AAAA-MM-DD, "15 de maio de 1990", etc.
    
    Args:
        data: Data informada em qualquer formato
    
    Returns:
        Data normalizada (AAAA-MM-DD) ou erro
    """
    import re
    from datetime import datetime
    
    # Mapeamento de meses em português para números
    meses_pt = {
        'janeiro': '01', 'jan': '01',
        'fevereiro': '02', 'fev': '02',
        'março': '03', 'mar': '03', 'marco': '03',
        'abril': '04', 'abr': '04',
        'maio': '05', 'mai': '05',
        'junho': '06', 'jun': '06',
        'julho': '07', 'jul': '07',
        'agosto': '08', 'ago': '08',
        'setembro': '09', 'set': '09',
        'outubro': '10', 'out': '10',
        'novembro': '11', 'nov': '11',
        'dezembro': '12', 'dez': '12'
    }
    
    data_lower = data.lower().strip()
    
    # Tenta formato DD/MM/AAAA
    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', data)
    if match:
        dia, mes, ano = match.groups()
        try:
            datetime(int(ano), int(mes), int(dia))
            return {"sucesso": True, "data": f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"}
        except:
            pass
    
    # Tenta formato AAAA-MM-DD
    match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', data)
    if match:
        ano, mes, dia = match.groups()
        try:
            datetime(int(ano), int(mes), int(dia))
            return {"sucesso": True, "data": f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"}
        except:
            pass
    
    # Tenta formato "15 de maio de 1990" ou "15 maio 1990"
    match = re.search(r'(\d{1,2})\s*(?:de\s+)?(\w+)\s*(?:de\s+)?(\d{4})', data_lower)
    if match:
        dia, mes_texto, ano = match.groups()
        if mes_texto in meses_pt:
            mes = meses_pt[mes_texto]
            try:
                datetime(int(ano), int(mes), int(dia))
                return {"sucesso": True, "data": f"{ano}-{mes}-{dia.zfill(2)}"}
            except:
                pass
    
    # Tenta formato DD-MM-AAAA
    match = re.search(r'(\d{1,2})-(\d{1,2})-(\d{4})', data)
    if match:
        dia, mes, ano = match.groups()
        try:
            datetime(int(ano), int(mes), int(dia))
            return {"sucesso": True, "data": f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"}
        except:
            pass
    
    return {"sucesso": False, "erro": "Data inválida. Tente formatos como: 15/05/1990, 15 de maio de 1990, ou 1990-05-15."}


@tool
def autenticar_cliente_tool(cpf: str, data_nascimento: str) -> dict:
    """
    Autentica cliente com CPF e data de nascimento.
    
    Args:
        cpf: CPF do cliente (11 dígitos, apenas números)
        data_nascimento: Data de nascimento (AAAA-MM-DD)
    
    Returns:
        Dados do cliente se autenticado, erro caso contrário
    """
    from utils.csv_handler import autenticar_cliente
    
    cliente = autenticar_cliente(cpf, data_nascimento)
    
    if cliente:
        return {
            "sucesso": True,
            "autenticado": True,
            "cliente": {
                "nome": cliente.get("nome"),
                "cpf": cliente.get("cpf"),
                "limite_credito": cliente.get("limite_credito"),
                "score": cliente.get("score")
            }
        }
    
    return {
        "sucesso": True,
        "autenticado": False,
        "erro": "CPF ou data de nascimento não conferem."
    }


# ==================== CONJUNTOS DE TOOLS POR AGENTE ====================

def get_tools_triagem():
    """Retorna tools disponíveis para o Agente de Triagem"""
    return [
        responder_usuario,  # OBRIGATÓRIO para todas as respostas
        validar_cpf,
        validar_data_nascimento,
        autenticar_cliente_tool,
        redirecionar_para_credito,
        redirecionar_para_cambio,
        redirecionar_para_entrevista,
        encerrar_conversa,
    ]


def get_tools_credito():
    """Retorna tools disponíveis para o Agente de Crédito"""
    return [
        responder_usuario,  # OBRIGATÓRIO para todas as respostas
        consultar_limite_credito,
        solicitar_aumento_limite,
        redirecionar_para_cambio,
        redirecionar_para_entrevista,
        encerrar_conversa,
    ]


def get_tools_cambio():
    """Retorna tools disponíveis para o Agente de Câmbio"""
    return [
        responder_usuario,  # OBRIGATÓRIO para todas as respostas
        consultar_cotacao_moeda,
        redirecionar_para_credito,
        redirecionar_para_entrevista,
        encerrar_conversa,
    ]


def get_tools_entrevista():
    """Retorna tools disponíveis para o Agente de Entrevista"""
    return [
        responder_usuario,  # OBRIGATÓRIO para todas as respostas
        registrar_renda_mensal,
        registrar_tipo_emprego,
        registrar_despesas_fixas,
        registrar_dependentes,
        registrar_dividas,
        calcular_novo_score,
        redirecionar_para_credito,
        redirecionar_para_cambio,
        encerrar_conversa,
    ]
