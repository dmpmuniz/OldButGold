# AGENT_RULES.md

Regras para agentes (humanos ou IA) que modificam o OldButGold.

## Versionamento

- `obg/__init__.py` e `pyproject.toml` contêm a versão.
- Commits com mudanças relevantes (bugfix, feature, layout, build) **devem** incrementar a versão.
- Formato: `0.3` → `0.4` para mudanças maiores, `0.3` → `0.3.1` para patches.
- A release deve ser recriada após cada mudança (binário + ZIP).

## Release

- `release/OldButGold-v{version}/OldButGold` é o binário atual.
- `release/OldButGold-v{version}.zip` é o ZIP de distribuição.
- **Sempre** atualizar ambos após qualquer alteração no código.
- Limpar `obg_*.log` da pasta release antes de zipar.

## O que já foi feito (não desfazer sem perguntar)

### Layout fixo 100×30

Terminal redimensiona com `\x1b[8;30;100t` em `__main__.py:53` e em `app.py` (ObgApp.on_mount). O frame `#app-frame` tem `width: 100; height: 30` no CSS.

### Header/Footer com dock

`#header` usa `dock: top`, `#footer` usa `dock: bottom`. Estão fora do fluxo vertical, sempre visíveis no topo/base.

### Body usa Container (não VerticalScroll)

`#body` é `Container` com `height: 1fr; overflow-y: auto`. `VerticalScroll` consome eventos de seta — Container não. Se trocar de volta para `VerticalScroll`, as setas param de funcionar em telas com scroll.

### BINDINGS com priority=True

`StartupScreen` usa `Binding(key, action, desc, priority=True)` para Enter, Escape, ←, →. Isso garante que as teclas funcionem mesmo quando um botão desabilitado está focado. **Não usar tupla** com `priority=True` — dá `SyntaxError`. Usar `from textual.binding import Binding`.

### PyInstaller — imports antes de execvp

Em `__main__.py`, `from obg.ui.app import ObgApp` **deve** vir antes do bloco `if os.geteuid() != 0:` que chama `os.execvp`/`sys.exit`. PyInstaller não analisa código depois de chamadas terminativas — o módulo some do PYZ e o binário quebra.

### rich._unicode_data no spec

O spec coleta `collect_submodules('rich._unicode_data')` para evitar `zlib.error` ao renderizar caracteres Unicode.

### DriveInfoScreen Back vai para DriveSelection

O botão Back em DriveInfoScreen usa `while len(self.app.screen_stack) > 2: self.app.pop_screen()` — volta direto para a tela de seleção de disco, pulando SmartTestScreen.

### Log vai para o CWD

`obg/utils/logger.py` escreve em `os.getcwd()`. O log aparece na pasta onde o binário foi executado (ex: pasta release). Foi movido para `~/.cache/obg/` e voltou a pedido do usuário.

### Terminal fallback

Quando não root e sem TTY (clique no gerenciador de arquivos), tenta terminais nesta ordem: ptyxis (`-x`), gnome-terminal (`-x`), kgx, konsole, xfce4-terminal, lxterminal, xterm (`-e`). A sintaxe difere entre `-x` (comando como string única) e `-e` (args separados).

## Antes de desfazer algo

Se for reverter qualquer item acima, **pergunte ao usuário primeiro**. Se não responder, não desfaça.
