# 🏦 Banco Ágil - Sistema de Agentes Bancários Inteligentes

## 📋 Visão Geral do Projeto

O **Banco Ágil** é um sistema de atendimento ao cliente baseado em agentes de IA especializados, desenvolvido para simular um ambiente bancário digital completo. O sistema utiliza múltiplos agentes especializados que trabalham de forma coordenada para atender diferentes necessidades dos clientes, mantendo uma experiência fluida e transparente.

## 🚀 Começando

Para começar a usar o sistema, clone o repositório e siga as instruções de instalação abaixo.

### Características Principais

- 🤖 **Múltiplos Agentes Especializados**: Cada agente possui responsabilidades bem definidas
- 🧠 **IA-Driven**: Sistema utiliza LLMs (Large Language Models) para interpretação natural de mensagens, não apenas palavras-chave
- 🔄 **Transições Transparentes**: Mudanças entre agentes são imperceptíveis para o cliente
- 🔐 **Sistema de Autenticação**: Validação segura de clientes via CPF e data de nascimento
- 💾 **Persistência de Dados**: Armazenamento em arquivos CSV para simplicidade
- 🌐 **Interface Web Moderna**: Interface Streamlit intuitiva e responsiva
- 🧮 **Cálculo Inteligente de Score**: Sistema ponderado para avaliação de crédito
- 🔀 **Gateway Inteligente de Modelos**: Sistema automático de fallback entre modelos LLM quando há limite de quota
- 🐛 **Debug Transparente**: Painel de debug mostra prompts e respostas da IA para transparência

## 🏗️ Arquitetura do Sistema

### Componentes Principais

```
Desafio_Tech4ai/
├── agents/              # Módulos dos agentes especializados
│   ├── base_agent.py    # Classe base abstrata para todos os agentes
│   ├── triagem_agent.py # Agente de autenticação e triagem
│   ├── credito_agent.py # Agente de consulta e solicitação de crédito
│   ├── entrevista_agent.py # Agente de entrevista financeira
│   └── cambio_agent.py  # Agente de consulta de cotações
├── utils/               # Utilitários compartilhados
│   ├── csv_handler.py   # Manipulação de arquivos CSV
│   ├── score_calculator.py # Cálculo de score de crédito
│   └── cotacao_api.py   # Integração com API de cotações
├── data/                # Arquivos de dados
│   ├── clientes.csv     # Base de dados de clientes
│   ├── score_limite.csv # Tabela de limites por score
│   └── solicitacoes_aumento_limite.csv # Histórico de solicitações
├── orchestrator.py      # Orquestrador principal
├── app.py              # Interface Streamlit
├── requirements.txt    # Dependências do projeto
├── listar_modelos.py   # Script para listar modelos disponíveis da API
├── doc.md              # Enunciado original do desafio técnico
└── .env                # Arquivo de configuração (criar manualmente, não está no repo)
```

### Fluxo de Dados

1. **Entrada**: Cliente interage via interface Streamlit
2. **Orquestração**: `Orchestrator` gerencia o fluxo entre agentes
3. **Processamento**: Agente especializado processa a solicitação
4. **Persistência**: Dados são salvos/consultados em arquivos CSV
5. **Resposta**: Resposta é retornada ao cliente via interface

### Agentes e Responsabilidades

#### 1. Agente de Triagem (`TriagemAgent`)
- **Responsabilidade**: Porta de entrada do sistema
- **Funcionalidades**:
  - Saudação inicial
  - Coleta de CPF e data de nascimento
  - Autenticação contra base de dados
  - Identificação de necessidade do cliente
  - Redirecionamento para agente apropriado
- **Limites**: Máximo de 3 tentativas de autenticação

#### 2. Agente de Crédito (`CreditoAgent`)
- **Responsabilidade**: Gestão de crédito e limites
- **Funcionalidades**:
  - Consulta de limite de crédito atual
  - Processamento de solicitações de aumento
  - Validação de score vs limite solicitado
  - Registro de solicitações em CSV
  - Redirecionamento para entrevista quando necessário

#### 3. Agente de Entrevista de Crédito (`EntrevistaAgent`)
- **Responsabilidade**: Coleta de dados financeiros e recálculo de score
- **Funcionalidades**:
  - Entrevista estruturada (5 perguntas)
  - Coleta de: renda, tipo de emprego, despesas, dependentes, dívidas
  - Cálculo de novo score usando fórmula ponderada
  - Atualização de score na base de dados
  - Redirecionamento de volta para Agente de Crédito

