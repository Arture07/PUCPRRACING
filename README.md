**Ferramenta de Análise de Logs de Dados para a Equipe PUCPR Racing**

## Introdução

Esta ferramenta foi desenvolvida como parte do Processo Seletivo PUCPR Racing 2025, focando no **Tema 4: Ferramenta – Soluções físicas ou digitais (ex: simulações, testes, medições) que sirvam para validar ou auxiliar etapas do projeto.**

O objetivo principal é fornecer à equipe uma solução inicial em Python para carregar, visualizar e realizar análises básicas em logs de dados (formato CSV) coletados durante testes do carro Fórmula SAE, auxiliando na validação de desempenho e no auxílio ao desenvolvimento e acerto do veículo.

## Funcionalidades Principais

* **Carregamento de Logs:** Carrega arquivos de dados no formato CSV.
* **Mapeamento Flexível de Canais:** Utiliza um arquivo de configuração (`config.ini`) para mapear os nomes das colunas do CSV para os canais esperados pela aplicação, permitindo adaptabilidade a diferentes loggers ou formatos de exportação.
* **Visualização Temporal:** Plota múltiplos canais de dados selecionados em função do tempo (ou índice) na aba "Geral / Plotagem". Inclui ferramentas de zoom e pan.
* **Diagrama G-G:** Gera o gráfico de Aceleração Lateral vs. Aceleração Longitudinal para análise do envelope de performance do veículo.
* **Mapa da Pista (GPS):** Plota a trajetória do veículo usando coordenadas de GPS (Latitude/Longitude) e permite colorir a trajetória com base nos valores de outro canal selecionado (ex: Velocidade).
* **Cálculo de Tempo de Volta (Beta):** Implementa um algoritmo básico para detectar voltas baseado no cruzamento de uma linha de chegada/partida (coordenadas definidas no `config.ini`) e calcula os tempos. A precisão depende da qualidade do GPS e dos parâmetros no `config.ini`.
* **Análises Específicas (Básicas/Placeholders):**
    * **Skid Pad:** Calcula métricas básicas de G Lateral (máximo e médio sobre o log inteiro - placeholder).
    * **Aceleração:** Calcula o tempo estimado para atingir 75m e a velocidade máxima durante essa puxada (baseado em detecção simples de início).
    * **Autocross / Endurance:** Além do cálculo de voltas, inclui plot de Histograma de Posição da Suspensão e um placeholder para plot de Delta-Time.
* **Seleção Rápida de Canais:** Botões "Marcar Todos" e "Desmarcar Todos" para facilitar a seleção na lista de canais.
* **Exportar Dados:** Permite salvar o DataFrame carregado (incluindo a coluna 'LapNumber' se calculada) em um novo arquivo CSV.
* **Interface Gráfica Moderna:** Utiliza a biblioteca CustomTkinter para uma aparência escura e organizada.

## Estrutura de Arquivos

Para executar a aplicação, os seguintes arquivos devem estar no mesmo diretório:

1.  `main_gui.py`: Script principal que contém a interface gráfica e orquestra as chamadas.
2.  `config_manager.py`: Módulo responsável por ler e gerenciar o arquivo `config.ini`.
3.  `data_loader.py`: Módulo responsável por carregar e pré-processar o arquivo CSV.
4.  `calculations.py`: Módulo contendo as funções para cálculos de métricas (G-G, Tempo de Volta, Aceleração, Skid Pad, Delta-Time placeholder).
5.  `plotting.py`: Módulo contendo as funções para gerar os gráficos Matplotlib.
6.  `config_pucpr_tool.ini`: Arquivo de configuração (será criado automaticamente na primeira execução se não existir). **É ESSENCIAL EDITÁ-LO.**
7.  `image_cf6f57.png`: Arquivo de imagem do logo da equipe (usado na área de plotagem inicial).

## Requisitos

* Python 3.x
* Bibliotecas Python:
    * `customtkinter`
    * `pandas`
    * `numpy`
    * `matplotlib`
    * `Pillow` (para o logo)
    * `tksheet` (Se você reintroduziu a aba Planilha em alguma versão sua)

    Você pode instalar as bibliotecas necessárias usando pip:
    ```bash
    pip install customtkinter pandas numpy matplotlib Pillow
    # Se adicionou a planilha novamente: pip install tksheet
    ```

## Configuração Essencial (`config.ini`)

Este arquivo é **crucial** para que a ferramenta funcione corretamente com os **seus dados**. Ele permite mapear os nomes das colunas do seu arquivo CSV para os nomes internos que a aplicação espera.

