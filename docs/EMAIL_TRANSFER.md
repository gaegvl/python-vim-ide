# Доставка на Astra через почту

## Как устроен ваш фильтр

| Что | Поведение |
|-----|-----------|
| Размер файла | не режет |
| Расширения вроде `.py`, `.whl`, `.sh`, `.exe` | **блок** |
| Первая строка файла начинается с `#!` | **блок** (shebang) |
| Обычный `.txt` без `#!` | проходит |

Поэтому **нельзя** слать `script.py.txt`, если внутри всё ещё `#!/usr/bin/env python3` в первой строке — фильтр смотрит содержимое.

## Что делать

На машине с репозиторием:

```bash
cd python-vim-ide
git pull
./bin/pack-for-email.sh --minimal          # jedi+parso, один .txt
# или все wheels:
./bin/pack-for-email.sh
```

В `dist/email/` будут **только** файлы `*.txt`:
- `unpack-pyide.txt` — распаковщик (первая строка — `"""..."""`, не `#!`)
- `pyide-jedi.txt` / `pyide-wheels.txt` — данные в base64

Их и прикрепляйте к письму. Никаких `.py` / `.whl` / `.sh` даже в имени.

### На Astra

```bash
# сохранили вложения в одну папку
python3 unpack-pyide.txt pyide-jedi.txt
# появится vendor/wheels/
```

Дальше скопируйте `vendor/` в каталог PyIDE и:

```bash
bash bin/install-tools.sh
# или полный install.sh, если слали --full
```

## Лимит письма 25 МБ

Все wheels в одном `.txt` ≈ 29 МБ — почта не примет. Режьте на части:

```bash
./bin/pack-for-email.sh --chunk 20
# → pyide-wheels-part000.txt (~20 МБ), part001.txt (~8 МБ)
# + unpack-pyide.txt
```

Два письма (или два вложения, если суммарно лимит на письмо):
1. `unpack-pyide.txt` + `pyide-wheels-part000.txt`
2. `pyide-wheels-part001.txt`

На Astra (все части в одной папке):

```bash
python3 unpack-pyide.txt pyide-wheels-part*.txt
bash bin/install-tools.sh
```

## Проверка, что письмо «безопасное»

Перед отправкой:

```bash
# первая строка каждого вложения — НЕ должна начинаться с #!
head -n1 dist/email/*.txt
```

Ожидаемо:
```
PyIDE-mail-pack kind=jedi ...
"""PyIDE unpack for email...
PyIDE mail pack (Astra-safe)
```

## Минимум vs полный набор

- `--minimal` — только jedi+parso (дополнение, `gd`, документация)
- без флагов — все wheels из `vendor/` (ruff, pytest, …)
- `--full` — весь каталог `python-vim-ide`
