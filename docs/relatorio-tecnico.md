# Relatório técnico — Central de Chamados de TI

**Projeto demonstrativo de portfólio**  
**Tecnologias:** Python, Flask, SQLite, HTML, CSS e `unittest`

## 1. Objetivo

A Central de Chamados de TI representa um fluxo compacto de service desk. O sistema permite registrar uma solicitação, atribuir categoria e prioridade, acompanhar seu status e consultar uma visão resumida do atendimento. O objetivo é demonstrar fundamentos de desenvolvimento web, lógica de programação, persistência relacional, validação de dados e leitura de indicadores em um contexto próximo a atividades de suporte técnico.

O escopo é intencionalmente demonstrativo. Os nomes, e-mails e situações apresentados na carga inicial são fictícios. O projeto não deve receber informações de usuários ou chamados reais em uma publicação aberta.

## 2. Escopo funcional

### 2.1 Registro

O formulário recebe nome e e-mail do solicitante, título, descrição, categoria e prioridade. O servidor valida os campos novamente, mesmo com validações HTML no navegador. Cada registro recebe um protocolo `CH-ANO-NNNN`, baseado no identificador sequencial do banco.

### 2.2 Classificação

As categorias disponíveis são Acesso e contas, Hardware, Rede e conectividade, Sistemas e software, Impressoras e Outro. A prioridade pode ser Baixa, Média, Alta ou Crítica. O status inicial é Aberto.

### 2.3 Acompanhamento

O chamado percorre os estados Aberto, Em atendimento, Aguardando usuário, Resolvido e Fechado. A equipe pode alterar o estado pela tabela ou pela ficha individual, que exibe o contexto completo e os dados de contato. A transição para Resolvido ou Fechado registra `resolved_at`; ao reabrir ou devolver o chamado a um estado ativo, esse campo é limpo, evitando contabilizar como concluído um chamado ainda ativo.

### 2.4 Pesquisa e filtros

A consulta procura correspondências em protocolo, solicitante, título e e-mail. Os filtros de status, categoria e prioridade podem ser combinados com a pesquisa. Os valores dos filtros são conferidos com as opções permitidas pelo servidor.

### 2.5 Indicadores

- **Chamados ativos:** Aberto, Em atendimento e Aguardando usuário.
- **Resolvidos:** Resolvido e Fechado.
- **Total registrado:** quantidade total de registros.
- **Tempo médio de resolução:** média em minutos entre criação e conclusão, calculada apenas para chamados com `resolved_at`.
- **Distribuição por status e prioridade:** contagens visuais para apoiar leitura rápida da fila.

O tempo usa os instantes armazenados em UTC. A tabela formata a data para o fuso de São Paulo. Na carga demonstrativa, os itens resolvidos têm tempos artificiais para que o indicador tenha conteúdo inicial; esses valores não representam SLA nem dados observados de uma operação real.

## 3. Arquitetura

A aplicação tem três partes principais:

1. **Interface:** `templates/index.html` monta o painel, tabela, filtros e formulário. `static/styles.css` define o layout responsivo para desktop e celular.
2. **Aplicação web:** `app.py` implementa rotas Flask, validações, geração de protocolo, proteção CSRF e consultas ao banco.
3. **Persistência:** SQLite armazena os chamados em uma tabela com chave primária, protocolo único e índices para status e data de criação.

As requisições de leitura usam `GET`; criação e atualização de status usam `POST`. Depois de uma gravação, o servidor redireciona para a página principal, evitando repetição acidental do formulário ao atualizar o navegador.

### 3.1 Rotas HTTP

| Método e rota | Função | Resultado |
|---|---|---|
| `GET /` | Painel, busca e filtros | Indicadores e lista de chamados |
| `POST /chamados` | Valida e registra uma solicitação | Redireciona ao painel com o protocolo gerado |
| `GET /chamados/<id>` | Consulta a ficha individual | Descrição, contato, prioridade e status |
| `POST /chamados/<id>/status` | Atualiza o andamento | Redireciona à ficha ou à lista |
| `GET /saude` | Verifica a conexão SQLite | JSON `{"status":"ok"}` |

## 4. Modelo de dados

| Campo | Uso |
|---|---|
| `id` | Chave primária sequencial |
| `protocol` | Identificador público único do chamado |
| `requester`, `email` | Contato demonstrativo do solicitante |
| `title`, `description` | Resumo e contexto da solicitação |
| `category`, `priority`, `status` | Classificação e andamento |
| `created_at`, `updated_at` | Datas de criação e última alteração |
| `resolved_at` | Data de conclusão; nulo enquanto ativo |

