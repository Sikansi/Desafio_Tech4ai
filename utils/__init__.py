"""
Módulo de Utilitários
"""
from utils.csv_handler import (
    ler_clientes,
    autenticar_cliente,
    obter_cliente_por_cpf,
    atualizar_score_cliente,
    ler_score_limite,
    verificar_limite_permitido,
    registrar_solicitacao_aumento
)
from utils.score_calculator import calcular_score
from utils.cotacao_api import buscar_cotacao_dolar, buscar_cotacao_moeda

__all__ = [
    "ler_clientes",
    "autenticar_cliente",
    "obter_cliente_por_cpf",
    "atualizar_score_cliente",
    "ler_score_limite",
    "verificar_limite_permitido",
    "registrar_solicitacao_aumento",
    "calcular_score",
    "buscar_cotacao_dolar",
    "buscar_cotacao_moeda"
]