#### 4. Agente de Câmbio (`CambioAgent`)
- **Responsabilidade**: Consulta de cotações de moedas
- **Funcionalidades**:
  - Busca de cotação em tempo real via API externa
  - Suporte para múltiplas moedas (atualmente USD)
  - Apresentação formatada da cotação
  - Tratamento de erros de API

### Fórmula de Score de Crédito

O score é calculado usando uma fórmula ponderada:

```python
score = (
    (renda_mensal / (despesas + 1)) * peso_renda +
    peso_emprego[tipo_emprego] +
    peso_dependentes[num_dependentes] +
    peso_dividas[tem_dividas]
)
```

**Pesos**:
- `peso_renda`: 30
- `peso_emprego`: formal=300, autônomo=200, desempregado=0
- `peso_dependentes`: 0=100, 1=80, 2=60, 3+=30
- `peso_dividas`: sim=-100, não=100

**Limite**: Score entre 0 e 1000 pontos

## ✨ Funcionalidades Implementadas

### ✅ Autenticação e Triagem
- [x] Coleta de CPF e data de nascimento
- [x] Validação contra base de dados CSV
- [x] Sistema de tentativas (máximo 3)
- [x] Identificação automática de necessidade
- [x] Redirecionamento inteligente

### ✅ Gestão de Crédito
- [x] Consulta de limite atual
- [x] Solicitação de aumento de limite
- [x] Validação de score vs limite solicitado
- [x] Registro de solicitações em CSV
- [x] Aprovação/rejeição automática
- [x] Oferecimento de entrevista quando rejeitado

### ✅ Entrevista de Crédito
- [x] Entrevista conversacional estruturada
- [x] Coleta de 5 informações financeiras
- [x] Cálculo de novo score
- [x] Atualização automática na base de dados
- [x] Redirecionamento para nova análise

### ✅ Consulta de Câmbio
- [x] Busca de cotação em tempo real
- [x] Integração com API pública (AwesomeAPI)
- [x] Formatação amigável de resultados
- [x] Tratamento de erros de API

### ✅ Interface e Experiência
- [x] Interface Streamlit moderna
- [x] Histórico de conversação
- [x] Indicador de agente atual
- [x] Informações do cliente autenticado
- [x] Botão de reiniciar conversa
- [x] Tratamento de encerramento de conversa
- [x] Painel de debug da IA (mostra prompts e respostas)

### ✅ Sistema de IA e Interpretação
- [x] Interpretação natural de mensagens usando LLMs
- [x] Sistema de comandos MCP-like para comunicação estruturada
- [x] Gateway inteligente com fallback automático de modelos
- [x] Debug transparente de chamadas à IA
- [x] Tratamento robusto de erros de interpretação

### ✅ Persistência de Dados
- [x] Leitura/escrita de arquivos CSV
- [x] Validação de dados
- [x] Tratamento de erros de arquivo
- [x] Histórico de solicitações

## 🚧 Desafios Enfrentados e Soluções

### 1. Migração de Sistema Baseado em Palavras-chave para LLM-Driven
**Desafio**: O sistema inicialmente dependia principalmente de busca por palavras-chave para identificar intenções do usuário, o que limitava a flexibilidade e não aproveitava o potencial de interpretação natural das LLMs.

**Solução**: 
- Refatoração completa para usar LLMs como método primário de interpretação
- Implementação de sistema de comandos MCP-like onde a IA pode responder com comandos estruturados (ex: `CPF:12345678900`, `CREDITO`, `VALOR:250000`) ou texto natural
- Remoção de métodos hardcoded de identificação de intenção, mantendo apenas como fallback
- Prompts detalhados explicando o contexto do sistema e as opções disponíveis para cada agente

### 2. Modelos LLM Indisponíveis ou Descontinuados
**Desafio**: O modelo padrão `gemini-pro` foi descontinuado pela Google, causando erros `NOT_FOUND` (404) ao tentar usar o sistema.

**Solução**:
- Criação do script `listar_modelos.py` para verificar dinamicamente quais modelos estão disponíveis na API
- Atualização da lista de modelos fallback baseada em modelos realmente disponíveis
- Mudança do modelo padrão para `gemini-2.5-flash` após verificação de disponibilidade

