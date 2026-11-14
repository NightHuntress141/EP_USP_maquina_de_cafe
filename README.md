# API REST de uma Máquina de Café

[![CI](https://github.com/NightHuntress141/EP_USP_maquina_de_cafe/actions/workflows/ci.yml/badge.svg)](https://github.com/NightHuntress141/EP_USP_maquina_de_cafe/actions/workflows/ci.yml)

Back-end de uma máquina de café automática desenvolvido em **Python + FastAPI**.
A máquina física é apenas um cliente: toda a inteligência (cardápio, estoque,
pagamento, preparo e manutenção) reside nesta API.

> **Escopo atual:** controllers de cliente e operador, com serviços reais de
> alteração de preço, manutenção, limpeza, estoque, relatório e login do
> operador usando SQLite. Os serviços de cliente (crédito, pedidos, listagem de
> produtos e status) continuam como contratos (`NotImplementedError`). A
> aplicação não deve ser apresentada como um backend completo.

## Arquitetura em camadas

```
app/
├── main.py            # FastAPI, CORS e handlers globais de erro
├── api/
│   ├── deps.py        # Dependência de autenticação do operador (RN11)
│   ├── client.py      # Endpoints do fluxo do cliente
│   └── operator.py    # Endpoints do fluxo do operador
├── schemas/           # DTOs Pydantic de entrada e saída
│   ├── credito.py
│   ├── erro.py
│   ├── estoque.py
│   ├── operador.py
│   ├── pedido.py
│   ├── produto.py
│   ├── relatorio.py
│   └── status.py
├── repositories/      # SQLite, unidade de trabalho e migração
├── services/          # Regras implementadas e contratos pendentes
│   ├── credito_service.py
│   ├── estoque_service.py
│   ├── operador_service.py
│   ├── pedido_service.py
│   ├── produto_service.py
│   ├── relatorio_service.py
│   └── status_service.py
└── core/
    └── exceptions.py  # Exceções de negócio customizadas
tests/
├── conftest.py
├── test_api_client.py
├── test_api_operator.py
├── test_regressoes.py
├── test_services_operador.py
└── test_servicos_estoque_relatorio.py
```

A camada de **API** apenas valida entradas (Pydantic), delega aos **serviços** e
traduz as exceções de negócio em códigos HTTP. Nenhuma regra de negócio fica nos
controllers.

## Endpoints do cliente (implementados)

| Método | Rota | Descrição | Sucesso |
|---|---|---|---|
| GET | `/produtos` | Cardápio (preço, tempo, disponibilidade) | 200 |
| GET | `/status` | Estado da máquina e crédito atual | 200 |
| POST | `/credito` | Insere crédito (RN01) | 200 |
| POST | `/troco` | Devolve todo o crédito restante (RN06) | 200 |
| POST | `/pedidos` | Cria um pedido (RN02–RN04) | 201 |
| GET | `/pedidos/{pedido_id}` | Consulta o status de um pedido | 200 |
| POST | `/pedidos/{pedido_id}/cancelar` | Cancela um pedido em preparo (RN05) | 200 |

## Endpoints do operador (implementados)

Exceto o login, todas as rotas exigem `Authorization: Bearer <token>`.

| Método | Rota | Autenticação | Descrição | Sucesso |
|---|---|---|---|---|
| POST | `/operador/login` | pública | Autentica o operador e devolve o token (RN11) | 200 |
| GET | `/operador/estoque` | Bearer | Consulta níveis e capacidades dos reservatórios (RN09) | 200 |
| POST | `/operador/estoque/reabastecer` | Bearer | Reabastece um reservatório (RN09) | 200 |
| PUT | `/operador/produtos/{produto_id}/preco` | Bearer | Altera o preço de uma bebida (RN10) | 200 |
| POST | `/operador/manutencao` | Bearer | Entra ou sai do modo de manutenção (RN08) | 200 |
| POST | `/operador/limpeza` | Bearer | Registra a limpeza e zera o contador (RN07) | 200 |
| GET | `/operador/relatorio` | Bearer | Relatório de vendas por período (RN12) | 200 |

O relatório recebe `inicio` e `fim` como *query parameters* no formato ISO 8601;
períodos com `inicio > fim` são recusados com HTTP 400.

## Tratamento padronizado de erros

O corpo de erro segue o formato `{"erro": SLUG, "mensagem": "..."}`:

| Situação | HTTP | `erro` |
|---|---|---|
| Dados inválidos (valor de crédito, açúcar fora de 0–3) | 400 | `DADOS_INVALIDOS` |
| Crédito insuficiente | 402 | `CREDITO_INSUFICIENTE` |
| Bebida/pedido inexistente | 404 | `BEBIDA_NAO_ENCONTRADA` / `PEDIDO_NAO_ENCONTRADO` |
| Estoque/copo insuficiente ou máquina ocupada | 409 | `ESTOQUE_INSUFICIENTE` / `MAQUINA_OCUPADA` |
| Pedido que não está mais em preparo | 409 | `PEDIDO_NAO_CANCELAVEL` |
| Operação incompatível com o estado da máquina | 409 | `ESTADO_INVALIDO` |
| Reabastecimento acima da capacidade | 422 | `CAPACIDADE_EXCEDIDA` |
| Máquina em manutenção ou aguardando limpeza | 503 | `MAQUINA_INDISPONIVEL` |
| Operador sem token válido ou credenciais inválidas | 401 | `NAO_AUTORIZADO` |
| Autenticação do operador não configurada | 503 | `SERVICO_INDISPONIVEL` |
| Banco ausente, não inicializado ou temporariamente bloqueado | 503 | `BANCO_INDISPONIVEL` |
| Falha interna de persistência | 500 | `ERRO_INTERNO` |

O mapeamento é centralizado nos *exception handlers* de `app/main.py`.

## Como rodar

```bash
# 1. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Configurar autenticação e inicializar um banco novo
export OPERATOR_USER="operador"
export OPERATOR_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
export OPERATOR_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m app.repositories.database init

# 4. Subir a API
uvicorn app.main:app --reload
```

- Documentação interativa (Swagger UI): http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## Como testar

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Os testes de controller usam o `TestClient` do FastAPI e mockam os serviços com
`unittest.mock.patch`, cobrindo o caminho feliz e cada mapeamento de erro.

## CI/CD (GitHub Actions)

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda a suíte de
testes a cada **push na `main`** e a cada **pull request** direcionado à `main`.
Os passos executados são exatamente os mesmos do fluxo local:

```bash
pip install -r requirements-dev.txt
ruff check app tests
pytest -q
```

Se algum teste falhar, o check `testes` fica vermelho e o merge fica sinalizado
como não apto. Para **bloquear** o merge de fato, ative a proteção de branch:

1. GitHub → **Settings** → **Branches** → **Add branch protection rule**.
2. Em *Branch name pattern*, informe `main`.
3. Marque **Require status checks to pass before merging** e selecione o check
   `testes`.

> A proteção de branch é uma configuração do GitHub (não versionada em arquivo),
> por isso precisa ser feita uma vez pela pessoa administradora do repositório.

## Documentação (Swagger + pdoc)

- **Swagger/OpenAPI**: gerado automaticamente pelo FastAPI em `/docs`.
- **pdoc**: as docstrings de classes e métodos são publicadas como um site HTML
  navegável (sidebar, busca e tema claro/escuro) em
  [`docs/index.html`](docs/index.html).

### Regenerar a documentação (pdoc)

A ferramenta está declarada em `requirements-dev.txt`:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt

rm -rf docs
pdoc -o docs --docformat google app
cp docs/app.html docs/index.html   # index.html como página inicial
```

O pdoc percorre a árvore do pacote `app` automaticamente, gerando a sidebar de
navegação e uma página por módulo. A página inicial inclui o conteúdo deste
README (via `.. include::` na docstring do pacote `app`).

Depois, abra [`docs/index.html`](docs/index.html) no navegador.

## Autenticação do operador (RN11)

O contrato do `POST /operador/login` é **público**: recebe `usuario` e `senha`, deverá comparar com as
variáveis de ambiente `OPERATOR_USER` e `OPERATOR_PASSWORD` e devolve o token de
`OPERATOR_TOKEN` no corpo `{"token": "...", "tipo": "bearer"}`.

Todos os demais endpoints de `/operador` são **protegidos** e exigem o cabeçalho:

```http
Authorization: Bearer <token>
```

| Variável | Configuração |
|---|---|
| `OPERATOR_USER` | usuário do operador, obrigatório e sem padrão público |
| `OPERATOR_PASSWORD` | senha do operador, obrigatória e sem padrão público |
| `OPERATOR_TOKEN` | segredo Bearer obrigatório, sem padrão público |

A validação do token é feita pela dependência `get_current_operator` em
`app/api/deps.py`. No Swagger (`/docs`), use o botão **Authorize** e informe o
token para chamar as rotas protegidas. Credenciais inválidas ou token ausente
retornam HTTP 401 com `erro = "NAO_AUTORIZADO"`. A API recusa iniciar sem as três
variáveis de autenticação ou com banco não inicializado/migrado. O login compara
usuário e senha com `secrets.compare_digest` e devolve exatamente o
`OPERATOR_TOKEN` aceito pelo Bearer.

## Decisões técnicas

- **FastAPI**: tipagem, validação automática e documentação OpenAPI nativa.
- **Snake_case** nos campos JSON (`produto_id`, `credito_restante`), alinhado ao
  padrão do Python/Pydantic.
- **Erros padronizados em `{"erro", "mensagem"}`** via handlers globais, mantendo
  os controllers finos e sem `try/except` repetidos.
- **Validação de entrada no Pydantic** (valores de crédito da RN01, açúcar de 0 a
  3) e HTTP 400 para dados inválidos (em vez do 422 padrão do FastAPI).
- **Serviços pendentes como contratos** (`NotImplementedError`); os três serviços
  implementados têm testes de integração com persistência real.

## Observação para o grupo

No cardápio extraído do PDF há divergência entre a tabela e os exemplos de
requisição/resposta (Cappuccino aparece como R$ 6,00 na tabela, mas R$ 6,50 nos
exemplos; Chocolate quente, R$ 6,50 na tabela e R$ 7,00 nos exemplos). Como os
preços são dados de domínio (camada de serviço), isso **não afeta a API**, mas
deve ser alinhado antes de popular o cardápio.

## Persistência e configuração

Consulte [database/README.md](database/README.md) para inicialização e migração.
Preço é validado em reais com Decimal e armazenado em centavos inteiros; o JSON
continua usando reais. Não são aceitos frações de centavo, valores não finitos
ou preços acima de R$ 99.999.999,99. Crédito só aceita as denominações exatas.

Os serviços coordenam regras; somente os repositórios executam SQL. Uma unidade
de trabalho mantém leitura, decisão e gravações na mesma transação. Erros de
persistência são registrados no servidor e devolvidos sem SQL/caminhos internos.

- `DATABASE_PATH`: caminho do banco (padrão: `maquina.db` na raiz do projeto).
- `DATABASE_TIMEOUT_SECONDS`: espera por lock, entre 0 e 30 (padrão: 5).
- `CORS_ORIGINS`: origens HTTP(S) explícitas separadas por vírgula, sem caminhos.
  Por padrão nenhuma origem externa é permitida; cookies não são habilitados.
- `OPERATOR_TOKEN`: segredo obrigatório, sem fallback. Gere um valor aleatório e
  evite compartilhá-lo em código, logs ou URLs. Fora do desenvolvimento local,
  exponha a API somente por HTTPS.

A limpeza exige MANUTENCAO e mantém esse estado. SAIR devolve PRONTA se o contador
for menor que 30; caso contrário, devolve AGUARDANDO_LIMPEZA. O alerta de estoque
usa `quantidade_atual <= nivel_alerta`. O reabastecimento preserva as unidades do
seed (ml, g e un); como o schema atual declara quantidades inteiras e não há
migração acordada para unidades menores, frações são recusadas pelo serviço em
vez de truncadas ou arredondadas silenciosamente.

O relatório de vendas usa `pedido.criado_em` como instante da venda, pois o
schema não possui `finalizado_em`; uma conclusão real exigirá coluna/migração e
integração com o serviço de pedidos. Datas sem fuso são interpretadas como UTC e
as comparações são feitas em UTC. O faturamento usa o `preco_cobrado` histórico,
acumulado em centavos inteiros com Decimal, sem `SUM` de floats.

Os testes incluem HTTP com banco real, rollback, concorrência de reabastecimento,
migração com referências, estoque, relatório, login e validação de configuração.
Não substituem teste de implantação nem a implementação das regras de crédito,
pedido, listagem de produtos e status do cliente.

### Verificações de desenvolvimento

```bash
ruff check app tests
ruff format --check app tests
pytest -q
pip-audit -r constraints.txt --no-deps --disable-pip
```

`requirements.txt` contém somente execução; `requirements-dev.txt` adiciona testes,
documentação, lint e auditoria. `constraints.txt` registra as versões verificadas
no Linux/WSL com Python 3.12. Atualizações devem passar pelos testes e pela auditoria.
A auditoria consulta avisos conhecidos e não comprova ausência de vulnerabilidades.
