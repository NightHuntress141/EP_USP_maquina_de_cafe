# Pendências após a integração do lado operador

Esta lista considera entregues os serviços de alteração de preço, manutenção,
limpeza, consulta de estoque, reabastecimento, relatório e login.

## 1. Implementar os serviços do cliente

Os serviços abaixo ainda são contratos com `NotImplementedError`:

- [ ] **Cardápio:** implementar `produto_service.listar_produtos()`, consultando
      preços em centavos, tempos de preparo e disponibilidade por receita/estoque.
- [ ] **Estado da máquina:** implementar `status_service.obter_status()`,
      retornando o estado operacional e o crédito persistidos.
- [ ] **Inserção de crédito:** implementar `credito_service.adicionar_credito()`,
      respeitando as denominações exatas e o limite acumulado de R$ 50,00.
- [ ] **Troco:** implementar `credito_service.devolver_troco()`, devolvendo todo o
      saldo e zerando o crédito na mesma transação.
- [ ] **Criação de pedidos:** implementar `pedido_service.criar_pedido()`,
      validando estado, bebida, saldo, ingredientes, açúcar e copo; debitar crédito
      e estoque e registrar o pedido atomicamente.
- [ ] **Consulta de pedidos:** implementar `pedido_service.consultar_pedido()`,
      calculando a conclusão pela previsão de término, sem timer.
- [ ] **Cancelamento:** implementar `pedido_service.cancelar_pedido()`, permitindo
      cancelar somente pedidos em preparo, devolvendo o valor ao crédito e
      mantendo consumidos os ingredientes já descontados.

Registrar os movimentos de crédito correspondentes às operações. Manter SQL nos
repositórios, regras nos serviços e controllers limitados à interface HTTP.

## 2. Integrar pedidos ao estado da máquina e à limpeza

- [ ] Manter coerência entre estado da máquina e situação dos pedidos.
- [ ] Incrementar o contador uma única vez por pedido concluído.
- [ ] Ao atingir 30 preparos, colocar a máquina em `AGUARDANDO_LIMPEZA`.
- [ ] Impedir compras durante preparo, manutenção ou espera por limpeza.
- [ ] Impedir que consultas repetidas/concorrentes concluam o mesmo pedido ou
      incrementem o contador mais de uma vez.
- [ ] Garantir que a corrida entre conclusão e cancelamento efetive apenas um
      resultado, preservando crédito, estoque e estado.
- [ ] Integrar o fluxo já implementado de manutenção e limpeza à conclusão dos
      pedidos, sem duplicar sua lógica.

## 3. Corrigir os limites do relatório

Os pontos abaixo permanecem necessários se não forem corrigidos antes da
integração. Não é necessário reimplementar o relatório.

- [ ] Unificar a normalização entre controller e serviço. Pela política atual,
      datas sem fuso são UTC; um intervalo misturando datas com/sem fuso deve
      funcionar quando for válido.
- [ ] Tratar datas que ultrapassam os limites de datetime ao converter para UTC,
      devolvendo erro de entrada em vez de HTTP 500.
- [ ] Filtrar o período antes de converter preços históricos, para que um registro
      monetário inválido fora do intervalo não derrube a consulta.
- [ ] Traduzir falhas de conversão de vendas incluídas para erro de persistência
      padronizado, sem ignorar registros inválidos silenciosamente.
- [ ] Evitar carregar todo o histórico concluído para consultar um período curto,
      preservando a política de timezone e os limites inclusivos.

Adicionar testes HTTP para datas com/sem fuso, extremos de datetime e registros
monetários inválidos dentro/fora do período.

## 4. Consolidar os dados para os serviços restantes

- [ ] Definir representação monetária exata do saldo, de `pedido.preco_cobrado`
      e dos movimentos de crédito. O preço atual de produto já usa
      `preco_centavos`; não usar float para cálculos financeiros.
- [ ] Se a representação persistida mudar, incluir migração com backup, validação,
      preservação de referências e rollback; não arredondar dados inválidos
      silenciosamente.
- [ ] Implementar geração de IDs para pedidos e movimentos de crédito. No SQLite,
      `INT PRIMARY KEY` não fornece autoincremento; preservar segurança sob concorrência.
- [ ] Confirmar com o grupo os contratos já adotados: alerta inclusivo
      (`quantidade_atual <= nivel_alerta`), quantidades inteiras e datas sem fuso em UTC.
- [ ] Alinhar exemplos/DTOs de reabastecimento à política de inteiros para todos
      os insumos. Copos permanecem obrigatoriamente em unidades inteiras.
- [ ] Confirmar o uso de `pedido.criado_em` como referência temporal da venda.
      Somente se for exigida conclusão real: adicionar `finalizado_em` por
      migração e preenchê-lo na conclusão. Não inventar timestamps históricos.
- [ ] Se o grupo decidir aceitar frações de outros insumos, definir unidades e
      precisão e incluir migração antes de mudar a validação atual.

## 5. Validar o sistema completo com banco real

Os testes existentes do operador não substituem a integração do fluxo do cliente.

- [ ] Cardápio → crédito → compra → preparo concluído → saldo → troco.
- [ ] Cancelamento em preparo, com devolução correta e sem restaurar ingredientes.
- [ ] Recusa por saldo insuficiente, falta de ingrediente/copo ou estado incompatível.
- [ ] Trigésimo preparo → bloqueio por limpeza → manutenção → limpeza → operação normal.
- [ ] Login → acesso Bearer → reposição → estoque → compra usando o estoque atualizado.
- [ ] Relatório refletindo vendas concluídas, excluindo cancelamentos e preservando
      o preço histórico após alteração do preço atual.
- [ ] Rollback quando falhar uma gravação relacionada.
- [ ] Concorrência de compras, consultas de conclusão e cancelamentos.
- [ ] Persistência de saldo, estoque, pedidos e estado após reiniciar a API.
- [ ] Atualizar README, docstrings e documentação gerada conforme os serviços
      deixarem de ser stubs.
- [ ] Executar lint, formatação, testes, compatibilidade de dependências e auditoria.

## 6. Preparar a execução e a exposição do sistema

- [ ] Inicializar um banco novo ou migrar um banco existente conforme
      `database/README.md`; não reaplicar seed em banco populado.
- [ ] Configurar `DATABASE_PATH`, `OPERATOR_USER`, `OPERATOR_PASSWORD` e
      `OPERATOR_TOKEN` com valores privados, sem fallback público.
- [ ] Configurar `CORS_ORIGINS` caso o frontend utilize outra origem.
- [ ] Para acesso fora do desenvolvimento local, configurar HTTPS e limitação
      de tentativas de login na aplicação ou no proxy.