### 3. Limite de Quota Diária dos Modelos LLM
**Desafio**: Quando um modelo atinge seu limite de quota diária (`RESOURCE_EXHAUSTED`), o sistema falhava completamente, exigindo intervenção manual ou espera de horas.

**Solução**:
- Implementação de gateway inteligente com fallback automático entre modelos
- Lista ordenada `MODELOS_FALLBACK` com modelos preferenciais (do melhor para o pior)
- Cache compartilhado (`_modelos_esgotados_compartilhado`) para evitar tentativas repetidas em modelos já esgotados
- Detecção automática de erro `RESOURCE_EXHAUSTED` e troca imediata para o próximo modelo disponível
- O sistema continua funcionando mesmo quando múltiplos modelos estão esgotados

### 4. Duplicação de Chamadas à IA e Acúmulo de Debug Info
**Desafio**: O sistema estava enviando as mesmas mensagens múltiplas vezes para a IA, e o debug info estava acumulando informações de interações anteriores, dificultando a análise.

**Solução**:
- Implementação do parâmetro `usar_historico` em `gerar_resposta` e `processar_com_comandos` para controlar quando enviar histórico completo
- Para extração de dados específicos (CPF, valores, etc.), uso de `usar_historico=False` para evitar contexto desnecessário
- Método `resetar_debug_info()` chamado antes de cada processamento para limpar debug info anterior
- Debug info agora mostra apenas as chamadas relevantes para a interação atual

### 5. Extração Incorreta de Valores Numéricos
**Desafio**: O sistema não conseguia extrair corretamente valores como "250k", "250 mil" ou "1 milhão", interpretando "250k" como R$ 250,00 ao invés de R$ 250.000,00.

**Solução**:
- Melhoria da função `_extrair_valor` para reconhecer sufixos "k" (multiplicador 1000) e "mil" (multiplicador 1000)
- Uso de LLM para interpretação de valores em linguagem natural antes de tentar extração direta
- Suporte para múltiplos formatos: números diretos, "k", "mil", "milhão", etc.

### 6. Agente de Entrevista Não Usando Sistema de Comandos
**Desafio**: O `EntrevistaAgent` ainda usava métodos hardcoded (`_extrair_tipo_emprego`, `_extrair_booleano`) ao invés do sistema de comandos baseado em LLM, e não redirecionava corretamente após conclusão.

**Solução**:
- Migração completa do `EntrevistaAgent` para usar `processar_com_comandos` em todas as etapas
- Implementação de prompts específicos para cada etapa (renda, emprego, despesas, dependentes, dívidas)
- Sistema de redirecionamento após entrevista concluída usando IA para detectar intenção do cliente
- Fallback para métodos diretos apenas quando a IA falha

### 7. Agente de Crédito Não Retornando Respostas Após Comandos
**Desafio**: Quando a IA identificava comandos como `CONSULTAR_LIMITE` ou `SOLICITAR_AUMENTO:valor`, o `CreditoAgent` processava mas não retornava a resposta gerada, causando perda da resposta ao usuário.

**Solução**:
- Adição de `return` explícito após processar comandos para garantir que a resposta seja retornada ao orquestrador
- Separação clara entre identificação de comando e geração de resposta final
- Garantia de que todas as respostas geradas são adicionadas ao histórico e retornadas

### 8. Interpretação Incorreta de Aceitação de Entrevista
**Desafio**: O `CreditoAgent` interpretava incorretamente mensagens como "Quero aumentar meu limite para 100 mil reais" como aceitação de entrevista, porque continha a palavra "quero".

**Solução**:
- Melhoria do prompt em `_aceitou_entrevista` para ser mais específico sobre o contexto
- Instrução explícita para a IA ignorar mensagens sobre limite, aumento ou crédito
- Verificação apenas quando realmente há uma oferta de entrevista pendente (`entrevista_oferecida == True`)

### 9. Gateway Tentando Usar Modelos Inexistentes
**Desafio**: A lista de modelos fallback continha modelos que não existiam mais na API, causando erros 404 durante o fallback.

