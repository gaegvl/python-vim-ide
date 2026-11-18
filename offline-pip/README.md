# Offline pip — отправка библиотек почтой

Два скрипта:

| Скрипт | Где | Назначение |
|--------|-----|------------|
| `pack_library.py` | ПК с интернетом | скачать библиотеку → `.txt` чанки |
| `unpack_library.py` | Astra / без сети | собрать чанки → wheels → `pip install` |

Почта: только `.txt`, без `#!` в первой строке, чанки &lt; 25 МБ.

## 1. Упаковка (с интернетом)

```bash
cd offline-pip
python3 pack_library.py requests
python3 pack_library.py django==4.2 --chunk-mb 20
python3 pack_library.py -r requirements.txt --python-version 3.9
```

Результат в `dist-mail/`:
- `unpack_library.txt`
- `PyLib-requests.txt` или `PyLib-requests-part000.txt`, `part001.txt`, …
- `MANIFEST.txt`

Отправьте все `*.txt` почтой.

## 2. Распаковка (без интернета)

```bash
# сохранили вложения в одну папку
python3 unpack_library.txt PyLib-requests-part*.txt --install
# или в venv:
python3 unpack_library.txt PyLib-requests-part*.txt --install --venv ~/myenv
```

Только распаковать wheels без установки:
```bash
python3 unpack_library.txt PyLib-requests-part*.txt -o ./wheels
```

## Замечания

- Вместе с пакетом качаются **зависимости** (как `pip download`).
- Для Astra укажите версию Python: `--python-version 3.9`
- Если на Astra нет pip — один раз упакуйте ещё и `pip setuptools wheel`, либо они подтянутся как зависимости некоторых пакетов; установщик умеет bootstrap из `pip-*.whl`.
