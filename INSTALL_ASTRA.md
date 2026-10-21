# Быстрая установка на Astra Linux SE / CE

## Вариант A — только Vim + Python (уже есть)

```bash
mkdir -p ~/opt
cp -a python-vim-ide ~/opt/
echo 'source ~/opt/python-vim-ide/vimrc' >> ~/.vimrc
vim -c 'PyIdeHealth' -c 'qa'
```

Откройте любой `.py` и нажмите `<Space>e`, `<Space>rr`.

## Вариант B — «почти IDE» (jedi + ruff)

На хосте **с интернетом** (или зеркалом):

```bash
mkdir -p pyide-offline/{wheels,debs}
pip download jedi parso ruff pytest -d pyide-offline/wheels
# по возможности:
# apt-get download universal-ctags ripgrep git
# mv *.deb pyide-offline/debs/
tar czf pyide-offline.tar.gz pyide-offline python-vim-ide
```

На Astra:

```bash
tar xzf pyide-offline.tar.gz
cp -a python-vim-ide ~/opt/
echo 'source ~/opt/python-vim-ide/vimrc' >> ~/.vimrc

python3 -m pip install --user --no-index --find-links=./pyide-offline/wheels jedi ruff pytest
# sudo dpkg -i pyide-offline/debs/*.deb   # если скачали

vim -c 'PyIdeHealth' -c 'qa'
```

## Вариант C — системный Python без pip user

```bash
sudo python3 -m pip install --no-index --find-links=./pyide-offline/wheels jedi ruff
```

или в venv проекта:

```bash
cd ~/myproject
python3 -m venv .venv
.venv/bin/pip install --no-index --find-links=~/pyide-offline/wheels jedi ruff pytest
```

## Проверка после установки

| Проверка | Ожидание |
|---|---|
| `:PyIdeHealth` | Vim/Python OK, jedi OK |
| `<Space>e` | дерево слева |
| в `def`<Tab> | развернулся шаблон |
| `gd` на имени функции | прыжок (нужен jedi) |
| `<Space>rl` | lint OK / список ошибок |
| `<Space>rr` | терминал с выводом скрипта |

## Частые проблемы Astra

**`termguicolors` ломает цвета в старом TERM**  
В `~/.vimrc` после source: `set notermguicolors`

**Нет `+terminal` / `+job`**  
Поставьте пакет `vim-nox` / `vim-gtk3` с Huge features (у вас должен быть Huge — проверьте `vim --version | grep -E 'terminal|job|python3'`).

**Нет интернета у pip**  
Только `--no-index --find-links=...` с заранее скачанными wheel.

**Кодировка cp1251**  
Уже включено `fileencodings=utf-8,cp1251,...` в vimrc.
