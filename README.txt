PLANTS VS. ZOMBIES GOTY — ORIGINAL EMULADO NO NAVEGADOR

FUNCIONOU: menu, perfil temporário, modo Aventura, primeira fase, seleção da
ervilha e plantio. O custo de sol foi descontado corretamente.
Não depende da Steam. Não é uma recriação nem uma conversão do código-fonte.
Destino da publicação: https://leonardoscheitz.github.io/pvz-browser/
Estado do deploy: https://github.com/leonardoscheitz/pvz-browser/actions

JOGAR LOCALMENTE
Execute Servir.ps1 com PowerShell e abra http://127.0.0.1:8765/index.html
Se já houver um servidor nessa porta, use o endereço acima.
Escolha Jogar sem som, a configuração validada. A primeira inicialização baixa
cerca de 150 MB e pode levar alguns minutos. Use Chrome ou Edge no computador.

EDIÇÃO TESTADA
C:/Program Files (x86)/Plants vs. Zombies GOTY Edition
Executável original SHA256:
1FF5A2DCF009B453B8866783A68E8D04BD0D066ABDA3F8196D75A677366B2DFF
A instalação original não foi alterada. O pacote contém uma cópia do jogo.
Na cópia de emulação, ddraw.dll e wined3d.dll da pasta do jogo foram omitidas
para usar o DirectDraw/WineD3D do emulador. O executável e os recursos originais
foram preservados. Nenhum arquivo ou biblioteca da Steam foi incluído.

EMULADOR
Boxedwine build oficial master 149, SingleThreadedJit.
Commit: 24dd867e08bd8f1e514372ce0a30f21ab15e0a4e
Build: https://boxedwine.org/builds/branches/master/builds/149/artifacts/build-149.zip
Fonte: https://github.com/danoon2/Boxedwine/tree/24dd867e08bd8f1e514372ce0a30f21ab15e0a4e
Filesystem: https://boxedwine.org/v2/44/TinyCore15Wine11.0-web.zip
Licença: modern/LICENSE-Boxedwine.txt
O build antigo 26R1 não desenhava o jogo corretamente. O build atualizado
com JIT e WineD3D/WebGL foi o que funcionou.

VERIFICAÇÕES E LIMITES
- Menu e criação de perfil pelo teclado: verificados.
- Mouse, seleção da semente e plantio na fase 1-1: verificados.
- Executável instalado: hash mantido.
- Nenhuma biblioteca Steam incluída: conferido no pacote.
- Áudio: não validado; opção com som é experimental.
- Todas as fases, finalização da campanha e celulares: não testados.
- IndexedDB: inicialização e extração verificadas; recuperação do progresso
  após fechar a página ainda não validada.

GITHUB PAGES
O build de uma thread não precisa de cabeçalhos COOP/COEP.
Os caminhos são relativos, inclusive para subpastas de repositórios.
Inclui .nojekyll e workflow de deploy. O maior arquivo tem cerca de 92 MiB,
abaixo do limite Git de 100 MiB por arquivo. Envie por Git; o upload pelo site
do GitHub possui limite menor.
O script Publicar.ps1 cria leonardoscheitz/pvz-browser e ativa o GitHub Pages.
Requer GitHub CLI oficial e login com gh auth login.
O repositório pvz-browser foi reservado para este jogo; outros projetos não
fazem parte desta publicação.

PRIVACIDADE
O servidor local só escuta em 127.0.0.1. Não há credenciais, perfis de navegador
ou sessões da Steam no pacote. O teste usou um perfil novo e temporário.
Jogo e bibliotecas proprietárias mantêm as próprias licenças.

SKILLS
Consultadas as dez skills de sites indicadas. Diretrizes pertinentes de
Frontend Design, Impeccable, UI/UX Pro Max, Bencium e Web Design Guidelines
aplicadas à página de entrada. React, Composition Patterns e React Native
não se aplicam a este HTML estático. Grill Me referencia grilling, ferramenta
indisponível; requisitos essenciais esclarecidos na conversa. AccessLint foi
consultada, sem motor de auditoria disponível. Sem declaração WCAG para o jogo.
