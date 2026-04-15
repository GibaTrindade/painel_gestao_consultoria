# Visao Geral do Sistema de Monitoramento de Metas

## Proposito do produto
O sistema foi desenhado para ajudar gestores a sair do acompanhamento superficial de metas e entrar em uma leitura gerencial mais forte da operacao.

Em vez de apenas mostrar se a meta foi ou nao atingida, o app permite entender:

- o que esta abaixo do esperado
- onde o problema esta acontecendo
- quem esta impactando o resultado
- quais acoes de melhoria foram criadas
- se essas acoes estao gerando impacto operacional real
- quais gargalos estao aparecendo com mais frequencia

Em resumo, o produto combina operacao + analise + acompanhamento gerencial.

## O que o sistema hoje e capaz de fazer

### 1. Organizar a operacao por niveis
O sistema suporta contextos hierarquicos de organizacao, por exemplo:

- Prefeitura
- Secretaria
- UPA
- Posto
- Unidade operacional
- Empresa

Na pratica, isso significa que e possivel cadastrar uma estrutura como:

- Prefeitura de Nova Esperanca
- Secretaria Municipal de Saude
- UPA Centro NE
- UPA Norte NE

Com isso:

- a unidade operacional registra a execucao do dia a dia
- o nivel pai consolida os resultados dos filhos
- a gestao ganha uma leitura de rede, e nao apenas de uma unidade isolada

### 2. Trabalhar com perfis diferentes de acesso
Hoje o sistema possui tres formas principais de uso:

- Admin da consultoria
- Gestor
- Funcionario

Tambem existe modo hibrido:

- um usuario pode atuar como gestor e como funcionario
- ele troca de modo sem precisar sair e entrar novamente

### 3. Controlar diagnosticos, indicadores, acoes e tarefas
O fluxo principal do sistema hoje e:

1. cadastrar um diagnostico
2. cadastrar indicadores vinculados a esse diagnostico
3. cadastrar acoes de melhoria vinculadas aos indicadores
4. atribuir essas acoes para profissionais ou equipes
5. gerar automaticamente as tarefas dos funcionarios
6. receber os lancamentos diarios dos funcionarios
7. refletir isso automaticamente nos indicadores, dashboards e analises

### 4. Atualizar o indicador automaticamente
O indicador nao depende mais de preenchimento manual de valor atual.

Hoje a logica e:

- o funcionario informa o que realizou
- os registros diarios alimentam as tarefas
- as tarefas alimentam as acoes
- as acoes alimentam os indicadores

Isso reduz retrabalho e aumenta confiabilidade operacional.

### 5. Manter historico de metas por vigencia
As metas dos indicadores sao controladas por vigencia mensal.

Isso significa que:

- a meta pode mudar a partir de determinado mes
- o passado nao e reescrito
- analises historicas continuam coerentes

Exemplo:

- meta de janeiro a marco: 800
- meta a partir de abril: 1000

Nesse caso:

- janeiro, fevereiro e marco continuam sendo avaliados contra 800
- abril em diante passa a usar 1000

### 6. Trabalhar metas individuais e metas de equipe
O sistema ja suporta tres formas de distribuicao:

- distribuicao automatica entre os membros da equipe
- distribuicao manual por membro
- meta oficial da equipe com detalhamento interno por colaborador

Exemplo:

- acao com meta 100
- equipe com 3 pessoas

No modo automatico:

- A = 33
- B = 33
- C = 34

No modo manual:

- A = 40
- B = 30
- C = 30

Na leitura por equipe:

- a equipe responde pela meta 100
- mas o gestor continua enxergando a contribuicao de cada membro

### 7. Fechar o ciclo operacional das atribuicoes
Hoje o sistema ja trata o ciclo de vida entre atribuicao e tarefa.

Se uma atribuicao for desativada ou removida:

- tarefa sem historico pode ser removida
- tarefa com historico e cancelada, preservando rastreabilidade
- tarefas canceladas deixam de aparecer como itens ativos para o funcionario

Isso evita "tarefa orfa" ou ruido operacional.

## Perfis de acesso

### Admin da consultoria
Pode:

- entrar pelo codigo mestre
- acessar ambiente administrativo
- navegar entre clientes
- acompanhar operacoes em alto nivel

Exemplo de uso:

- acompanhar varias prefeituras ou empresas ao mesmo tempo
- entender quais clientes estao com maior concentracao de gargalos

### Gestor
Pode:

- acessar o contexto da sua organizacao
- cadastrar diagnosticos
- cadastrar indicadores
- cadastrar acoes
- atribuir profissionais e equipes
- acompanhar dashboards
- analisar gargalos
- acompanhar consolidacao entre unidades, quando estiver no nivel pai

Exemplo de uso:

- gestor da prefeitura acompanha o resultado consolidado das UPAs
- gestor da UPA acompanha o operacional detalhado da sua unidade

### Funcionario
Pode:

- entrar na area operacional
- visualizar tarefas atribuídas
- informar o que realizou
- acompanhar seus resultados
- registrar justificativas mensais quando ficar abaixo da meta

Exemplo de uso:

- enfermeira registra quantas vacinas aplicou
- agente registra visitas de busca ativa
- sistema consolida isso automaticamente para a gestao

## Exemplos de acessos de demonstracao
Os acessos abaixo existem na base demo atual:

