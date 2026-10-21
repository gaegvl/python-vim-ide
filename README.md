# PyIDE — полноценная офлайн Python IDE на Vim

Репозиторий: https://github.com/gaegvl/python-vim-ide  

Работает на **Astra Linux** без интернета из редактора. Всё нужное лежит в одном клоне: Vim-плагины + wheel-пакеты (Jedi, Ruff, Pytest, …).

## Быстрый старт (Astra)

```bash
git clone https://github.com/gaegvl/python-vim-ide.git ~/opt/python-vim-ide
# если git недоступен — скопируйте каталог с флешки

bash ~/opt/python-vim-ide/bin/install.sh
vim ~/opt/python-vim-ide/examples/demo.py
```

В Vim: `<Space>?` — шпаргалка, `:PyIdeHealth` — проверка.

`install.sh` делает:
1. Подключает `vimrc` в `~/.vimrc`
2. Ставит из `vendor/wheels` в `~/.local/share/pyide/venv`: **jedi, ruff, pytest, isort, debugpy**

## Что входит в IDE

| Область | Возможности | Клавиши |
|---|---|---|
| Проект | дерево файлов, fuzzy find, grep, recent | `SPC e/ff/fb/fg/fr` |
| Код | дополнение (Jedi), gd/gr/K, rename | `.` / `gd` `gr` `K` |
| Качество | lint, format, organize imports | `SPC rl/rf/ri` F7 F8 |
| Запуск | run, pytest, REPL, terminal | `SPC rr/rt/rv/tt` F5 F6 |
| Отладка | breakpoint ●, pdb | `SPC b` `SPC rd` F9 |
| Структура | outline классов/функций | `SPC o` |
| Задачи | TODO/FIXME по проекту | `SPC td` |
| Git | gutter, status, blame | `SPC gs/gb` |
| Сессия | save/load окон проекта | `SPC ss/sl` |
| Сниппеты | def/class/main/try/… | триггер + `Tab` |
| Venv | `.venv` / tools venv auto | статусбар |

## Состав репозитория

```
python-vim-ide/
  vimrc                      # точка входа IDE
  bin/install.sh             # установка «под ключ»
  bin/install-tools.sh       # только Python tools из wheels
  bin/fetch-wheels.sh        # обновить wheels (нужен интернет)
  vendor/wheels/             # офлайн-пакеты (jedi, ruff, …)
  tools/                     # jedi_bridge, symbols, todos
  pack/python-ide/start/pyide/  # плагины Vim
  examples/                  # демо
  templates/                 # .gitignore для проектов
```

## Офлайн на другой архитектуре / версии Python

Wheels в `vendor/` собраны под **linux x86_64 / Python 3.12** (часть — universal).  
Если на Astra другой Python:

```bash
# на машине с интернетом:
./bin/fetch-wheels.sh 3.11    # или 3.9 / 3.10
# скопируйте vendor/wheels на сервер и:
./bin/install-tools.sh
```

## Настройки

В `~/.vimrc` после `source`:

```vim
let g:pyide_format_on_save = 1
let g:pyide_python_forced = '/path/to/python'   " зафиксировать интерпретатор
let g:pyide_explorer_width = 36
let g:pyide_show_banner = 0
```

## Типовой рабочий день

1. `vim .` в корне проекта (с `.venv` или без)
2. `<Space>e` — открыть файл, `<Space>ff` — поиск
3. Пишете код: `def`<Tab>, дополнение после `.`
4. `<Space>rl` / авто-lint при сохранении
5. `<Space>b` breakpoint → `<Space>rd` отладка
6. `<Space>rt` тесты, `<Space>o` outline
7. `<Space>ss` сохранить сессию на вечер

Подробности: [INSTALL_ASTRA.md](INSTALL_ASTRA.md), [CHEATSHEET.md](CHEATSHEET.md), `:help pyide`
