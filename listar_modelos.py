"""
Script para listar modelos disponíveis da API do Google Gemini
"""
import os
import sys
from dotenv import load_dotenv

# Configura encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Carrega variáveis de ambiente
load_dotenv()

# Obtém a chave da API
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("ERRO: GOOGLE_API_KEY nao encontrada no arquivo .env")
    print("Por favor, configure a variavel GOOGLE_API_KEY no arquivo .env")
    exit(1)

print("Listando modelos disponiveis da API do Google Gemini...\n")
print("Usando a API REST diretamente para garantir compatibilidade...\n")

try:
    import requests
    
    # Usa a API REST do Google Gemini para listar modelos
    url = "https://generativelanguage.googleapis.com/v1beta/models?key=" + api_key
    
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"ERRO ao acessar a API: {response.status_code}")
        print(f"Resposta: {response.text}")
        exit(1)
    
    data = response.json()
    
    if 'models' not in data:
        print(f"ERRO: Resposta inesperada da API: {data}")
        exit(1)
    
    models = data['models']
    
    print("=" * 80)
    print("MODELOS DISPONÍVEIS:")
    print("=" * 80)
    
    modelos_geracao = []
    
    for model in models:
        nome = model.get('name', '')
        # Remove o prefixo "models/" se existir
        nome_limpo = nome.replace('models/', '')
        
        # Verifica se o modelo suporta generateContent
        supported_methods = model.get('supportedGenerationMethods', [])
        if 'generateContent' in supported_methods:
            modelos_geracao.append({
                'name': nome_limpo,
                'display_name': model.get('displayName', nome_limpo),
                'description': model.get('description', ''),
                'supported_methods': supported_methods
            })
            
            print(f"\n[OK] {nome_limpo}")
            print(f"   Nome completo: {nome}")
            if model.get('displayName'):
                print(f"   Descrição: {model.get('displayName')}")
            if model.get('description'):
                print(f"   Detalhes: {model.get('description')}")
            print(f"   Métodos suportados: {', '.join(supported_methods)}")
    
    print("\n" + "=" * 80)
    print("RECOMENDAÇÕES:")
    print("=" * 80)
    
    # Prioriza modelos mais recentes e eficientes
    modelos_recomendados = []
    
    for model in modelos_geracao:
        nome = model['name']
        # Prioriza modelos flash (mais rápidos) e pro (mais capazes)
        if 'flash' in nome.lower():
            modelos_recomendados.append((nome, "Rápido e eficiente para uso geral"))
        elif 'pro' in nome.lower():
            modelos_recomendados.append((nome, "Mais capaz, ideal para tarefas complexas"))
        elif '1.5' in nome:
            modelos_recomendados.append((nome, "Versão 1.5, balanceado"))
    
    if modelos_recomendados:
        print("\nModelos recomendados para este projeto:")
        for nome, descricao in modelos_recomendados[:5]:  # Mostra os 5 primeiros
            print(f"   - {nome} - {descricao}")
    
    # Sugere o melhor modelo baseado nas características
    melhor_modelo = None
    for model in modelos_geracao:
        nome = model['name']
        # Prioriza flash para velocidade, mas mantém qualidade
        if 'flash' in nome.lower() and '1.5' in nome:
            melhor_modelo = nome
            break
    
    if not melhor_modelo:
        for model in modelos_geracao:
            nome = model['name']
            if 'pro' in nome.lower() and '1.5' in nome:
                melhor_modelo = nome
                break
    
    if not melhor_modelo and modelos_geracao:
        melhor_modelo = modelos_geracao[0]['name']
    
    if melhor_modelo:
        print(f"\n>>> Modelo recomendado: {melhor_modelo}")
        print(f"   (Use este modelo no arquivo .env como GEMINI_MODEL={melhor_modelo})")
        print(f"\n   Ou atualize o codigo em agents/base_agent.py linha 25:")
        print(f"   model = os.getenv(\"GEMINI_MODEL\", \"{melhor_modelo}\")")
    
    print("\n" + "=" * 80)
    print(f"Total de modelos disponíveis: {len(modelos_geracao)}")
    print("=" * 80)
    
except ImportError:
    print("ERRO: Biblioteca 'requests' nao encontrada")
    print("Instale com: pip install requests")
    exit(1)
except Exception as e:
    print(f"ERRO ao listar modelos: {e}")
    import traceback
    traceback.print_exc()
    print("\nVerifique se:")
    print("1. A GOOGLE_API_KEY esta correta no arquivo .env")
    print("2. Voce tem permissao para listar modelos")
    print("3. A biblioteca requests esta instalada (pip install requests)")
    exit(1)