**Solução**:
- Uso do script `listar_modelos.py` para manter lista atualizada de modelos disponíveis
- Remoção de modelos descontinuados da lista `MODELOS_FALLBACK`
- Validação de modelos antes de adicionar à lista de fallback

## 🔧 Escolhas Técnicas e Justificativas

### Stack Tecnológica

| Componente | Tecnologia | Alternativas Consideradas |
|------------|------------|---------------------------|
| **LLM** | Google Gemini | OpenAI GPT-4, Claude, Groq |
| **Framework** | LangChain | LangGraph, CrewAI, Google ADK |
| **UI** | Streamlit | Gradio, Flask, FastAPI |
| **API Cotação** | AwesomeAPI | ExchangeRate-API, Fixer.io |
| **Dados** | CSV + Pandas | SQLite, PostgreSQL |

### LLM: Google Gemini

**Por que Gemini?**
- **Free tier generoso**: ~1500 requisições/dia sem custo
- **Modelos de qualidade**: gemini-2.5-flash oferece boa performance para tarefas conversacionais
- **Tool Calling nativo**: Suporte integrado para Function Calling, essencial para a arquitetura de agentes
- **Baixa latência**: Respostas rápidas comparado a alternativas

**Por que não outras opções?**
- **OpenAI GPT-4**: Pago, custo por token significativo
- **Claude**: Limite de uso gratuito mais restritivo
- **Groq**: Muito rápido, mas modelos menos inteligentes para interpretação contextual

### Framework: LangChain

**Por que LangChain?**
- **Consolidado**: Framework maduro com grande comunidade
- **Tool Calling integrado**: Abstração elegante para Function Calling via decorators `@tool`
- **Gerenciamento de memória**: `InMemoryChatMessageHistory` pronto para uso
- **Integração Gemini**: `langchain-google-genai` bem documentado e mantido
- **Flexibilidade**: Fácil trocar entre provedores de LLM se necessário

**Por que não outras opções?**
- **LangGraph**: Mais complexo, ideal para fluxos com loops/condicionais mais elaborados
- **CrewAI**: Focado em agentes autônomos colaborativos, overkill para este caso
- **Google ADK**: Muito novo, menos documentação e exemplos

### Interface: Streamlit

**Por que Streamlit?**
- **Zero frontend code**: Interface completa apenas com Python
- **Setup em minutos**: `pip install streamlit` + `streamlit run app.py`
- **Chat nativo**: Componentes `st.chat_input` e `st.chat_message` prontos
- **Hot reload**: Atualiza automaticamente ao salvar código
- **Deploy fácil**: Streamlit Cloud gratuito para demonstrações

**Por que não outras opções?**
- **Gradio**: Muito similar, escolha poderia ser qualquer um
- **Flask/FastAPI**: Exigem frontend separado (React, Vue, etc.)

### API de Cotações: AwesomeAPI

**Por que AwesomeAPI?**
- **100% gratuita**: Sem limites de uso, sem necessidade de cadastro
- **Sem API key**: Zero configuração adicional
- **Dados confiáveis**: Fonte baseada em dados do Banco Central do Brasil
- **Múltiplas moedas**: USD, EUR, GBP, JPY, CHF, CAD, AUD, CNY, ARS, CLP, MXN
- **Tempo real**: Cotações atualizadas constantemente

**Por que não outras opções?**
- **ExchangeRate-API**: Requer API key, limite no plano gratuito
- **Fixer.io**: Plano gratuito muito limitado (100 req/mês)

### Armazenamento: Arquivos CSV

**Por que CSV?**
- **Requisito do desafio**: Especificado no enunciado
- **Simplicidade**: Fácil de ler, editar e versionar
- **Transparência**: Dados visíveis para debug e testes
- **Zero config**: Não precisa instalar banco de dados

**Limitações conhecidas**:
- Não escala para muitos usuários simultâneos
- Sem transações ACID
- Em produção, migraria para SQLite ou PostgreSQL

### Arquitetura: Agentes Especializados + Orquestrador

**Por que esta arquitetura?**
- **Separação de responsabilidades**: Cada agente com escopo bem definido
- **Requisito do desafio**: 3 agentes especializados + triagem
- **Manutenibilidade**: Fácil modificar um agente sem afetar outros
- **Testabilidade**: Cada agente pode ser testado isoladamente
- **Extensibilidade**: Adicionar novos agentes é trivial

### Dependências do Projeto

