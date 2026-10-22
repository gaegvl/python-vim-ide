# Установка на Astra Linux (офлайн)

## Важно: что писать в `~/.vimrc`

**Правильно** (Vimscript):
```vim
source ~/python-vim-ide/vimrc
```

**Неправильно** — НЕ добавляйте в `.vimrc`:
```vim
source ~/.local/share/pyide/env.sh
```
`env.sh` — это скрипт **для bash** (`export PATH=...`). В Vim будет ошибка:
`E1042: Команда :export используется только в Vim9 script`.

Перед Vim в терминале (по желанию):
```bash
source ~/.local/share/pyide/env.sh
vim
```
Vim и сам найдёт venv через `~/.local/share/pyide/python`.

## Важно: типичные ошибки Astra

**«недопустимое название pipefail»** — скрипт запущен через `sh` (dash), не bash.
Правильно:
```bash
python3 bin/install_tools.py
# или
bash bin/install-tools.sh
```
Проверка: `bash --version` и `readlink -f $(command -v bash)`.

**«нет файла /usr/bin/env»** — не запускайте `./bin/...`, только `bash bin/...`
или `python3 bin/install_tools.py`.

**«Отказано в доступе»**:
```bash
chmod -R u+rwX vendor
PYIDE_HOME=$HOME/pyide python3 bin/install_tools.py
```

## Рекомендуемый путь

```bash
# 1. Доставьте каталог на сервер (git / scp / флешка)
git clone https://github.com/gaegvl/python-vim-ide.git ~/opt/python-vim-ide

# 2. Одна команда
bash ~/opt/python-vim-ide/bin/install.sh

# 3. Проверка
vim -c 'PyIdeHealth' -c 'qa'
vim ~/opt/python-vim-ide/examples/demo.py
```

В Vim нажмите `<Space>?`.

## Если нет git на сервере

На машине с сетью:

```bash
git clone https://github.com/gaegvl/python-vim-ide.git
tar czf python-vim-ide.tar.gz python-vim-ide
```

На Astra:

```bash
tar xzf python-vim-ide.tar.gz -C ~/opt
bash ~/opt/python-vim-ide/bin/install.sh
```

## Если ruff/debugpy не встали

Бинарные wheels зависят от архитектуры и версии Python. На хосте с интернетом:

```bash
./bin/fetch-wheels.sh 3.9    # под вашу версию: python3 --version
```

Скопируйте `vendor/wheels` на Astra и снова `./bin/install-tools.sh`.

Минимум для «умной» IDE: **jedi** (pure Python, почти всегда встаёт).

## Системные пакеты (по возможности с зеркала Astra)

```bash
sudo apt-get install vim-nox git universal-ctags ripgrep
```

`vim-nox` / Huge Vim: нужны `+python3`, `+terminal`, `+job` (`vim --version`).
