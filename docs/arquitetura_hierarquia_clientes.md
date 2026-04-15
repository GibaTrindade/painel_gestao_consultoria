# Hierarquia de Clientes

## Objetivo
Evoluir `Cliente` de uma estrutura plana para uma estrutura hierarquica que permita consolidacao por rede, prefeitura, secretaria e unidades operacionais sem duplicar modelos.

## Motivacao
Hoje o sistema responde bem por unidade isolada, mas ainda nao consegue responder com qualidade:

- qual unidade puxou o resultado da secretaria para baixo
- como consolidar varias UPAs de uma prefeitura
- como navegar entre visao executiva e operacional mantendo a mesma base de dados

## Direcao adotada
O modelo `Cliente` passa a suportar um relacionamento com ele mesmo:

- `parent`: cliente pai
- `children`: clientes filhos

Exemplo:

- Prefeitura de Exemplo
  - Secretaria de Saude
    - UPA Centro
    - UPA Norte

## Regras de modelagem

1. Todo cliente pode ser raiz ou filho de outro cliente.
2. O sistema nao permite ciclos na hierarquia.
3. Clientes atuais sao tratados como raizes na migracao inicial.
4. O codigo de acesso continua existindo por cliente.
5. O contexto selecionado passa a representar um subtree inteiro:
   - se o usuario escolhe uma secretaria, as consultas passam a considerar a secretaria e suas unidades filhas
   - se escolhe uma UPA, a leitura continua local

## Impacto esperado nas consultas

Quando um `cliente_atual` for selecionado, as consultas passam a trabalhar com:

- `cliente_ids_contexto = cliente_atual + descendentes`

Isso permite adaptar as telas atuais sem ainda criar um novo dashboard consolidado.

## Escopo desta branch

1. Documentar a proposta
2. Implementar `parent` em `Cliente`
3. Migrar os dados atuais mantendo clientes existentes como raizes
4. Adaptar contexto e consultas para subtree
5. Preparar o sistema para telas consolidadas futuras

## O que fica para a proxima etapa

- breadcrumbs e navegação hierarquica mais rica
- dashboards consolidados por rede
- comparativos entre unidades irmas
- regras mais finas de permissao por nivel hierarquico