```
streamlit>=1.28.0           # Interface web
langchain>=0.1.0            # Framework principal de agentes
langchain-google-genai>=1.0.0  # Integração com Gemini
langchain-core>=0.1.0       # Mensagens, Tools, Memória
python-dotenv>=1.0.0        # Carregar variáveis de ambiente
pandas>=2.0.0               # Manipulação de CSVs
requests>=2.31.0            # Chamadas HTTP (API cotação)
pydantic>=2.0.0             # Validação de schemas (tools)
google-generativeai>=0.3.0  # SDK Gemini
```

## 📚 Tutorial de Execução e Testes

### Pré-requisitos

1. **Python 3.8+** instalado
2. **Chave da API Google Gemini**:
   - Acesse: https://makersuite.google.com/app/apikey
   - Crie uma nova chave
   - Copie a chave gerada

### Instalação

1. **Clone o repositório**:
```bash
git clone <url-do-repositorio>
cd Desafio_Tech4ai
```

2. **Crie um ambiente virtual** (recomendado):
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instale as dependências**:
```bash
pip install -r requirements.txt
```

4. **Configure a chave da API**:
   - **Opção 1 (Recomendada)**: Crie um arquivo `.env` na raiz do projeto (mesmo diretório onde está o `app.py`)
     - Crie um arquivo chamado `.env` (sem extensão)
     - Adicione a seguinte linha: `GOOGLE_API_KEY=sua_chave_aqui`
     - Substitua `sua_chave_aqui` pela sua chave real
   
   - **Opção 2**: Exporte como variável de ambiente:
     ```bash
     # Windows PowerShell
     $env:GOOGLE_API_KEY="sua_chave_aqui"
     
     # Linux/Mac
     export GOOGLE_API_KEY="sua_chave_aqui"
     ```
   
   **⚠️ IMPORTANTE**: O arquivo `.env` não deve ser commitado no repositório (já está no .gitignore). Mantenha suas chaves seguras!

### Execução

1. **Inicie a aplicação Streamlit**:
```bash
streamlit run app.py
```

2. **Acesse no navegador**:
   - O Streamlit abrirá automaticamente em `http://localhost:8501`
   - Se não abrir, acesse manualmente no navegador

3. **Verificação de Configuração**:
   - Se você ver uma mensagem de erro sobre `GOOGLE_API_KEY`, verifique se o arquivo `.env` está na raiz do projeto
   - Certifique-se de que o arquivo `.env` contém exatamente: `GOOGLE_API_KEY=sua_chave_aqui` (sem espaços ao redor do `=`)

### Scripts Úteis

#### Listar Modelos Disponíveis
Para ver quais modelos da API Google Gemini estão disponíveis:
```bash
python listar_modelos.py
```
Este script ajuda a verificar se sua chave está funcionando e mostra os modelos que podem ser usados pelo sistema.

### Testes

#### Teste 1: Autenticação Bem-Sucedida
1. Abra a interface Streamlit
2. Digite qualquer mensagem para iniciar
3. Informe CPF: `12345678900`
4. Informe data de nascimento: `15/05/1990`
5. **Resultado esperado**: Mensagem de autenticação bem-sucedida

#### Teste 2: Consulta de Limite
1. Após autenticação, digite: "Qual é meu limite de crédito?"
2. **Resultado esperado**: Exibição do limite atual e score

#### Teste 3: Solicitação de Aumento (Aprovada)
1. Digite: "Quero aumentar meu limite para 6000"
2. **Resultado esperado**: 
   - Se score permitir: Aprovação da solicitação
   - Se não permitir: Rejeição com oferta de entrevista

#### Teste 4: Entrevista de Crédito
1. Se uma solicitação foi rejeitada, aceite a entrevista
2. Responda as perguntas:
   - Renda: `8000`
   - Emprego: `formal`
   - Despesas: `3000`
   - Dependentes: `1`
   - Dívidas: `não`
3. **Resultado esperado**: Novo score calculado e redirecionamento para crédito

#### Teste 5: Consulta de Câmbio
1. Após autenticação, digite: "Qual a cotação do dólar?"
2. **Resultado esperado**: Cotação atual do dólar em tempo real

#### Teste 6: Autenticação com Falhas
1. Tente autenticar com CPF/data incorretos 3 vezes
2. **Resultado esperado**: Mensagem de encerramento após 3 tentativas

