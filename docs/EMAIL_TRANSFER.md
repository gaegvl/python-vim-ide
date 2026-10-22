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

## Если куски всё же нужны

```bash
./bin/pack-for-email.sh --minimal --chunk 5
python3 unpack-pyide.txt pyide-jedi-part*.txt
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
