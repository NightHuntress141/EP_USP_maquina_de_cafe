# API REST de uma Máquina de Café

[![CI](https://github.com/NightHuntress141/EP_USP_maquina_de_cafe/actions/workflows/ci.yml/badge.svg)](https://github.com/NightHuntress141/EP_USP_maquina_de_cafe/actions/workflows/ci.yml)

Back-end de uma máquina de café automática desenvolvido em **Python + FastAPI**.
A máquina física é apenas um cliente: toda a inteligência (cardápio, estoque,
pagamento, preparo e manutenção) reside nesta API.

> **Escopo atual desta entrega:** camada de **API (controllers)** do fluxo do
> **cliente**, com schemas Pydantic, tratamento padronizado de erros, testes,
> documentação e a estrutura de pastas do projeto. As regras de negócio e a
> persistência (camadas de serviço e repositório) são de responsabilidade dos
> demais integrantes e estão representadas aqui por *stubs* com a assinatura dos
> métodos.

## Arquitetura em camadas

```
app/
├── main.py            # FastAPI, CORS e handlers globais de erro
├── api/
│   ├── deps.py        # Dependência de autenticação do operador (RN11)
│   └── client.py      # Endpoints do fluxo do cliente
├── schemas/           # DTOs Pydantic de entrada e saída
│   ├── credito.py
│   ├── erro.py
│   ├── pedido.py
│   ├── produto.py
│   └── status.py
├── services/          # Contrato das regras de negócio (stubs)
│   ├── credito_service.py
│   ├── pedido_service.py
│   ├── produto_service.py
│   └── status_service.py
└── core/
    └── exceptions.py  # Exceções de negócio customizadas
tests/
├── conftest.py
└── test_api_client.py
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

## Tratamento padronizado de erros

O corpo de erro segue o formato `{"erro": SLUG, "mensagem": "..."}`:

| Situação | HTTP | `erro` |
|---|---|---|
| Dados inválidos (valor de crédito, açúcar fora de 0–3) | 400 | `DADOS_INVALIDOS` |
| Crédito insuficiente | 402 | `CREDITO_INSUFICIENTE` |
| Bebida/pedido inexistente | 404 | `BEBIDA_NAO_ENCONTRADA` / `PEDIDO_NAO_ENCONTRADO` |
| Estoque/copo insuficiente ou máquina ocupada | 409 | `ESTOQUE_INSUFICIENTE` / `MAQUINA_OCUPADA` |
| Reabastecimento acima da capacidade | 422 | `CAPACIDADE_EXCEDIDA` |
| Máquina em manutenção ou aguardando limpeza | 503 | `MAQUINA_INDISPONIVEL` |
| Operador sem token válido | 401 | `NAO_AUTORIZADO` |

O mapeamento é centralizado nos *exception handlers* de `app/main.py`.

## Como rodar

```bash
# 1. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Subir a API
uvicorn app.main:app --reload
```

- Documentação interativa (Swagger UI): http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## Como testar

```bash
source .venv/bin/activate
pytest -q
```

Os testes de controller usam o `TestClient` do FastAPI e mockam os serviços com
`unittest.mock.patch`, cobrindo o caminho feliz e cada mapeamento de erro.

## CI/CD (GitHub Actions)

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda a suíte de
testes a cada **push na `main`** e a cada **pull request** direcionado à `main`.
Os passos executados são exatamente os mesmos do fluxo local:

```bash
pip install -r requirements.txt
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

> O módulo `app.api.operator` será incluído automaticamente quando os endpoints
> de operador forem implementados na próxima rodada.

## Autenticação do operador (RN11)

Os endpoints de operador usarão autenticação `Bearer`. O token é comparado com a
variável de ambiente `OPERATOR_TOKEN` (padrão de desenvolvimento:
`senha_padrao_para_dev`). A dependência já está pronta em `app/api/deps.py`.

## Decisões técnicas

- **FastAPI**: tipagem, validação automática e documentação OpenAPI nativa.
- **Snake_case** nos campos JSON (`produto_id`, `credito_restante`), alinhado ao
  padrão do Python/Pydantic.
- **Erros padronizados em `{"erro", "mensagem"}`** via handlers globais, mantendo
  os controllers finos e sem `try/except` repetidos.
- **Validação de entrada no Pydantic** (valores de crédito da RN01, açúcar de 0 a
  3) e HTTP 400 para dados inválidos (em vez do 422 padrão do FastAPI).
- **Services como contrato** (`NotImplementedError`) para respeitar a divisão de
  responsabilidades e permitir testar a API com serviços mockados.

## Observação para o grupo

No cardápio extraído do PDF há divergência entre a tabela e os exemplos de
requisição/resposta (Cappuccino aparece como R$ 6,00 na tabela, mas R$ 6,50 nos
exemplos; Chocolate quente, R$ 6,50 na tabela e R$ 7,00 nos exemplos). Como os
preços são dados de domínio (camada de serviço), isso **não afeta a API**, mas
deve ser alinhado antes de popular o cardápio.
