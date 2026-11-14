-- Schema do banco de dados da máquina de café
-- Coloquei algumas restrições de integridade para garantir que os dados fiquem consistentes,
-- como por exemplo, não permitir que a quantidade atual de um ingrediente seja maior que sua capacidade máxima.

-- Pontos de atenção:
-- preparos_desde_limpeza: é incrementado a cada pedido concluído, e quando atinge 30, a máquina entra em estado AGUARDANDO_LIMPEZA.


CREATE TABLE maquina (   -- ID da nossa máquina = 1, há apenas uma máquina, então não precisamos de uma tabela de máquinas com várias linhas
    id                      INT PRIMARY KEY CHECK (id = 1),
    estado                  VARCHAR(20) NOT NULL
        CHECK (estado IN ('PRONTA','PREPARANDO','AGUARDANDO_LIMPEZA','MANUTENCAO')),
    credito                 NUMERIC(10,2) NOT NULL DEFAULT 0
        CHECK (credito >= 0 AND credito <= 50.00), -- maquina aceita no máximo R$50,00 de crédito
    preparos_desde_limpeza  INT NOT NULL DEFAULT 0 CHECK (preparos_desde_limpeza >= 0)
);

CREATE TABLE ingrediente ( -- AGUA, CAFE, LEITE, CHOCOLATE, ACUCAR, COPOS
    id                INT PRIMARY KEY,
    codigo            VARCHAR(20) NOT NULL UNIQUE,
    unidade           VARCHAR(10) NOT NULL,          -- ml, g, un
    quantidade_atual  INT NOT NULL CHECK (quantidade_atual >= 0 AND (codigo != 'COPOS' OR typeof(quantidade_atual) = 'integer')),
    capacidade_maxima INT NOT NULL CHECK (capacidade_maxima > 0),
    nivel_alerta      INT NOT NULL CHECK (nivel_alerta >= 0),
    CHECK (quantidade_atual <= capacidade_maxima)
);

CREATE TABLE produto (
    id              INT PRIMARY KEY,
    nome            VARCHAR(50) NOT NULL UNIQUE,
    preco_centavos  INTEGER NOT NULL
        CHECK (typeof(preco_centavos) = 'integer' AND preco_centavos BETWEEN 1 AND 9999999999),
    tempo_preparo_s INT NOT NULL CHECK (tempo_preparo_s > 0)
);

CREATE TABLE receita_item (       -- inclui o copo (1 un) como ingrediente
    produto_id     INT NOT NULL REFERENCES produto(id),
    ingrediente_id INT NOT NULL REFERENCES ingrediente(id),
    quantidade     INT NOT NULL CHECK (quantidade > 0), -- quantidade necessária do ingrediente para preparar o produto
    PRIMARY KEY (produto_id, ingrediente_id)
);

CREATE TABLE pedido (
    id               INT PRIMARY KEY,   -- AUTO_INCREMENT/SERIAL/IDENTITY
    produto_id       INT NOT NULL REFERENCES produto(id),
    acucar_porcoes   INT NOT NULL CHECK (acucar_porcoes BETWEEN 0 AND 3),
    preco_cobrado    NUMERIC(10,2) NOT NULL CHECK (preco_cobrado > 0),
    status           VARCHAR(15) NOT NULL
        CHECK (status IN ('EM_PREPARO','CONCLUIDO','CANCELADO')),
    criado_em        TIMESTAMP NOT NULL,
    previsao_termino TIMESTAMP NOT NULL
    -- finalizado_em    TIMESTAMP NULL   -- será preenchido quando o pedido for concluído ou cancelado de fato,
    -- mas não é necessário para o funcionamento da máquina, então deixei comentado
);

-- Índices para melhorar a performance das consultas, deletar caso não necessário
CREATE INDEX idx_pedido_produto ON pedido(produto_id);
CREATE INDEX idx_pedido_status ON pedido(status);
CREATE INDEX idx_pedido_criado ON pedido(criado_em);

CREATE TABLE movimento_credito (  -- auditoria do crédito
    id         INT PRIMARY KEY,
    pedido_id  INT NULL REFERENCES pedido(id),
    tipo       VARCHAR(20) NOT NULL
        CHECK (tipo IN ('INSERCAO','DEBITO_PEDIDO','ESTORNO_CANCELAMENTO','TROCO')),
    valor      NUMERIC(10,2) NOT NULL CHECK (valor > 0),
    criado_em  TIMESTAMP NOT NULL
);

CREATE TABLE reabastecimento (
    id             INT PRIMARY KEY,
    ingrediente_id INT NOT NULL REFERENCES ingrediente(id),
    quantidade     INT NOT NULL CHECK (quantidade > 0),
    criado_em      TIMESTAMP NOT NULL
);

CREATE TABLE limpeza (
    id           INT PRIMARY KEY,
    realizada_em TIMESTAMP NOT NULL
);
