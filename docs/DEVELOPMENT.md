# Guia de desenvolvimento

## 1. Ambiente

Diretório do projeto:

    ~/Projects/storix

Ambiente virtual:

    .venv/

Ativar o ambiente:

    source .venv/bin/activate

Verificar o interpretador:

    which python
    python --version

## 2. Dependências

As dependências da aplicação devem ser instaladas no ambiente virtual.
O Python do sistema não deve ser modificado apenas para desenvolver
o Storix.

As dependências e os comandos de instalação serão registrados no
projeto conforme a implementação evoluir.

## 3. Testes

Os testes devem verificar, no mínimo:

- Conversões entre bytes, GiB e TiB.
- Cálculo de percentuais de utilização.
- Capacidade total e espaço disponível.
- Valores zero e dados inválidos.
- Dados ausentes ou indisponíveis.
- Dispositivos sem sistemas de arquivos montados.

Os testes de lógica devem ser independentes dos discos reais sempre
que possível, utilizando dados de exemplo controlados.

## 4. Metodologia

Cada etapa de implementação deverá:

1. Ter um objetivo delimitado.
2. Introduzir somente as dependências necessárias.
3. Incluir testes para o comportamento implementado.
4. Ser executada e validada no ambiente de desenvolvimento.
5. Registrar limitações e decisões técnicas relevantes.

## 5. Segurança

O desenvolvimento deve priorizar consultas de somente leitura.

Não executar operações de formatação, particionamento, montagem
automática ou alteração de sistemas de arquivos como parte dos testes.

## 6. Controle de versão

Antes de registrar alterações:

    git status
    git diff --check
    git diff

Revisar as mudanças antes de criar um commit.
