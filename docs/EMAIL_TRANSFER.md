# Как доставить wheels на Astra через почту

Почта часто режет `.whl`, `.py`, `.sh`, архивы. Рабочая схема — **перегнать бинарники в обычный текст `.txt`**.

## Способ 1 (рекомендуется): base64 → `.txt`

### На машине, где есть репозиторий (с интернетом)

```bash
cd python-vim-ide

# Минимум (~5–7 МБ текста): только jedi+parso — хватает для gd/дополнения
./bin/pack-for-email.sh --minimal --chunk 2

# Все wheels (ruff, pytest, …) — больше писем
./bin/pack-for-email.sh --chunk 2

# Весь IDE одним пакетом
./bin/pack-for-email.sh --full --chunk 2
```

В каталоге `dist/email/` появятся файлы вида:
- `pyide-mail-wheels.b64.txt` (или `.part000.b64.txt` …)
- `unpack-from-email.py.txt`
- `MANIFEST.txt`

**Прикрепите к письму только `*.txt`.**

### На Astra

1. Сохраните вложения в одну папку, например `~/mail-pyide/`
2. Распаковщик:
   ```bash
   mv unpack-from-email.py.txt unpack-from-email.py
   # только wheels:
   python3 unpack-from-email.py pyide-mail-wheels.b64.txt
   # или куски:
   python3 unpack-from-email.py pyide-mail-wheels.part*.b64.txt
   ```
3. Если это был `--full` — получите каталог `python-vim-ide/`, затем:
   ```bash
   bash ~/…/python-vim-ide/bin/install.sh
   ```
4. Если только wheels — положите `vendor/wheels` в уже существующий клон и:
   ```bash
   bash bin/install-tools.sh
   ```

Проверка: `sha256` из заголовка `.b64.txt` должен совпасть (скрипт сам сверит).

---

## Способ 2: переименовать без кодирования

Иногда проходит, если фильтр смотрит только на расширение:

| Было | Отправить как |
|------|----------------|
| `jedi-….whl` | `jedi-….whl.txt` или `jedi-….dat` / `jedi-….csv` |
| `install.sh` | `install.sh.txt` |
| `*.py` | `*.py.txt` |

На Astra:
```bash
mv jedi-0.20.1-py2.py3-none-any.whl.txt jedi-0.20.1-py2.py3-none-any.whl
```

У вас `.py → .py.txt` уже не проходит — тогда **только способ 1** (base64).

---

## Способ 3: минимум без бинарных wheels

Для «умного» дополнения хватает **jedi + parso** — это pure Python.

На машине с сетью:
```bash
pip download jedi parso -d /tmp/j
cd /tmp/j
unzip jedi-*.whl -d jedi_src
unzip parso-*.whl -d parso_src
# исходники .py можно уложить в один tar и снова pack-for-email,
# либо каждый .py слать как .txt (долго).
```

На Astra поставить в `PYTHONPATH` или:
```bash
pip install --user --no-index --find-links=./wheels jedi
```
(если `.whl.txt` переименовали обратно в `.whl`).

`ruff` / `debugpy` — бинарные; без них IDE всё равно работает (lint через `py_compile`, format JSON/python частично).

---

## Способ 4: вложить `.txt` внутрь `.docx` / `.odt`

Некоторые фильтры пропускают Office, но режут «подозрительные» вложения.

1. `pack-for-email.sh`
2. Откройте Word/Writer → вставьте содержимое `*.b64.txt` **как текст** в документ  
   или прикрепите `.txt` внутрь архива документа (docx = zip)
3. На Astra скопируйте текст обратно в `.b64.txt` и `unpack-from-email.py`

---

## Лимиты писем

Если «файл слишком большой»:
```bash
./bin/pack-for-email.sh --chunk 1    # куски ~1 МБ, несколько писем
```
На Astra скармливайте все `part*.b64.txt` одной командой — порядок склеится по номеру части.

---

## Что не стоит делать

- Пароль на zip часто **не помогает** — фильтр всё равно видит archive/exe.
- Менять только расширение `.whl` → `.zip` — часто тоже блок.
- Слать `.exe` / `.bin` / `.run` — точно блок.

---

## Быстрый чеклист

1. `./bin/pack-for-email.sh --chunk 2`
2. Письма с `*.txt` на Astra
3. `mv unpack-from-email.py.txt unpack-from-email.py`
4. `python3 unpack-from-email.py pyide-mail-*.b64.txt`
5. `bash bin/install-tools.sh` или `bash bin/install.sh`
6. `vim -c 'PyIdeHealth' -c 'qa'`
