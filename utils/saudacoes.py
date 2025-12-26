"""
Utilitário para detectar e responder a saudações
"""
from datetime import datetime
from typing import Optional, Tuple


def detectar_saudacao(mensagem: str) -> Optional[str]:
    """
    Detecta se a mensagem contém uma saudação
    
    Returns:
        Tipo de saudação detectada: "bom_dia", "boa_tarde", "boa_noite", "ola", ou None
    """
    mensagem_lower = mensagem.lower().strip()
    
    saudações_bom_dia = ["bom dia", "bomdia", "bom-dia", "good morning"]
    saudações_boa_tarde = ["boa tarde", "boatarde", "boa-tarde", "good afternoon"]
    saudações_boa_noite = ["boa noite", "boanoite", "boa-noite", "good evening", "good night"]
    saudações_ola = ["olá", "ola", "oi", "hey", "hi", "hello"]
    
    # Verifica se a mensagem é principalmente uma saudação
    palavras = mensagem_lower.split()
    if len(palavras) <= 3:  # Mensagens curtas são mais prováveis de serem apenas saudações
        if any(saudacao in mensagem_lower for saudacao in saudações_bom_dia):
            return "bom_dia"
        elif any(saudacao in mensagem_lower for saudacao in saudações_boa_tarde):
            return "boa_tarde"
        elif any(saudacao in mensagem_lower for saudacao in saudações_boa_noite):
            return "boa_noite"
        elif any(saudacao in mensagem_lower for saudacao in saudações_ola):
            return "ola"
    
    # Verifica se começa com saudação
    if any(mensagem_lower.startswith(saudacao) for saudacao in saudações_bom_dia):
        return "bom_dia"
    elif any(mensagem_lower.startswith(saudacao) for saudacao in saudações_boa_tarde):
        return "boa_tarde"
    elif any(mensagem_lower.startswith(saudacao) for saudacao in saudações_boa_noite):
        return "boa_noite"
    elif any(mensagem_lower.startswith(saudacao) for saudacao in saudações_ola):
        return "ola"
    
    return None


def gerar_resposta_saudacao(tipo_saudacao: str, contexto: str = "") -> str:
    """
    Gera resposta apropriada para uma saudação
    
    Args:
        tipo_saudacao: Tipo de saudação detectada
        contexto: Contexto adicional (ex: "já autenticado")
        
    Returns:
        Resposta apropriada
    """
    hora_atual = datetime.now().hour
    
    # Determina período do dia baseado na hora atual
    if 5 <= hora_atual < 12:
        periodo = "bom dia"
    elif 12 <= hora_atual < 18:
        periodo = "boa tarde"
    else:
        periodo = "boa noite"
    
    if tipo_saudacao == "bom_dia":
        resposta = "Bom dia!"
    elif tipo_saudacao == "boa_tarde":
        resposta = "Boa tarde!"
    elif tipo_saudacao == "boa_noite":
        resposta = "Boa noite!"
    else:  # ola
        resposta = f"{periodo.capitalize()}!"
    
    # Adiciona contexto se necessário
    if contexto:
        resposta += f" {contexto}"
    
    return resposta


def extrair_mensagem_sem_saudacao(mensagem: str) -> str:
    """
    Remove saudações do início da mensagem para processar o conteúdo real
    
    Returns:
        Mensagem sem a saudação inicial
    """
    mensagem_lower = mensagem.lower().strip()
    
    saudações = [
        "bom dia", "bomdia", "bom-dia", "boa tarde", "boatarde", "boa-tarde",
        "boa noite", "boanoite", "boa-noite", "olá", "ola", "oi", "hey", "hi", "hello"
    ]
    
    for saudacao in saudações:
        if mensagem_lower.startswith(saudacao):
            # Remove a saudação e espaços extras
            mensagem_sem_saudacao = mensagem[len(saudacao):].strip()
            # Remove vírgulas, pontos ou espaços extras no início
            mensagem_sem_saudacao = mensagem_sem_saudacao.lstrip(" ,.!?")
            return mensagem_sem_saudacao
    
    return mensagem

