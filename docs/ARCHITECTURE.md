# Arquitetura do Storix

## 1. Visão geral

O Storix utiliza uma arquitetura modular, priorizando bibliotecas e
APIs Python. Ferramentas externas serão utilizadas quando oferecerem
informações que não sejam obtidas de forma simples e confiável por
meio das interfaces Python disponíveis.

A interface não deve depender diretamente dos mecanismos de coleta.

## 2. Fluxo de dados

1. Coleta: obtém informações sobre dispositivos e sistemas de arquivos.
2. Normalização: converte os resultados para modelos internos comuns.
3. Análise: calcula indicadores e identifica limitações dos dados.
4. Apresentação: exibe os resultados na interface de terminal.

## 3. Componentes planejados

### Collectors

Responsáveis pela coleta de informações.

- Dispositivos de bloco e partições.
- Pontos de montagem.
- Capacidade e ocupação dos sistemas de arquivos.
- Informações complementares do kernel e das ferramentas disponíveis.

### Models

Define os modelos internos utilizados para representar dispositivos,
partições, sistemas de arquivos e medições.

### Analyzers

Calcula percentuais e organiza os indicadores de armazenamento.
Deve distinguir valores medidos, indisponíveis e não aplicáveis.

### UI

Apresenta os dados com tabelas, painéis, barras de progresso e árvores
hierárquicas utilizando Rich.

## 4. Fontes de dados

A coleta poderá utilizar:

- os.statvfs(): estatísticas de sistemas de arquivos acessíveis.
- /sys: informações expostas pelo kernel sobre dispositivos.
- /proc: informações do sistema e das montagens.
- lsblk: hierarquia dos dispositivos de bloco.
- findmnt: informações sobre pontos de montagem.
- udev: propriedades de dispositivos, quando necessário e disponível.

A disponibilidade de cada fonte será verificada em tempo de execução.

## 5. Regras de integridade

- Não confundir capacidade física com espaço disponível em um sistema
  de arquivos.
- Não considerar uma partição não montada como vazia.
- Não somar indiscriminadamente dispositivos físicos e virtuais.
- Não presumir que todas as partições possuem sistemas de arquivos.
- Tratar separadamente tecnologias como Btrfs, LVM, RAID e LUKS.
- Identificar quando uma medição não puder ser realizada.
- Não exigir privilégios administrativos sem necessidade comprovada.

## 6. Escopo

A plataforma inicial é Linux, com foco em compatibilidade entre
distribuições.

O suporte a sistemas de arquivos e camadas de armazenamento especiais
será implementado e validado incrementalmente.
