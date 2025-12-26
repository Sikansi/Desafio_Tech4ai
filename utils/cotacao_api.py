"""
Utilitário para buscar cotações de moedas via API
"""
import requests
import os
from typing import Dict, Optional


def buscar_cotacao_dolar() -> Dict[str, any]:
    """
    Busca cotação do dólar usando API pública gratuita
    
    Returns:
        Dict com informações da cotação
    """
    try:
        # Usando API pública do AwesomeAPI (gratuita, sem necessidade de chave)
        url = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # A API retorna no formato {"USDBRL": {...}}
        if "USDBRL" in data:
            cotacao = data["USDBRL"]
            return {
                "moeda": "USD",
                "moeda_destino": "BRL",
                "valor_compra": float(cotacao.get("bid", 0)),
                "valor_venda": float(cotacao.get("ask", 0)),
                "valor_medio": float(cotacao.get("bid", 0)),  # Usa bid como referência
                "timestamp": cotacao.get("timestamp", ""),
                "sucesso": True
            }
        
        raise Exception("Formato de resposta inesperado da API")
        
    except requests.exceptions.RequestException as e:
        # Fallback: retorna uma mensagem de erro amigável
        return {
            "sucesso": False,
            "erro": f"Não foi possível conectar à API de cotações. Erro: {str(e)}",
            "moeda": "USD",
            "moeda_destino": "BRL"
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro ao processar cotação: {str(e)}",
            "moeda": "USD",
            "moeda_destino": "BRL"
        }


def buscar_cotacao_moeda(moeda: str = "USD") -> Dict[str, any]:
    """
    Busca cotação de uma moeda específica usando API pública
    
    Args:
        moeda: Código da moeda (USD, EUR, GBP, JPY, etc.)
        
    Returns:
        Dict com informações da cotação
    """
    moeda = moeda.upper()
    
    # Mapeamento de moedas suportadas
    moedas_suportadas = {
        "USD": "USD",  # Dólar Americano
        "EUR": "EUR",  # Euro
        "GBP": "GBP",  # Libra Esterlina
        "JPY": "JPY",  # Iene Japonês
        "CHF": "CHF",  # Franco Suíço
        "CAD": "CAD",  # Dólar Canadense
        "AUD": "AUD",  # Dólar Australiano
        "CNY": "CNY",  # Yuan Chinês
        "ARS": "ARS",  # Peso Argentino
        "CLP": "CLP",  # Peso Chileno
        "MXN": "MXN",  # Peso Mexicano
    }
    
    if moeda not in moedas_suportadas:
        return {
            "sucesso": False,
            "erro": f"Moeda {moeda} não suportada. Moedas disponíveis: USD, EUR, GBP, JPY, CHF, CAD, AUD, CNY, ARS, CLP, MXN.",
            "moeda": moeda
        }
    
    try:
        # Usando API pública do AwesomeAPI (gratuita, sem necessidade de chave)
        # Formato: {MOEDA}-BRL (ex: USD-BRL, EUR-BRL)
        url = f"https://economia.awesomeapi.com.br/json/last/{moeda}-BRL"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # A API retorna no formato {"{MOEDA}BRL": {...}}
        chave = f"{moeda}BRL"
        if chave in data:
            cotacao = data[chave]
            return {
                "moeda": moeda,
                "moeda_destino": "BRL",
                "valor_compra": float(cotacao.get("bid", 0)),
                "valor_venda": float(cotacao.get("ask", 0)),
                "valor_medio": float(cotacao.get("bid", 0)),  # Usa bid como referência
                "timestamp": cotacao.get("timestamp", ""),
                "sucesso": True
            }
        
        raise Exception("Formato de resposta inesperado da API")
        
    except requests.exceptions.RequestException as e:
        return {
            "sucesso": False,
            "erro": f"Não foi possível conectar à API de cotações. Erro: {str(e)}",
            "moeda": moeda,
            "moeda_destino": "BRL"
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro ao processar cotação: {str(e)}",
            "moeda": moeda,
            "moeda_destino": "BRL"
        }

