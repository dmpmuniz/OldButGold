# OldButGold

**OldButGold** transforma a sequência de comandos para validar e reviver um
HDD/SSD num único processo guiado — com nota final (Gold / Silver / Bronze /
Failed) e relatório.

![Python](https://img.shields.io/badge/python-3.11+-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-Linux-black)

## A história

Eu tinha uns HDDs velhos em casa e queria reaproveitá-los. Já tinha usado as
ferramentas (smartctl, badblocks, sgdisk, mkfs) — sempre separadas, sempre
digitando vários comandos, sempre na ordem certa, do contrário já era.

Eu não queria uma ferramenta nova. Eu queria **uma fórmula pronta**: escolher o
disco, clicar, deixar rodando e ir fazer outra coisa. OldButGold é isso: um
fluxo guiado em TUI que orquestra as ferramentas Linux que você já conhece.

## Quick start

```bash
pipx install git+https://github.com/dmpmuniz/OldButGold
obg
```

Ou direto do código-fonte:

```bash
git clone https://github.com/dmpmuniz/OldButGold
cd OldButGold
pipx install .
obg
```

## Veja sem risco

Teste o fluxo completo num disco virtual (arquivo de imagem) — nenhum drive
real é tocado:

```bash
obg --mock
```

> `--test` executa o fluxo real, mas limita a leitura badblocks a ~1% do drive.
> **Ainda é destrutivo** — use apenas em drives cujos dados você não precisa.

## Uso

```text
obg                validação completa (destrutiva)
obg --test         fluxo real, badblocks limitado a ~1%
obg --mock         modo seguro num disco virtual
obg --version      versão
```

## O que faz

1. **Identificação** — enumera discos, lê SMART e geometria.
2. **Saúde inicial** — SMART short self-test + baseline.
3. **Superfície** — badblocks destrutivo, reativável se interrompido.
4. **Saúde final** — re-lê SMART e calcula deltas.
5. **Particionar/formatar** — GPT + sistema de arquivos escolhido.
6. **Relatório** — classificação graduada com relatório em markdown.

## Requisitos

- Linux, Python 3.11+
- `root` (SMART e badblocks precisam de acesso ao dispositivo, escalado via `pkexec`)
- Ferramentas de terminal inclusas em `tools/` — sem dependências de host

## Tecnologias

- **Python 3.11+** · **Textual** (TUI) · **Rich** (terminal)
- **PyInstaller** para build self-contained
- Orquestra: `smartctl`, `badblocks`, `lsblk`, `blockdev`, `sgdisk`, `partprobe`, `mkfs.*`

## Aviso

Ferramenta criada para uso pessoal, sem garantias. A validação é **destrutiva**:
execute apenas em drives cujos dados você não precisa. Qualquer dano é
responsabilidade do usuário.

## Licença

MIT — ver [LICENSE](LICENSE).

---

## EN

OldButGold turns the command sequence for validating and reviving an
HDD/SSD into a single guided process — with a final grade
(Gold / Silver / Bronze / Failed) and report. Born from old drives at home
and a lazy principle: pick the disk, click, let it run, go do something else.

```bash
pipx install git+https://github.com/dmpmuniz/OldButGold
obg --mock    # safe trial on a virtual disk
```