- `smr-admin` -> `admin / admin123`
- `maracaja` -> `gestor / gestor123`
- `pref-ne` -> `gestor-pref / gestor123`
- `upa-centro-ne` -> `bia-upa / func123`
- `upa-norte-ne` -> `mirella-upa / func123`

## O que o gestor consegue visualizar hoje

### Dashboard operacional por unidade
No dashboard da unidade o gestor consegue:

- navegar entre indicadores
- trocar competencia por mes
- ver performance das acoes
- ver performance do indicador
- ver curva mensal de acoes x indicador
- ver ritmo dos profissionais
- abrir tarefas do profissional em modal

Esse dashboard ajuda a responder perguntas como:

- qual indicador esta mais atrasado neste mes?
- quais acoes estao sustentando esse indicador?
- quais profissionais estao entregando menos dentro desse indicador?

### Analise de problemas
A pagina de analise de problemas ja entrega:

- tarefas abaixo da meta
- pendencias de justificativa
- equipes afetadas
- profissionais afetados
- categorias de gargalo
- ranking de profissionais com mais nao atingimentos
- ranking de acoes mais criticas
- radar comparativo entre equipes

Essa pagina ajuda a responder perguntas como:

- por que a meta nao foi atingida?
- qual gargalo aparece mais?
- em qual equipe o problema esta mais concentrado?
- qual profissional precisa de mais apoio ou acompanhamento?

### Consolidacao multiunidade
Quando o gestor entra em um cliente-pai, o sistema abre uma pagina de consolidacao.

Nela, ele consegue ver:

- resultado consolidado da rede na competencia
- media dos ultimos 3 meses
- ranking das unidades
- unidades abaixo da meta
- comparativo visual entre unidades
- leitura de gargalos por unidade
- melhor unidade e pior unidade do periodo

Essa pagina ajuda a responder perguntas como:

- quais UPAs estao puxando o resultado para baixo?
- qual unidade teve melhor desempenho no periodo?
- a rede como um todo esta melhorando ou piorando?
- onde devemos aprofundar a analise?

## Exemplos de perguntas que o app ja ajuda a responder

### Exemplo 1. Meta do municipio abaixo do esperado
Pergunta:

- A meta do municipio e 1000 vacinas no mes. Nos ultimos 3 meses a media foi 800. Por que?

Leitura possivel hoje:

- abrir a consolidacao no nivel da prefeitura
- verificar quais unidades ficaram abaixo da meta
- abrir a analise de problemas para enxergar os gargalos mais recorrentes
- identificar se o problema esta mais ligado a insumo, pessoal, logistica ou execucao operacional

### Exemplo 2. Unidade com resultado fraco
Pergunta:

- Qual UPA nao esta conseguindo bater a meta?

Leitura possivel hoje:

- comparar as unidades na pagina de consolidacao
- identificar a pior unidade do periodo
- entrar na unidade
- navegar pelos indicadores e pelas acoes
- ver quais profissionais ou equipes estao abaixo

### Exemplo 3. Funcionario abaixo da meta
Pergunta:

- Quem nao conseguiu cumprir a meta e por que?

Leitura possivel hoje:

- abrir a analise de problemas
- ver ranking de profissionais
- identificar tarefas abaixo da meta
- conferir justificativas registradas
- entender se o problema e de capacidade, falta de insumo, ausencia, logistica ou outra causa

## Graficos e leituras disponiveis hoje
O sistema ja possui uma camada visual importante para analise:

- curvas mensais com tooltip
- comparativos por profissional
- gauges de performance
- graficos de barras
- radar comparativo entre equipes
- leitura consolidada por unidade

Esses graficos nao servem apenas para "embelezar" a tela.
Eles ajudam a transformar dados operacionais em leitura gerencial.

## O que o sistema resolve na pratica
Hoje o app ja consegue resolver problemas reais de gestao como:

- parar de depender de planilhas soltas para acompanhar execucao
- organizar o fluxo de meta > acao > atribuicao > tarefa > lancamento > indicador
- dar visibilidade para gestores e consultoria
- consolidar leitura por unidade e por rede
- tornar o nao atingimento explicavel e rastreavel
- criar historico confiavel de meta e resultado

## Visao de valor para o cliente
Em termos simples, o sistema hoje entrega:

- organizacao operacional
- monitoramento continuo
- leitura gerencial mensal
- comparacao entre unidades
- identificacao de gargalos
- base concreta para tomada de decisao

Ou seja:

o sistema nao e apenas um lugar para registrar tarefas.
Ele ja funciona como uma camada de inteligencia operacional para apoiar a gestao.

## Proximos passos naturais de evolucao
As proximas entregas mais valiosas sao:

- explicitar a unidade de referencia no cadastro de diagnosticos em contexto hierarquico
- permitir editar atribuicoes existentes diretamente no modal
- melhorar trilha de auditoria
- seguir refinando a consolidacao e o drilldown entre rede, unidade, equipe e funcionario

## Resumo executivo
Hoje o produto ja permite:

- cadastrar a operacao
- distribuir metas
- acompanhar execucao
- medir resultado
- explicar nao atingimentos
- comparar unidades
- consolidar resultados de rede

Para o cliente, isso significa sair do acompanhamento reativo e passar a enxergar:

- onde agir
- com quem agir
- por que agir
- e qual acao de melhoria esta fazendo sentido de verdade
