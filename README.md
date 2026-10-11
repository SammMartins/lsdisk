# Storix

**Cross-distro Linux Storage Explorer**

O Storix é um visualizador de armazenamento para Linux que apresenta
informações sobre HDs, SSDs, partições e sistemas de arquivos de
maneira compreensível para usuários com diferentes níveis técnicos.

## Objetivos

- Identificar dispositivos de armazenamento e suas relações.
- Apresentar capacidade, espaço utilizado e espaço disponível.
- Diferenciar discos físicos, partições e sistemas de arquivos.
- Identificar partições não montadas e dados indisponíveis.
- Explicar informações técnicas em linguagem acessível.
- Oferecer uma interface de terminal com cores, tabelas, barras
  de progresso e visualização hierárquica.
- Funcionar em diferentes distribuições Linux.

## Princípios do projeto

- Somente leitura: não modificar discos ou partições.
- Modularidade: separar coleta, análise e apresentação.
- Portabilidade: evitar dependência de uma distribuição específica.
- Transparência: não apresentar estimativas como valores confirmados.
- Testabilidade: validar cálculos e comportamentos com testes.

## Tecnologias planejadas

- Python
- Rich, para a interface de terminal
- APIs da biblioteca padrão do Python
- Interfaces do Linux, como `/sys` e `/proc`, quando necessárias
- Ferramentas externas, como `lsblk` e `findmnt`, quando justificadas
- unittest, para os testes automatizados iniciais

## Requisitos

- Linux
- Python compatível com as dependências adotadas
- Ambiente virtual Python recomendado

Algumas funcionalidades poderão depender de ferramentas ou permissões
específicas do sistema.

## Desenvolvimento

O projeto está em fase inicial de desenvolvimento.

Consulte:

- [Arquitetura](docs/ARCHITECTURE.md)
- [Guia de desenvolvimento](docs/DEVELOPMENT.md)

## Segurança

O Storix será desenvolvido para consultar informações de armazenamento.
Operações de formatação, particionamento e alteração de sistemas de
arquivos não fazem parte do escopo.

## Licença

A licença será definida antes da primeira distribuição pública.

## Roadmap

### Planned Improvements

- **Unmounted partition discovery:** Identify filesystem types on partitions
  that are not currently mounted, without mounting them.
- **Filesystem metadata:** Collect filesystem labels and UUIDs whenever
  the required information is available.
- **Partition identification:** Distinguish partitions with recognized
  filesystems from partitions whose filesystem information is unavailable
  or has not yet been identified.
- **Read-only inspection:** Preserve the project's read-only principle
  throughout storage discovery.

These improvements are planned and are not fully implemented in version 0.1.0.
