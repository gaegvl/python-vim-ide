# Установка на Astra Linux (офлайн)

## Важно: ошибка «нет файла /usr/bin/env»

На части Astra нет `/usr/bin/env`. Не запускайте `./bin/install-tools.sh`.
Только так:

```bash
bash bin/install-tools.sh
bash bin/install.sh
```

Скрипт после установки чинит shebang у `ruff`/`pytest` в venv.

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
