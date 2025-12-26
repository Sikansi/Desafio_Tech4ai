"""
Calculadora de Score de Crédito
"""
from typing import Dict


def calcular_score(
    renda_mensal: float,
    tipo_emprego: str,
    despesas_fixas: float,
    num_dependentes: int,
    tem_dividas: bool
) -> float:
    """
    Calcula o score de crédito baseado em fatores financeiros
    
    Args:
        renda_mensal: Renda mensal do cliente
        tipo_emprego: 'formal', 'autônomo' ou 'desempregado'
        despesas_fixas: Despesas fixas mensais
        num_dependentes: Número de dependentes
        tem_dividas: True se tem dívidas ativas, False caso contrário
        
    Returns:
        Score de crédito (0 a 1000)
    """
    # Pesos definidos na especificação
    peso_renda = 30
    peso_emprego = {
        "formal": 300,
        "autônomo": 200,
        "desempregado": 0
    }
    peso_dependentes = {
        0: 100,
        1: 80,
        2: 60
    }
    peso_dividas = {
        True: -100,
        False: 100
    }
    
    # Calcula componente de renda
    componente_renda = (renda_mensal / (despesas_fixas + 1)) * peso_renda
    
    # Componente de emprego
    componente_emprego = peso_emprego.get(tipo_emprego.lower(), 0)
    
    # Componente de dependentes
    if num_dependentes >= 3:
        componente_dependentes = 30
    else:
        componente_dependentes = peso_dependentes.get(num_dependentes, 30)
    
    # Componente de dívidas
    componente_dividas = peso_dividas.get(tem_dividas, 0)
    
    # Calcula score total
    score = (
        componente_renda +
        componente_emprego +
        componente_dependentes +
        componente_dividas
    )
    
    # Garante que o score está entre 0 e 1000
    score = max(0, min(1000, score))
    
    return round(score, 2)

