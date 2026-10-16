# Central de Chamados de TI

Aplicação web demonstrativa para registrar solicitações de suporte, classificar prioridade e categoria, acompanhar o andamento e consultar indicadores da fila.

## O que o projeto faz

- Registra chamados com solicitante, e-mail, título, descrição, categoria e prioridade.
- Gera um protocolo sequencial no formato `CH-ANO-NNNN`.
- Acompanha cinco etapas: Aberto, Em atendimento, Aguardando usuário, Resolvido e Fechado.
- Abre a ficha de cada solicitação para consultar descrição, contato e atualizar o status.
- Pesquisa protocolo, solicitante, título e e-mail; filtra por status, categoria e prioridade.
- Apresenta total de chamados, chamados ativos, concluídos e tempo médio até a resolução.
- Salva os registros em SQLite e inclui exemplos fictícios na primeira execução.
- Protege formulários POST com token CSRF e usa consultas SQL parametrizadas.

O projeto simula um fluxo de triagem de service desk para fins de estudo. Os registros de exemplo são fictícios; não insira informações pessoais ou solicitações reais em uma publicação de demonstração. A opção `DEMO_READ_ONLY=1` oculta os formulários e rejeita gravações, mantendo a consulta pública em modo somente leitura.

## Requisitos

- Python 3.10 ou superior
- pip

## Executar no Windows

No terminal, dentro da pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000/` no navegador. Para encerrar, pressione `Ctrl+C` no terminal.

## Executar testes

```powershell
python -m unittest discover -s tests -v
```

Os testes usam um banco temporário e não alteram os exemplos do banco local.

## Estrutura

```text
app.py                 Rotas, validações, consultas e inicialização SQLite
templates/index.html   Painel, filtros e formulário de abertura
templates/ticket_detail.html  Ficha individual do chamado
static/styles.css      Layout responsivo
tests/test_app.py      Testes de rotas e regras principais
docs/guia-de-uso.md    Instruções para percorrer o fluxo local
docs/relatorio-tecnico.md  Arquitetura, modelo de dados e validação
```

## Documentação

- [Guia de uso](docs/guia-de-uso.md)
- [Relatório técnico](docs/relatorio-tecnico.md)

## Banco e dados fictícios

O banco padrão fica em `instance/chamados.db`. A pasta `instance/` e o banco local não são versionados. Para iniciar sem registros de demonstração, defina `LOAD_SAMPLE_DATA=0` antes da primeira execução. Para usar outro arquivo, defina `TICKETS_DATABASE` com o caminho desejado. A variável `PORT` altera a porta do servidor local. Em hospedagem HTTPS, ative `DEMO_READ_ONLY=1` e `SESSION_COOKIE_SECURE=1`, forneça uma `SECRET_KEY` estável e mantenha o modo de depuração desativado.

## Limites desta versão

Esta é uma aplicação de portfólio, não um sistema pronto para operar um service desk real. Ela não possui login, perfis de acesso, notificações, anexos, trilha de auditoria, política de retenção nem banco de dados gerenciado. Uma publicação pública deve usar dados fictícios e ser configurada como demonstração; para uso real, implementar autenticação e autorização, HTTPS, proteção contra abuso, backups, registro de auditoria e armazenamento persistente.

## Tecnologias

Python · Flask · SQLite · HTML · CSS · unittest