#### Teste 7: Encerramento de Conversa
1. A qualquer momento, digite: "encerrar" ou "sair"
2. **Resultado esperado**: Mensagem de despedida e encerramento

### Dados de Teste Disponíveis

O arquivo `data/clientes.csv` contém os seguintes clientes para teste:

| CPF | Nome | Data Nascimento | Limite | Score |
|-----|------|----------------|--------|-------|
| 12345678900 | João Silva | 1990-05-15 | R$ 5.000 | 650 |
| 98765432100 | Maria Santos | 1985-08-22 | R$ 8.000 | 750 |
| 11122233344 | Pedro Oliveira | 1992-11-30 | R$ 3.000 | 550 |
| 55566677788 | Ana Costa | 1988-03-10 | R$ 10.000 | 850 |
| 99988877766 | Carlos Souza | 1995-07-05 | R$ 2.000 | 450 |

### Verificação de Arquivos Gerados

Após executar solicitações de aumento de limite, verifique:
- `data/solicitacoes_aumento_limite.csv`: Deve conter registros das solicitações
- `data/clientes.csv`: Score deve ser atualizado após entrevistas

### Debug da IA

O sistema inclui um painel de debug na sidebar que mostra:
- Prompts enviados para a IA
- Respostas recebidas da IA
- Modelo utilizado em cada chamada
- Erros ocorridos (se houver)

Isso permite transparência total sobre como a IA está interpretando as mensagens do usuário.

### Solução de Problemas

#### Erro: "GOOGLE_API_KEY não encontrada"
- Verifique se o arquivo `.env` existe na raiz do projeto
- Confirme que o arquivo contém exatamente: `GOOGLE_API_KEY=sua_chave_aqui` (sem espaços)
- Certifique-se de que o arquivo está no mesmo diretório que `app.py`

#### Erro: "RESOURCE_EXHAUSTED" ou "Quota Exceeded"
- O sistema automaticamente tenta outros modelos quando um atinge o limite
- Se todos os modelos estiverem esgotados, aguarde algumas horas ou use uma nova chave de API
- Você pode verificar quais modelos estão disponíveis com: `python listar_modelos.py`

#### A IA não está interpretando corretamente
- Verifique o painel de debug na sidebar para ver o que a IA está recebendo
- Os prompts são mostrados explicitamente para facilitar debugging
- Se necessário, ajuste os prompts nos arquivos dos agentes

#### Problemas com ambiente virtual
- Certifique-se de que o ambiente virtual está ativado antes de instalar dependências
- No Windows, use `venv\Scripts\activate` (não `venv\Scripts\activate.bat`)
- Se tiver problemas, tente reinstalar: `pip install --upgrade -r requirements.txt`

## 📝 Estrutura de Arquivos CSV

### clientes.csv
```csv
cpf,nome,data_nascimento,limite_credito,score
```

### score_limite.csv
```csv
score_minimo,score_maximo,limite_maximo
```

### solicitacoes_aumento_limite.csv
```csv
cpf_cliente,data_hora_solicitacao,limite_atual,novo_limite_solicitado,status_pedido
```

## 🔒 Segurança e Considerações

- ⚠️ **Este é um protótipo educacional**: Não use em produção sem revisão de segurança
- 🔐 **Dados sensíveis**: CPFs e informações pessoais estão em texto plano
- 🌐 **API Keys**: Nunca commite chaves de API no repositório
- 📊 **Validação**: Implemente validações mais robustas para produção

## 🚀 Melhorias Futuras

- [ ] Implementar banco de dados real (PostgreSQL/SQLite)
- [ ] Adicionar autenticação JWT
- [ ] Implementar logging estruturado
- [ ] Adicionar testes unitários e de integração
- [ ] Suporte a múltiplas moedas no agente de câmbio
- [ ] Dashboard administrativo
- [ ] Histórico de conversas persistido
- [ ] Suporte a múltiplos idiomas

## 📄 Licença

Este projeto foi desenvolvido como parte de um desafio técnico para Tech4Humans.

## 👨‍💻 Autor

Desenvolvido como parte do Desafio Técnico Tech4Humans - Banco Ágil

---

**Desenvolvido com ❤️ usando Python, LangChain, Streamlit e Google Gemini**

