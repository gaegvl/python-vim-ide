" :PyIdeHealth — диагностика окружения
function! pyide#health#check() abort
  call pyide#venv#auto()
  let l:py = pyide#project#python()
  let l:pp = pyide#venv#pythonpath()

  echo '=== PyIDE Health ==='
  echo 'Vim:      ' . v:version . (has('nvim') ? ' (Neovim)' : '')
  echo 'Python:   ' . l:py
  echo 'Venv:     ' . (empty(pyide#venv#name()) ? '(system)' : pyide#venv#name())
  echo 'Project:  ' . pyide#project#root()
  echo 'Pack:     ' . get(g:, 'pyide_root', '?')
  if !empty(l:pp)
    echo 'pyroot:   ' . l:pp
    echo 'PYTHONPATH+PATH подхвачены из --target (source env.sh не обязателен в Vim)'
  endif
  echo ''
  echo '--- Инструменты (нужны IDE) ---'
  for [l:name, l:ok] in [
        \ ['jedi', s:py_mod('jedi')],
        \ ['ruff', pyide#venv#has_bin('ruff')],
        \ ['pytest', pyide#venv#has_bin('pytest') || s:py_mod('pytest')],
        \ ]
    echo printf('  %-12s %s', l:name, l:ok ? 'OK' : 'нет')
  endfor
  echo ''
  echo '--- Опционально (можно «нет») ---'
  for [l:name, l:ok, l:hint] in [
        \ ['isort', pyide#venv#has_bin('isort') || s:py_mod('isort'), 'часто нет wheel'],
        \ ['debugpy', s:py_mod('debugpy'), 'часто нет wheel'],
        \ ['black', pyide#venv#has_bin('black'), 'не ставится, хватает ruff'],
        \ ['flake8', pyide#venv#has_bin('flake8'), 'не ставится, хватает ruff'],
        \ ['ctags', executable('ctags'), 'apt: universal-ctags'],
        \ ['git', executable('git'), 'apt: git'],
        \ ['rg', executable('rg'), 'apt: ripgrep'],
        \ ]
    echo printf('  %-12s %-4s  %s', l:name, l:ok ? 'OK' : 'нет', l:hint)
  endfor
  echo ''
  echo '--- Клавиши ---'
  echo '  mapleader=' . strtrans(get(g:, 'mapleader', '\\'))
  echo '  Space+e map: ' . (empty(maparg('<Space>e', 'n')) ? 'НЕТ (vimrc не загружен?)' : 'OK')
  echo '  :PyIdeHelp / F1 — шпаргалка'
  echo ''
  if !s:py_mod('jedi')
    echo 'jedi не виден. В bash:'
    echo '  source ~/.local/share/pyide/env.sh'
    echo '  python3 ' . get(g:, 'pyide_root', '.') . '/bin/install_tools.py'
    echo 'Затем перезапустите Vim и снова :PyIdeHealth'
  elseif !pyide#venv#has_bin('ruff')
    echo 'jedi OK, ruff не в PATH/pyroot/bin — переустановите tools или source env.sh'
  else
    echo 'IDE ready (jedi+ruff). isort/debugpy/black «нет» — нормально.'
  endif
endfunction

function! s:py_mod(name) abort
  let l:py = pyide#project#python()
  let l:pp = pyide#venv#pythonpath()
  " Явно PYTHONPATH — иначе import jedi из pyroot не находится
  let l:cmd = shellescape(l:py) . ' -c ' . shellescape('import ' . a:name)
  if !empty(l:pp)
    let l:env = l:pp
    if !empty($PYTHONPATH) && stridx(':' . $PYTHONPATH . ':', ':' . l:pp . ':') < 0
      let l:env = l:pp . ':' . $PYTHONPATH
    endif
    let l:cmd = 'env PYTHONPATH=' . shellescape(l:env) . ' ' . l:cmd
  endif
  call system(l:cmd)
  return !v:shell_error
endfunction

