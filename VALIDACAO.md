# Validação do PvZ Browser

Testes da [versão publicada antes do Menu Hack](https://github.com/leonardoscheitz/pvz-browser/commit/0612962ff14d1939c825049b238be1587fd4a67e), realizados em 24 de novembro de 2026 com o motor PvZ-Portable `2493154` e os recursos GOTY do repositório. Todos os perfis usados nesta validação eram descartáveis.

## Jogo e progresso

| Cenário | Resultado observado |
| --- | --- |
| Adventure com perfil novo | Criação de nome pelo campo do jogo, plantio de duas ervilhas, coleta de sol, vitória em 1-1 e recompensa Sunflower. O perfil gravou a fase 2. Ao sair para o menu em 1-2, fechar a aba e abrir novamente, apareceu “Continue Game?” e a partida voltou ao gramado. |
| Toque e rotação | Chromium com eventos de toque em 390 × 844 e 844 × 390. O campo de nome recebeu texto e devolveu o foco ao canvas. Foram usados os controles do jogo para plantar e coletar. O canvas manteve a proporção 4:3. |
| Bloqueios e menus | Com um perfil novo, Mini-Games, Puzzle e Survival exibiram o aviso “Locked!”. Com um perfil de teste pós-Adventure, ZomBotany e Survival: Day passaram pela seleção de seis sementes e abriram o tabuleiro. Em Vasebreaker, quebrar um vaso revelou uma carta. |
| Fases posteriores | Dois perfis preparados para os níveis internos 21 e 41 abriram, respectivamente, o quintal com piscina e o telhado. O jogo exibiu o diálogo de entrada correspondente a cada cenário. |
| Extras | O Almanac mostrou a ficha da Peashooter. O Zen Garden abriu a estufa e permitiu selecionar o regador. O Zombatar exibiu o acordo de primeira utilização. Em outro perfil preparado com essa etapa concluída, foi possível escolher cabelo, finalizar o retrato e verificar a entrada 1/1 gravada no perfil. |
| Migração real | Um perfil criado e salvo no executável GOTY da versão BoxedWine foi aberto pela versão nativa na mesma origem. `users.dat` e `user1.dat` chegaram idênticos, byte por byte. A onda em andamento ficou na emulação e os registros antigos permaneceram intactos. |
| Abas e falhas | A segunda aba mostrou o aviso antes de baixar os binários. Após fechar a primeira, a segunda abriu com o perfil salvo. Uma parte truncada do pacote exibiu erro, liberou o bloqueio e permitiu tentar novamente. A perda induzida do contexto WebGL apresentou a opção de reabrir e o perfil sobreviveu à recarga. |
| Áudio e tela cheia | O sinal Web Audio chegou à saída com amplitude diferente de zero durante a fase. Em Chromium, a opção Full Screen do jogo ativou o contêiner correto, e a saída de tela cheia funcionou. |

A comparação visual entre o executável GOTY emulado e o port abrangeu a tela de título, o cadastro de perfil, o menu e a fase 1-1 até a vitória. Nas duas versões, a fase começou com 150 de sol, a primeira Peashooter custou 100 e a vitória entregou a carta Sunflower. Também foram comparados o gramado, a disposição do tabuleiro e as instruções de plantio. A validação dos modos avançados usou perfis preparados para chegar diretamente às telas. A equivalência integral de física, animações, áudio e progressão de todas as fases continua em aberto.

O Chromium e o Firefox em Linux, o Edge no Windows e o WebKit no macOS passaram pelos três testes automatizados. O Safari 27.2 instalado no macOS também criou o perfil pelo teclado e recuperou os mesmos dados após recarregar a página. [Execução dos testes](https://github.com/leonardoscheitz/pvz-browser/actions/runs/45464036863)

No simulador de iPhone 17 Pro, o Safari 26.4 registrou três eventos de toque. O teste abriu o campo de nome, digitou e confirmou o perfil. Depois da recarga, o jogo recuperou o mesmo arquivo de perfil, byte por byte. [Teste do Safari no iPhone simulado](https://github.com/leonardoscheitz/pvz-browser/actions/runs/45464662903/job/138696237265)

## Carregamento

Amostra de laboratório com Chrome Headless Shell 151 em Linux, WebGL por software e um servidor local. A abertura a frio usou um contexto vazio. A reabertura usou o mesmo contexto com cache HTTP habilitado. O tempo até o título foi medido até o botão “Click to Start!” estar visível. O primeiro clique foi considerado aceito quando o motor ativou a caixa de nome.

| Cenário | Transferência HTTP observada | Até o título | Até aceitar a entrada |
| --- | ---: | ---: | ---: |
| Cache vazio, servidor local | 35,77 MB | 10,0 s | 10,5 s |
| Reabertura com cache | 300 B | 8,2 s | 8,7 s |
| Cache vazio, 10 Mbit/s e latência configurada em 100 ms | 35,77 MB | 39,4 s | 39,8 s |

Com o pacote monolítico, a mesma medição de reabertura transferiu 32,83 MB e chegou ao título em 8,5 s. Após a divisão, 37 recursos vieram do cache. O valor de 300 B é o total informado por Resource Timing nesse servidor. O cabeçalho de uma resposta do Pages pode ter outro tamanho. O navegador ainda descompacta os recursos e inicializa o motor a cada abertura.

O PAK reconstruído a partir das 22 partes contém os mesmos 44.779.106 bytes da versão anterior. O SHA-256 do PAK descompactado é `5281b527840b0db32128b982cff8c1a8d8af9bcbb2447a5cde7cf6bd76609d90`.

Na amostra de 5,04 s da fase inicial, 295 quadros tiveram chamadas de desenho WebGL (58,5 por segundo). O heap WebAssembly tinha 337 MiB. Em uma medição separada, o conjunto de processos do navegador de teste ocupou aproximadamente 664–665 MiB de PSS ao abrir a piscina e o telhado, contra 102 MiB no contexto vazio. PSS divide a memória compartilhada entre os processos. Esses valores dependem do dispositivo, da fase e do renderizador gráfico.

## Repetir

O workflow **Testar o GOTY no navegador** compila o projeto e testa cadastro, persistência entre abas, seleção do perfil legado mais recente e recuperação de uma parte corrompida. Os arquivos de perfil da suíte são gerados em memória com dados sintéticos. No Chromium, a suíte usa a entrada por toque. O motor e os recursos de cada execução são os do próprio repositório.

```sh
python scripts/build.py
python -m pip install playwright==1.62.0
python -m playwright install chromium
python tests/test_browser.py
```

O simulador manteve a altura da área visível durante a digitação. A aparência do teclado virtual e o conforto dos controles durante uma partida em celular físico ainda precisam de um teste em aparelho.
