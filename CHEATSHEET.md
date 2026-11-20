# PyIDE — шпаргалка (leader = Space)

## Правка

| Клавиша | Действие |
|---|---|
| `yy` | копировать строку |
| `v` … `y` | выделить и копировать |
| `"+y` | копировать в буфер ОС |
| `p` / `P` | вставить после / перед курсором |
| `"+p` | вставить из буфера ОС |
| `u` | отменить (как Ctrl+Z) |
| `Ctrl+r` | вернуть отменённое |

## Терминал и запуск

| Клавиша | Действие |
|---|---|
| `SPC `` ` | фокус в терминал |
| `SPC tt` / `Ctrl+`` ` | терминал вкл/выкл |
| `Ctrl+w` `w` | следующее окно (код ↔ терминал) |
| `Ctrl+w` `k` / `j` | окно вверх / вниз |
| в терминале `Ctrl+\` `Ctrl+n` | обычный режим Vim, потом окна |
| `SPC rr` / `F5` | запустить открытый `.py` |
| `SPC rt` / `F6` | тесты |
| `SPC rd` / `F9` | debug (pdb) |
| закрыть окно вывода F5 | `Ctrl+\` `Ctrl+n` → `q` (или `:q` / `Ctrl+w` `c` / `SPC x`) |

## Сохранение

| Клавиша | Действие |
|---|---|
| `SPC w` | сохранить файл (делайте до F5 / format) |
| `:w` | то же через командную строку |

## JSON

| Клавиша | Действие |
|---|---|
| открыть `.json` | можно одной длинной строкой |
| `SPC w` | сохранить |
| `F8` / `SPC rf` | развернуть / форматировать (jq или `python -m json.tool`) |

Нужен валидный JSON; иначе ошибка парсинга.

## Форматирование и ruff (Python)

| Клавиша | Действие |
|---|---|
| `F8` / `SPC rf` | format (`ruff format`) |
| `F7` / `SPC rl` | проверка ruff (lint) → замечания |
| `]d` / `[d` | следующее / предыдущее замечание |
| `SPC ri` | organize imports (ruff / isort) |
| `:PyIdeHealth` | jedi + ruff должны быть OK |

## IDE

| Клавиша | Действие |
|---|---|
| `SPC ?` / `F1` | эта справка в Vim |
| `SPC l` | IDE-раскладка вкл/выкл (дерево+терминал) |
| `SPC L` | включить IDE-раскладку |
| `SPC e` | дерево файлов |
| `SPC ff` | найти файл |
| `SPC fb` | буферы |
| `SPC fg` | grep |
| `SPC fr` | недавние |
| `SPC o` | outline |
| `SPC td` | TODO/FIXME |
| `SPC b` | toggle breakpoint |
| `SPC bc` | clear breakpoints |
| `SPC rv` | REPL |
| `gd` `gr` `K` | def / refs / doc |
| `SPC rn` | rename |
| `SPC /` | comment |
| `SPC gs` `gb` | git status / blame |
| `SPC ss` `sl` | session save / load |
| `SPC ct` | ctags |
| `SPC q` `x` | quit / close buffer |

Сниппеты (Insert): `def` `class` `if` `for` `while` `try` `with` `main` `pdb` `log` `dataclass` `prop` `test` `from` `imp` `doc` `init` `super` + **Tab**

Проверка tools: `:PyIdeHealth`. Установка: `python3 bin/install_tools.py` (+ при необходимости `apt install vim-nox git universal-ctags ripgrep`).
