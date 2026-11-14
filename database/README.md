# SQLite: inicialização e migração

A API não cria nem migra tabelas automaticamente. O caminho vem de DATABASE_PATH
(padrão: maquina.db na raiz do projeto). Use Python 3.12 com os requisitos instalados.

## Banco novo

Na raiz do projeto:

```bash
python -m app.repositories.database init
```

O comando carrega schema.sql e seed.sql atomicamente e recusa sobrescrever um
arquivo existente. Se a criação falhar, o arquivo pode ficar vazio: inspecione
a causa antes de removê-lo e tentar novamente.

## Banco com o schema anterior

Pare a API e outros escritores e faça backup do arquivo. Depois:

```bash
python -m app.repositories.database migrate
```

A migração substitui produto.preco por produto.preco_centavos (inteiro),
preservando IDs, nomes, tempos de preparo, receitas e referências em pedidos.
Valores sem representação exata em centavos são recusados, sem arredondamento.
Índices/triggers personalizados ou colunas extras exigem migração manual.
A transação reverte tudo se houver falha; repetir após sucesso é permitido.
Os registros históricos de preco_cobrado não são alterados: seu uso será
tratado junto à implementação de pedidos/relatórios.

COPOS exige quantidade atual inteira, tanto em bancos novos como migrados.
A unidade de trabalho ativa foreign_keys, serializa escritas com BEGIN IMMEDIATE
e não cria arquivo vazio quando o caminho do banco estiver incorreto.

Os SQLs enviados pelo grupo foram adaptados somente para preço exato em centavos
e integridade de COPOS. Bancos locais continuam ignorados pelo Git.
