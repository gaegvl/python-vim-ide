# Offline wheels for PyIDE

Содержимое ставится командой:

```bash
bash ../../bin/install-tools.sh
```

Текущий набор ориентирован на **Linux x86_64**.  
Пакеты `jedi` / `parso` / `pytest` — универсальные (pure Python).  
`ruff` / `debugpy` / `isort` — бинарные под конкретную платформу и версию CPython.

Обновить набор на машине с интернетом:

```bash
../../bin/fetch-wheels.sh          # текущий python3
../../bin/fetch-wheels.sh 3.11     # под другую версию
```
