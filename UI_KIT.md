# GOTY+ — kit visual

## Recursos
- A compilação reutiliza as imagens já extraídas de modern/pvz-goty.zip: titlescreen.jpg, PvZ_Logo.jpg e máscara, options_menuback.jpg e máscara e options_backtogamebutton0.png.
- ui-kit.css define os componentes .pvz-stone, .pvz-panel, .pvz-title, .pvz-panel-heading e .pvz-logo. Não recriar os botões a cada tela.
- ui-icons.svg contém ilustrações vetoriais novas e editáveis (Sandbox, offline, backup). Não são sprites oficiais.
- Os estados normal, hover, pressionado, desabilitado, foco e aria-pressed são tratados pelo kit. Respeitar redução de movimento.
- Textos funcionais permanecem HTML e traduzíveis; não incorporá-los em imagens.

## Tipografia
O canvas mantém as fontes originais do motor. O kit web usa provisoriamente Trebuchet MS e Georgia. Antes de converter as fontes do jogo para o navegador, inspecionar o formato real dos atlas e métricas e confirmar a cobertura de acentos PT-BR. Não publicar arquivos de fontes de terceiros obtidos de outras fontes.

## Novos menus
Usar os componentes compartilhados e, onde possível, texturas originais com suas máscaras. Novas ilustrações devem ser pequenas, com contorno escuro, volumes pintados e paleta compatível; salvar a fonte editável. Preservar os IDs e a acessibilidade dos controles e não misturar mudanças visuais com mudanças de saves.

## Validação
Executar scripts/build.py e tests/test_browser.py. O teste test_workshop_visual_assets verifica carregamento da imagem de botão, presença de ícones e ausência de overflow horizontal em quatro tamanhos de viewport. Isso não substitui revisão visual real em PC e iPhone.
