PLANTS VS. ZOMBIES GOTY NO NAVEGADOR

Jogar: https://leonardoscheitz.github.io/pvz-browser/
O endereço abre diretamente o jogo. Clique em “Click to Start”, crie o perfil e
entre em Adventure. O menu Options do jogo controla a música, os efeitos e a
tela cheia. Use o mouse ou toque para escolher sementes, plantar e recolher sol.
Durante uma fase, o botão Menu Hack aparece no canto inferior esquerdo.
Abrir o menu pausa a partida. Você pode ajustar sol e moedas, alternar o plantio
grátis, mudar a velocidade, curar plantas e remover os zumbis presentes.
O saldo de moedas é salvo no perfil. Use Voltar ao jogo para continuar.

O jogo usa os textos em inglês presentes na cópia GOTY deste repositório.

MOTOR E RECURSOS
O motor comunitário PvZ-Portable (revisão 2493154) roda em WebAssembly, usa WebGL para
desenhar e Web Audio para tocar as músicas e os efeitos do GOTY. Aventura,
Mini-Games, Puzzle, Survival, Zen Garden, Almanac e Zombatar fazem parte do
motor. Os desbloqueios seguem o progresso do perfil.

O build lê modern/pvz-goty.zip e empacota as imagens, animações, sons, fontes e
definições do jogo. Somente a pasta dist é publicada. O executável de Windows,
o instalador, os componentes da EA e o sistema Wine ficam fora do site. Os
links antigos para modern/boxedwine.html redirecionam para o jogo nativo.
Os recursos estáticos têm nomes versionados por conteúdo e usam o cache HTTP
do navegador. O pacote de recursos é dividido em partes pequenas, lidas em até
quatro downloads simultâneos e descompactadas diretamente no buffer final.
O WASM é compilado durante a leitura.

PROGRESSO
O motor guarda os perfis e as partidas no IndexedDB deste navegador e endereço.
Use “Main Menu” dentro da fase para o jogo salvar o ponto de retomada. Há uma
única aba com permissão de escrita por vez nos navegadores com Web Locks.
Apagar os dados do site remove o progresso. O jogo avisa se o navegador só
permitir uma sessão temporária.

Na primeira abertura, se este navegador tiver um perfil global da antiga
emulação no mesmo endereço, o site copia users.dat e userN.dat da instalação
com o progresso mais recente. Isso recupera
nome, fase e desbloqueios. Ondas em andamento da emulação ficam no banco antigo.

DESENVOLVIMENTO LOCAL
Com Python 3.9 ou superior, na raiz do repositório:
  python scripts/build.py
  python -m http.server 8765 --bind 127.0.0.1 --directory dist
Abra http://127.0.0.1:8765/. No Windows, Servir.ps1 prepara e serve o site.

O ZIP do motor com o Menu Hack está em vendor/pvz-garden.zip. O build verifica seu SHA-256
e pode ser executado offline apenas com a biblioteca padrão do Python.

PUBLICAÇÃO
O workflow em .github/workflows/pages.yml prepara o site no push para main e
envia dist ao GitHub Pages. A última etapa confere a revisão em revision.txt e
o HTML entregue pelo endereço público. Publicar.ps1 refaz o deploy com gh.
Execuções: https://github.com/leonardoscheitz/pvz-browser/actions/workflows/pages.yml
Os testes de compatibilidade ficam em .github/workflows/test-browser.yml.
Veja os resultados de jogo, saves e desempenho em VALIDACAO.md no repositório.

CRÉDITOS
Plants vs. Zombies, seus gráficos, áudios e textos pertencem a PopCap Games /
Electronic Arts. O motor comunitário é distribuído sob LGPL-3.0-or-later.
O arquivo engine/garden.inc acrescenta os controles do menu ao motor LGPL.
O workflow .github/workflows/garden-engine.yml reproduz a compilação.
Fonte correspondente e instruções de compilação:
https://github.com/wszqkzqk/PvZ-Portable/tree/2493154028b8542a58bc2caed14fda83b1b7c57e
Build original de referência: https://github.com/wszqkzqk/PvZ-Portable/actions/runs/45099544349
SHA-256 do ZIP original: 3a215c83f7544c7967253fe282ab86a5872f99daea7303ce5871f09cdb78d9e8
Licenças: licenses/PvZ-Portable-LGPL.txt, licenses/GPL.txt,
licenses/PopCap-Framework.txt e licenses/fcaseopen.txt.
This product includes portions of the PopCap Games Framework, © 2005-2009
PopCap Games, Inc. All rights reserved. (http://popcapframework.sourceforge.net/).
