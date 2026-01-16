"""
Utilitários para manipulação de arquivos CSV
"""
import pandas as pd
import os
from datetime import datetime
from typing import Optional, Dict, List


def ler_clientes(caminho: str = "data/clientes.csv") -> pd.DataFrame:
    """Lê o arquivo de clientes"""
    try:
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"Arquivo {caminho} não encontrado")
        return pd.read_csv(caminho)
    except Exception as e:
        raise Exception(f"Erro ao ler arquivo de clientes: {str(e)}")


def autenticar_cliente(cpf: str, data_nascimento: str, caminho: str = "data/clientes.csv") -> Optional[Dict]:
    """
    Autentica um cliente com base no CPF e data de nascimento
    
    Args:
        cpf: CPF do cliente (apenas números)
        data_nascimento: Data de nascimento no formato YYYY-MM-DD
        
    Returns:
        Dict com dados do cliente se autenticado, None caso contrário
    """
    try:
        df = ler_clientes(caminho)
        
        # Normaliza CPF (remove formatação)
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        # Busca cliente
        cliente = df[df['cpf'].astype(str) == cpf_limpo]
        
        if cliente.empty:
            return None
            
        cliente_data = cliente.iloc[0].to_dict()
        
        # Compara data de nascimento
        if str(cliente_data['data_nascimento']) == data_nascimento:
            return cliente_data
        
        return None
    except Exception as e:
        raise Exception(f"Erro na autenticação: {str(e)}")


def obter_cliente_por_cpf(cpf: str, caminho: str = "data/clientes.csv") -> Optional[Dict]:
    """Obtém dados do cliente apenas pelo CPF"""
    try:
        df = ler_clientes(caminho)
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        cliente = df[df['cpf'].astype(str) == cpf_limpo]
        
        if cliente.empty:
            return None
            
        return cliente.iloc[0].to_dict()
    except Exception as e:
        raise Exception(f"Erro ao buscar cliente: {str(e)}")


def atualizar_score_cliente(cpf: str, novo_score: float, caminho: str = "data/clientes.csv"):
    """Atualiza o score de crédito de um cliente"""
    try:
        df = ler_clientes(caminho)
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        # Garante que o score está entre 0 e 1000
        novo_score = max(0, min(1000, novo_score))
        
        df.loc[df['cpf'].astype(str) == cpf_limpo, 'score'] = novo_score
        df.to_csv(caminho, index=False)
    except Exception as e:
        raise Exception(f"Erro ao atualizar score: {str(e)}")


def atualizar_limite_cliente(cpf: str, novo_limite: float, caminho: str = "data/clientes.csv"):
    """Atualiza o limite de crédito de um cliente"""
    try:
        df = ler_clientes(caminho)
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        # Garante que o limite é positivo
        novo_limite = max(0, novo_limite)
        
        df.loc[df['cpf'].astype(str) == cpf_limpo, 'limite_credito'] = novo_limite
        df.to_csv(caminho, index=False)
        
        return True
    except Exception as e:
        raise Exception(f"Erro ao atualizar limite: {str(e)}")


def ler_score_limite(caminho: str = "data/score_limite.csv") -> pd.DataFrame:
    """Lê a tabela de limites por score"""
    try:
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"Arquivo {caminho} não encontrado")
        return pd.read_csv(caminho)
    except Exception as e:
        raise Exception(f"Erro ao ler tabela de score_limite: {str(e)}")


def verificar_limite_permitido(score: float, limite_solicitado: float, caminho: str = "data/score_limite.csv") -> bool:
    """
    Verifica se o limite solicitado é permitido para o score atual
    
    Returns:
        True se permitido, False caso contrário
    """
    try:
        df = ler_score_limite(caminho)
        
        # Encontra a faixa de score
        faixa = df[
            (df['score_minimo'] <= score) & 
            (df['score_maximo'] >= score)
        ]
        
        if faixa.empty:
            return False
        
        limite_maximo = faixa.iloc[0]['limite_maximo']
        return limite_solicitado <= limite_maximo
    except Exception as e:
        raise Exception(f"Erro ao verificar limite: {str(e)}")


def registrar_solicitacao_aumento(
    cpf: str,
    limite_atual: float,
    novo_limite_solicitado: float,
    status: str,
    caminho: str = "data/solicitacoes_aumento_limite.csv"
):
    """Registra uma nova solicitação de aumento de limite"""
    try:
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        data_hora = datetime.now().isoformat()
        
        nova_solicitacao = {
            'cpf_cliente': cpf_limpo,
            'data_hora_solicitacao': data_hora,
            'limite_atual': limite_atual,
            'novo_limite_solicitado': novo_limite_solicitado,
            'status_pedido': status
        }
        
        # Lê arquivo existente ou cria novo
        if os.path.exists(caminho):
            df = pd.read_csv(caminho)
        else:
            df = pd.DataFrame(columns=['cpf_cliente', 'data_hora_solicitacao', 'limite_atual', 'novo_limite_solicitado', 'status_pedido'])
        
        # Adiciona nova solicitação
        df = pd.concat([df, pd.DataFrame([nova_solicitacao])], ignore_index=True)
        df.to_csv(caminho, index=False)
    except Exception as e:
        raise Exception(f"Erro ao registrar solicitação: {str(e)}")