* **Criação:** Se o arquivo `config_pucpr_tool.ini` não existir no diretório ao executar `main_gui.py`, ele será criado automaticamente com valores padrão.
* **Edição:**
    * Abra o arquivo `config_pucpr_tool.ini` em um editor de texto. Você também pode usar o menu "Arquivo" > "Ver/Editar Configuração..." dentro do aplicativo.
    * **Seção `[CHANNELS]`:** Esta é a seção mais importante. Para cada linha (ex: `gpslat = GPS_Lat`), a **chave à esquerda** (`gpslat`) é o nome interno que a aplicação usa, e o **valor à direita** (`GPS_Lat`) deve ser **exatamente** o nome da coluna correspondente no seu arquivo CSV. Revise todas as chaves e ajuste os valores para baterem com o seu log.
    * **Seção `[TRACK]`:** Ajuste `StartFinishLat` e `StartFinishLon` com as coordenadas GPS da sua linha de chegada/partida para que o cálculo de voltas funcione.
    * **Seção `[ANALYSIS]`:** Contém parâmetros como `LapDetectionThresholdMeters` (distância máxima da linha para contar cruzamento) e `MinLapTimeSeconds` (tempo mínimo para validar uma volta). Ajuste conforme necessário.
* **Reiniciar:** Após editar e salvar o `config.ini`, **reinicie a aplicação** para que as novas configurações sejam carregadas.

## Como Executar

1.  Certifique-se de ter Python 3 e as bibliotecas listadas em "Requisitos" instaladas.
2.  Coloque todos os arquivos `.py` (`main_gui.py`, `config_manager.py`, etc.), o arquivo de logo `image_cf6f57.png` no mesmo diretório.
3.  (Opcional) Coloque seu arquivo `config_pucpr_tool.ini` já editado no mesmo diretório, ou deixe que ele seja criado na primeira execução para editar depois.
4.  Abra um terminal ou prompt de comando nesse diretório.
5.  Execute o script principal: `python main_gui.py`

## Como Usar

1.  **Carregar Log:** Clique no botão "Abrir Log (.csv)" ou use o menu "Arquivo" > "Abrir Log (.csv)..." e selecione seu arquivo de dados. O nome do arquivo aparecerá no painel esquerdo e a lista de canais será preenchida.
2.  **Plotagem Geral:**
    * Marque as caixas de seleção dos canais que deseja visualizar na lista à esquerda. O gráfico na aba "Geral / Plotagem" será atualizado automaticamente.
    * Use os botões "Marcar Todos" e "Desmarcar Todos" para agilizar a seleção.
    * Use a barra de ferramentas do Matplotlib abaixo do gráfico para dar zoom, pan, salvar a imagem do gráfico, etc.
3.  **Diagrama G-G:** Na aba "Geral / Plotagem", clique no botão "Plotar G-G".
4.  **Mapa da Pista:** Na aba "Geral / Plotagem", clique em "Plotar Mapa". Para colorir a trajetória, selecione um canal na caixa de seleção "Cor Mapa" *antes* de clicar em "Plotar Mapa".
5.  **Análises Específicas:**
    * Navegue para as abas "Skid Pad", "Aceleração" ou "Autocross / Endurance".
    * Clique em "Calcular Métricas" para ver os resultados dos cálculos (alguns são placeholders) na caixa de texto à direita.
    * Clique em "Plot Análise" para visualizar um gráfico relevante (placeholder ou básico) na área de plotagem principal.
6.  **Exportar Dados:** Use o menu "Arquivo" > "Exportar Log Atual (.csv)..." para salvar o DataFrame carregado (incluindo a coluna `LapNumber`, se calculada) em um novo arquivo CSV.
7.  **Editar Configuração:** Use o menu "Arquivo" > "Ver/Editar Configuração..." para abrir o `config.ini` no seu editor de texto padrão. Lembre-se de reiniciar o app após salvar as alterações.

## Limitações Atuais e Próximos Passos

* **Placeholders:** As análises de Skid Pad, Aceleração (além do 0-75m) e Delta-Time ainda são básicas ou placeholders. Elas precisam de algoritmos mais sofisticados para detectar as fases corretas das provas nos dados e realizar cálculos mais precisos.
* **Cálculo de Voltas:** A detecção de voltas por GPS é funcional (beta), mas sua precisão depende muito da qualidade do sinal GPS e da configuração correta dos parâmetros no `config.ini`.
* **Melhorias Futuras:** A ferramenta pode ser expandida para incluir:
    * Implementação completa das análises específicas (Skid Pad, Aceleração, Delta-Time real).
    * Análise de Frequência (FFT).
    * Métricas de Suspensão avançadas (velocidade de amortecedor, etc.).
    * Comparação direta com dados de simulação.
    * Sincronização com vídeo onboard.

## Troubleshooting Básico

* **Erro ao carregar log / Análises não funcionam:** Verifique se os nomes das colunas na seção `[CHANNELS]` do `config_pucpr_tool.ini` correspondem **exatamente** aos nomes no seu arquivo CSV.
* **Erro `NameError` ou `AttributeError`:** Verifique se todos os 5 arquivos `.py` estão no mesmo diretório e se você está executando a versão mais recente de cada um.
* **Biblioteca não encontrada:** Certifique-se de ter instalado todas as bibliotecas listadas em "Requisitos" usando `pip install <nome_da_biblioteca>`.
* **Verifique o Console:** Mensagens de erro ou avisos podem aparecer no terminal onde você executou o script.