Os campos de data são gravados em formato ISO 8601 com fuso UTC. O índice em `status` auxilia as consultas de acompanhamento; o índice em `created_at` atende à ordenação da lista.

## 5. Validação e proteção básica

- Campos obrigatórios e comprimentos máximos são verificados no servidor.
- O e-mail passa por validação básica de formato; isso não confirma que a caixa postal exista.
- Categoria, prioridade e status são limitados a listas conhecidas.
- Consultas usam parâmetros do SQLite, sem concatenar valores fornecidos pelo usuário em filtros SQL.
- Formulários de gravação validam um token CSRF mantido na sessão assinada do Flask.
- O cookie de sessão é configurado como `HttpOnly` e `SameSite=Lax`; em hospedagem HTTPS, `SESSION_COOKIE_SECURE=1` habilita o atributo `Secure`.
- A aplicação limita o tamanho do corpo da requisição.
- A rota `/saude` executa uma consulta simples ao banco para verificação de disponibilidade.
- Erros de validação são exibidos no painel e os valores já digitados são preservados para correção.

Essas medidas são adequadas ao escopo de estudo, mas não equivalem a uma revisão de segurança ou a controles de produção. Quando `SECRET_KEY` não está configurada, a aplicação gera uma chave aleatória para o processo atual; em uma hospedagem, defina `SECRET_KEY` por variável de ambiente para que as sessões permaneçam válidas entre reinicializações. A chave não deve ser publicada no repositório.

## 6. Instalação e execução

Requer Python 3.10 ou superior. No Windows, dentro da pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

A interface local fica em `http://127.0.0.1:5000/`. Os exemplos fictícios são inseridos quando o banco está vazio. `LOAD_SAMPLE_DATA=0` desativa a carga inicial; `TICKETS_DATABASE` permite apontar para outro arquivo SQLite. `PORT` altera a porta de execução local. A aplicação gera uma chave de sessão aleatória quando `SECRET_KEY` não foi definida; em uma hospedagem, forneça uma chave estável por variável de ambiente e mantenha `FLASK_DEBUG` desativado.

### 6.1 Configuração

| Variável | Padrão | Finalidade |
|---|---|---|
| `SECRET_KEY` | Chave aleatória por processo | Assina a sessão usada pelo token CSRF; defina um valor estável no ambiente hospedado |
| `TICKETS_DATABASE` | `instance/chamados.db` | Caminho do banco SQLite |
| `LOAD_SAMPLE_DATA` | `1` | Inclui exemplos fictícios quando o banco está vazio; use `0` para não carregar exemplos |
| `PORT` | `5000` | Porta do servidor de desenvolvimento |
| `FLASK_DEBUG` | Desativado | Ativa depuração local quando definido como `1`; não habilite em produção |
| `DEMO_READ_ONLY` | `0` | Com valor `1`, oculta formulários e bloqueia as rotas de gravação para uma demonstração pública |
| `SESSION_COOKIE_SECURE` | `0` | Com valor `1`, envia o cookie de sessão somente por HTTPS |

## 7. Testes

Os testes automatizados cobrem carregamento do painel, rota de saúde, criação e validação de chamados, preservação dos campos após erro, pesquisa combinada com categoria, ficha individual, mudança de status, data de resolução, rejeição de CSRF, modo somente leitura e resposta 404. A execução é feita com:

```powershell
python -m unittest discover -s tests -v
```

O conjunto usa um banco temporário isolado, para não alterar dados locais.

## 8. Limitações e próximos passos

A versão atual não tem autenticação, papéis de solicitante e técnico, atribuição de responsável, comentários, anexos, notificações, histórico completo de transições, SLA, exportação, paginação ou migrações de esquema. A validação de e-mail verifica apenas o formato básico, não a existência da caixa postal. O tempo médio considera tempo corrido, incluindo períodos fora do expediente, e não mede horas úteis.

Para aproximar o sistema de uma operação real, os próximos passos seriam adicionar autenticação e autorização por perfil; manter um histórico separado de eventos; atribuir chamados a técnicos; registrar primeira resposta e prazos de SLA; criar testes de integração; e migrar para um banco gerenciado com backups e política de retenção. Uma demonstração pública deve permanecer isolada e usar somente dados fictícios.

## 9. Conclusão

O projeto demonstra um ciclo simples de atendimento técnico, do registro à conclusão, com persistência, regras de validação e indicadores calculados a partir dos chamados. O código e as limitações estão documentados para facilitar revisão, execução local e evolução futura.
