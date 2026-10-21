# PyIDE — офлайн Python IDE для Vim (Astra Linux)

Полноценная IDE-обвязка для **Vim 9.1+** (и Neovim) без интернета из редактора.
Всё лежит в одном каталоге: плагины на Vimscript + мост к Jedi на Python.

## Что умеет

| Возможность | Как |
|---|---|
| Дерево файлов | `<Space>e` |
| Fuzzy-поиск файлов / буферов | `<Space>ff` / `<Space>fb` |
| Поиск по проекту | `<Space>fg` (rg или grep) |
| Автодополнение | `<C-x><C-o>` или `.` (Jedi, иначе буфер+теги) |
| Go to definition / references / doc | `gd` / `gr` / `K` |
| Lint на сохранении | ruff → flake8 → pylint → `py_compile` |
| Format | `<Space>rf` (ruff/black/autopep8) |
| Run / Test / Debug / REPL | `<Space>rr` / `rt` / `rd` / `rv` или F5–F9 |
| Сниппеты | `def`<Tab>, `class`<Tab>, `main`<Tab>… |
| Git gutter + status/blame | авто + `<Space>gs` / `gb` |
| Venv auto-detect | `.venv` / `venv` / `$VIRTUAL_ENV` |
| Statusline | режим, файл, ветка, venv, lint |

## Установка на Astra Linux (без интернета у Vim)

### 1. Скопируйте пакет на сервер

С машины, где есть этот каталог (флешка, scp с другого хоста):

```bash
scp -r python-vim-ide user@astra-host:~/
# или
cp -a python-vim-ide /opt/python-vim-ide
```

### 2. Подключите в Vim

В `~/.vimrc` (создайте, если нет):

```vim
source ~/python-vim-ide/vimrc
" либо:
" source /opt/python-vim-ide/vimrc
```

Проверка:

```bash
vim -c 'PyIdeHealth' -c 'qa'
```

### 3. Опциональные инструменты (офлайн)

На **машине с интернетом** скачайте пакеты и перенесите:

**Jedi (навигация и умное дополнение) — очень рекомендуется:**

```bash
# на машине с сетью:
pip download jedi parso -d ./wheels
# на Astra:
pip install --no-index --find-links=./wheels jedi
```

**Формат + линт (выберите один стек):**

```bash
pip download ruff -d ./wheels          # предпочтительно
# или
pip download black flake8 isort -d ./wheels
pip install --no-index --find-links=./wheels ruff
```

**Системные .deb (если есть зеркало Astra / флешка):**

```bash
sudo apt-get install universal-ctags git ripgrep
# либо скачать .deb и: sudo dpkg -i *.deb
```

Минимум для работы: только `python3` и этот каталог.
Без Jedi останутся буферное дополнение, tags, grep и `py_compile`.

### 4. Virtualenv проекта

```bash
cd /path/to/project
python3 -m venv .venv
# офлайн-установка зависимостей проекта:
.venv/bin/pip install --no-index --find-links=/path/to/wheels -r requirements.txt
```

PyIDE сам подхватит `.venv`.

## Горячие клавиши (leader = Space)

```
Space e     дерево файлов
Space ff    найти файл
Space fb    буферы
Space fg    grep
Space rr    запуск
Space rt    тесты
Space rl    lint
Space rf    format
Space rd    pdb
Space rv    REPL
Space /     комментарий
gd gr K     определение / ссылки / документация
]d [d       следующая/предыдущая ошибка
F5–F9       run / test / lint / format / debug
```

## Настройки

В `~/.vimrc` после `source`:

```vim
let g:pyide_format_on_save = 1      " форматировать при сохранении
let g:pyide_explorer_width = 36
let g:pyide_python = '/opt/myenv/bin/python'  " принудительно
let g:pyide_show_banner = 0
```

## Структура

```
python-vim-ide/
  vimrc                 # точка входа
  README.md
  INSTALL_ASTRA.md
  tools/jedi_bridge.py  # мост к Jedi
  pack/python-ide/start/pyide/
    plugin/             # команды
    autoload/pyide/     # модули IDE
    ftplugin/python.vim
    doc/pyide.txt
```

## Ограничения

- Это не LSP-сервер уровня PyCharm; для полной семантики нужен **jedi** (или позже можно добавить python-lsp-server офлайн).
- Fuzzy-поиск — упрощённый (без fzf); для огромных монореп поставьте `ripgrep` + при желании fzf из .deb.
- Rename через Jedi зависит от версии `jedi`; иначе — интерактивная замена в буфере.

## Команды помощи

```
:PyIdeHealth
:help pyide
:echo pyide#snippet#list()
```
