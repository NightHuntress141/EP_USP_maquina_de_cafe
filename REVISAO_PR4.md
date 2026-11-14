# Revisão independente do PR #4

## Referência revisada

- PR: [#4 — Implementa serviços do operador e corrige arquitetura e segurança](https://github.com/NightHuntress141/EP_USP_maquina_de_cafe/pull/4)
- HEAD conferido: `9fbb1a7ecbae61b4cb8428d0bad61404387b2928`
- Base: `main` (PR ainda aberto, sem merge)
- CI no HEAD: check `testes` concluído com sucesso em 2026-11-14
- Branch desta implementação: `feat/operador-completo`, criada de
  `origin/feat/servicos-operador` porque o PR #4 ainda não estava na `main`.
  A dependência deve ser conferida novamente contra a `main` após o merge.

A revisão não considerou o CI verde como aprovação. Abaixo estão os achados com
arquivo/linha do HEAD revisado, cenário, impacto e correção sugerida. A coluna
"Situação" indica o que foi tratado nesta branch e o que permanece pendente de
acordo com o grupo.

## Achados

### A1 — Serviços do operador ainda eram stubs (alto; tratado)

- Evidências: `app/services/estoque_service.py:12-23` e `:26-47`;
  `app/services/relatorio_service.py:13-31`;
  `app/services/operador_service.py:10-29`.
- Cenário: `GET /operador/estoque`, `POST /operador/estoque/reabastecer`,
  `GET /operador/relatorio` e `POST /operador/login` chegavam ao serviço e
  recebiam `NotImplementedError`; sem mocks, as rotas não funcionavam.
- Impacto: quatro contratos anunciados no README/Swagger não eram utilizáveis.
- Correção: implementar os serviços com validação de domínio, persistência e
  testes reais. Situação: implementado nesta branch. Permanecem como stubs
  apenas os serviços de cliente fora do escopo (`credito`, `pedido`,
  `listar_produtos`, `status`).

### A2 — Frações no DTO conflitavam com colunas `INT` (médio; contrato decidido)

- Evidências: `app/schemas/estoque.py:60-66` aceita frações para qualquer item,
  mas `database/schema.sql:22` declara `quantidade_atual INT` e `:73` declara
  `reabastecimento.quantidade INT`.
- Cenário: enviar `{"item":"agua","quantidade":1.5}`. O DTO aceita e o SQLite
  pode armazenar REAL por afinidade de tipo, sem garantia de integralidade.
- Impacto: perda de previsibilidade e eventual divergência entre DTO, banco e
  relatórios de estoque. Não era seguro truncar nem arredondar.
- Correção: até existir migração acordada para unidades menores, o serviço
  recusa frações para todos os itens com `OperacaoInvalidaError` (HTTP 400),
  além de recusar booleanos/textos antes da delegação. Decisão documentada no
  README e em `database/README.md`. Se o grupo optar por frações, será necessária
  migração explícita do schema (ou representação em unidades menores) e testes.
  Situação: política implementada; mudança de contrato para frações permanece
  pendente de acordo.

### A3 — Relatório sem `finalizado_em` não tinha semântica temporal definida (médio; decisão documentada)

- Evidência: `database/schema.sql:43-54`. A tabela `pedido` possui `criado_em` e
  `previsao_termino`, mas a coluna de conclusão real está comentada.
- Cenário: gerar relatório de vendas de um período. Sem uma regra, poder-se-ia
  filtrar por criação, previsão ou inventar uma data de conclusão.
- Impacto: risco de relatório incorreto e divergência com o serviço de pedidos.
- Correção: nesta entrega o relatório usa `pedido.criado_em` como instante da
  venda, com a limitação documentada. Para conclusão real, é necessário combinar
  e criar `finalizado_em` (migração) e preenchê-la no serviço de pedidos.
  Situação: semântica provisória documentada; migração pendente de decisão.

### A4 — `preco_cobrado` permanecia `NUMERIC` e podia induzir soma de floats (médio; tratado)

- Evidência: `database/schema.sql:47`.
- Cenário: relatório com preços como `0.10` e `0.20`; um `SUM`/soma em float pode
  produzir `0.30000000000000004`.
- Impacto: faturamento com centavos incorretos.
- Correção: o relatório lê `preco_cobrado` com `Decimal`, converte cada valor
  para centavos inteiros com a mesma validação do preço atual e soma inteiros.
  Não foi feita migração histórica dos pedidos/movimentos, o que continua sendo
  uma pendência separada. Situação: acumulação exata implementada e testada.

### A5 — `validar_schema` não conhecia `pedido`/`reabastecimento` (médio; tratado)

- Evidência: `app/repositories/operador_repository.py:113` verificava apenas
  `limpeza`, `ingrediente` e `receita_item`.
- Cenário: banco parcialmente inicializado sem `pedido` ou
  `reabastecimento`; a API iniciava e falhava somente na operação.
- Impacto: erro tardio (500/503) em vez de recusa de startup.
- Correção: as tabelas `pedido` e `reabastecimento` passaram a ser validadas no
  startup. Situação: implementado.

### A6 — `inicializar` deixava arquivo parcial quando a carga falhava (médio; tratado)

- Evidência: `app/repositories/database.py:29-40` criava o arquivo com `xb` e,
  se a leitura de `schema.sql`/`seed.sql` ou a execução falhasse, mantinha o
  arquivo vazio/parcial.
- Cenário: falha de leitura do seed após a criação do arquivo. Repetir
  `init` recebe `FileExistsError` e exige remoção manual.
- Impacto: inicialização não idempotente em caso de erro e risco de confundir um
  banco parcial com um banco válido.
- Correção: fechar a conexão e remover somente o arquivo criado por esta chamada
  quando a carga falha; teste adicionado. A proteção contra sobrescrever banco
  existente permanece. Situação: implementado.

### A7 — Coerção laxa de booleanos/textos em `quantidade` (baixo; tratado)

- Evidência: `app/schemas/estoque.py:60-66`.
- Cenário: `POST /operador/estoque/reabastecer` com `{"quantidade": true}` era
  convertido para `1.0` pelo Pydantic; `"10"` também era convertido para `10.0`.
- Impacto: escrita não intencional e aceitação de tipos fora do contrato JSON.
- Correção: validador `mode="before"` aceita somente `int`, `float` ou `Decimal`
  (sem booleanos/textos) e testes HTTP cobrem os casos. Situação: implementado.

### A8 — Startup usava `BEGIN IMMEDIATE` apenas para validar o banco (baixo; tratado)

- Evidência: `app/repositories/operador_repository.py:126-145` e `:162-165`.
  `validar_banco()` abria uma transação de escrita só para ler schema e máquina.
- Cenário: subir a API enquanto outro processo escreve; a validação podia bloquear
  ou receber lock desnecessário antes de qualquer escrita.
- Impacto: startup desnecessariamente acoplado ao lock de escrita.
- Correção: contexto `transacao_leitura()` com conexão `mode=ro` e transação
  única; usado por estoque, relatório e validação de startup. Situação:
  implementado.

### A9 — Credenciais do login não eram validadas na configuração (médio; tratado)

- Evidência: `app/main.py:36-37` validava apenas `OPERATOR_TOKEN`; não havia
  validação de `OPERATOR_USER`/`OPERATOR_PASSWORD`, coerente com o stub de login.
- Cenário: subir a API sem usuário/senha e só descobrir na tentativa de login.
- Impacto: login indisponível em produção sem falha explícita de configuração.
- Correção: `credenciais_operador()` centraliza a validação sem fallback; o
  startup e o login a utilizam. Configuração ausente no login retorna 503
  `SERVICO_INDISPONIVEL` sem expor valores. Situação: implementado.

### A10 — Todo `OperationalError` era tratado como banco indisponível (baixo; tratado)

- Evidência: `app/repositories/operador_repository.py:147-152` convertia qualquer
  `sqlite3.OperationalError` em `BancoIndisponivelError` (503).
- Cenário: erro de SQL/programação durante uma operação seria mascarado como
  indisponibilidade temporária.
- Impacto: diagnóstico incorreto e respostas 503 para falhas internas.
- Correção: apenas códigos de indisponibilidade (`SQLITE_BUSY`, `SQLITE_LOCKED`,
  `SQLITE_CANTOPEN`, `SQLITE_IOERR`, `SQLITE_NOTADB`, `SQLITE_PROTOCOL`) viram
  503; os demais viram `PersistenciaError` (500). Situação: implementado.

## Decisões de contrato tomadas nesta entrega

| Tema | Decisão | Onde está documentado/testado |
| --- | --- | --- |
| Alerta de estoque | `nivel_baixo = quantidade_atual <= nivel_alerta` | README, docstring de `estoque_service` e teste de fronteira |
| Frações de insumo | Recusadas no serviço enquanto o schema for inteiro; sem truncamento | README, `database/README.md`, testes de serviço/HTTP |
| Instante da venda | `pedido.criado_em`, por ausência de `finalizado_em` | README, `database/README.md`, docstring de `relatorio_service` |
| Timezone | Datas sem fuso são UTC; comparações em UTC | README, docstring e teste com offset |
| Dinheiro histórico | `preco_cobrado` em Decimal convertido para centavos | README, docstring e teste de soma exata |
| Login | Configuração obrigatória no startup e no login, sem fallback | README, `config.py`, `operador_service`, testes |

## Verificação executada

- Revisão de contratos, camadas, transações, migração, CORS, logs e testes do PR.
- Suíte no HEAD revisado: **138 testes** passando.
- Suíte nesta branch: **192 testes** passando.
- `python3 -m ruff check app tests`: sem erros.
- `python3 -m ruff format --check app tests`: sem diferenças.
- `pip check`: sem conflitos.
- `pip-audit -r constraints.txt --no-deps --disable-pip`: sem vulnerabilidades
  conhecidas nas versões fixadas consultadas.
- Validação executada em Python 3.14/Linux/WSL2; o CI do projeto usa Python 3.12.
  Isso não substitui teste de implantação.

## Pendências que não foram assumidas como concluídas

- Serviços de cliente: crédito, pedidos, listagem de produtos e status continuam
  como `NotImplementedError`.
- `finalizado_em`/migração para conclusão real de pedidos.
- Migração de valores históricos de `preco_cobrado` e `movimento_credito` para
  centavos.
- Definição do grupo sobre aceitar frações de insumos (exigiria migração e
  representação em unidades menores).
- Limitação de tentativas de login e HTTPS na implantação ficam como requisitos
  operacionais/proxy.
