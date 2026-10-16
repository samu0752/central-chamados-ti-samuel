# Guia de uso — Central de Chamados de TI

Este guia explica como iniciar a aplicação local e percorrer o fluxo de atendimento usando os dados fictícios incluídos no projeto.

## 1. Iniciar a aplicação

Abra o terminal na pasta do projeto e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

No primeiro acesso, abra `http://127.0.0.1:5000/`. O painel cria o banco SQLite em `instance/chamados.db` e carrega seis solicitações de exemplo quando o banco está vazio. Para parar o servidor, volte ao terminal e pressione `Ctrl+C`.

## 2. Entender o painel

- **Chamados ativos** reúne os estados Aberto, Em atendimento e Aguardando usuário.
- **Resolvidos** conta os estados Resolvido e Fechado.
- **Tempo médio de resolução** considera o tempo corrido entre a abertura e a conclusão de cada chamado com data de resolução.
- **Total registrado** mostra a quantidade completa de registros.
- Os gráficos de status e prioridade usam todos os registros ativos e não mudam com os filtros da tabela.

Os exemplos simulam uma fila para demonstrar os indicadores. O resultado é didático, não corresponde a uma operação real nem representa uma meta de SLA.

## 3. Encontrar uma solicitação

Na lista, pesquise por protocolo, nome, título ou e-mail. Combine a busca com um ou mais filtros de status, categoria e prioridade. Use **Limpar** para voltar à lista sem filtros. A tabela começa pelos registros mais recentes; clique no título para abrir a ficha completa.

## 4. Registrar e acompanhar

Na seção **Registrar novo chamado**, informe o solicitante, e-mail, título, categoria, prioridade e descrição. Campos obrigatórios são marcados no formulário, e o servidor confere novamente o conteúdo antes de salvar. O chamado recebe protocolo e estado inicial Aberto.

Para avançar o atendimento, altere o status pela lista ou abra a ficha individual. A conclusão registra a hora de resolução; voltar para um estado ativo limpa essa data. A versão atual não mantém uma trilha de mudanças anteriores.

## 5. Testar uma sequência

1. Abra um chamado de exemplo e confira a descrição e os dados do solicitante.
2. Mude o status para **Em atendimento** e salve.
3. Volte à lista e confirme a alteração.
4. Pesquise pelo protocolo e combine o resultado com um filtro de prioridade.
5. Mude o status para **Resolvido** e observe a contagem de ativos, a contagem de resolvidos e o tempo médio.
6. Registre um chamado novo e confira o protocolo criado.

## 6. Encerrar e reiniciar

`Ctrl+C` encerra o servidor local. Os chamados permanecem no arquivo SQLite, pois o banco é persistente enquanto a pasta local existir. Para zerar os dados, pare a aplicação e remova manualmente `instance/chamados.db`; ao iniciar novamente, a carga de exemplo será criada. Faça isso somente se quiser descartar os registros locais.

## 7. Mensagens comuns

- **O navegador não abre a página:** confirme que `python app.py` continua em execução e tente o endereço `http://127.0.0.1:5000/`.
- **A porta está ocupada:** feche outro servidor local ou defina `PORT=5001` antes de iniciar o app.
- **A sessão do formulário expirou:** atualize a página e envie o formulário novamente. O token CSRF protege operações de gravação.
- **Não aparecem os exemplos:** a carga de demonstração só é adicionada quando o banco está vazio. `LOAD_SAMPLE_DATA=0` desativa a carga inicial.
- **O formulário não aparece ou não aceita alterações:** verifique se `DEMO_READ_ONLY=1` foi configurado. Esse modo é recomendado para uma publicação pública.

Use somente dados fictícios na demonstração. O aplicativo não possui login nem controles para uso com chamados reais.
