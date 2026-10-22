" :PyIdeHealth — диагностика окружения
function! pyide#health#check() abort
  call pyide#venv#auto()
  echo '=== PyIDE Health ==='
  echo 'Vim:      ' . v:version . (has('nvim') ? ' (Neovim)' : '')
  echo 'Python:   ' . pyide#project#python()
  echo 'Venv:     ' . (empty(pyide#venv#name()) ? '(system)' : pyide#venv#name())
  echo 'Project:  ' . pyide#project#root()
  echo 'Pack:     ' . get(g:, 'pyide_root', '?')
  echo ''
  echo '--- Инструменты ---'
  for [l:name, l:ok] in [
        \ ['jedi', s:py_mod('jedi')],
        \ ['ruff', executable('ruff')],
        \ ['black', executable('black')],
        \ ['flake8', executable('flake8')],
        \ ['isort', executable('isort')],
        \ ['pytest', executable('pytest') || s:py_mod('pytest')],
        \ ['debugpy', s:py_mod('debugpy')],
        \ ['ctags', executable('ctags')],
        \ ['git', executable('git')],
        \ ['rg', executable('rg')],
        \ ]
    echo printf('  %-12s %s', l:name, l:ok ? 'OK' : 'нет')
  endfor
  echo ''
  echo '--- Клавиши ---'
  echo '  mapleader=' . strtrans(get(g:, 'mapleader', '\\'))
  echo '  Space+e map: ' . (empty(maparg('<Space>e', 'n')) ? 'НЕТ (vimrc не загружен?)' : 'OK')
  echo '  :PyIdeHelp   — шпаргалка; также F1'
  echo ''
  if !s:py_mod('jedi')
    echo 'Установите tools:  python3 ' . get(g:, 'pyide_root', '.') . '/bin/install_tools.py'
  else
    echo 'IDE ready. F1 или :PyIdeHelp — шпаргалка'
  endif
endfunction

function! s:py_mod(name) abort
  call system(shellescape(pyide#project#python()) . ' -c ' . shellescape('import ' . a:name))
  return !v:shell_error
endfunction
