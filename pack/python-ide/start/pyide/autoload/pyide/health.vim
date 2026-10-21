" :PyIdeHealth — диагностика окружения
function! pyide#health#check() abort
  echo '=== PyIDE Health ==='
  echo 'Vim:      ' . v:version . (has('nvim') ? ' (Neovim)' : '')
  echo 'Python:   ' . pyide#project#python()
  echo 'Project:  ' . pyide#project#root()
  echo 'Pack:     ' . get(g:, 'pyide_root', '?')
  echo ''
  echo '--- Инструменты ---'
  for [l:name, l:ok] in [
        \ ['jedi (pip)', s:py_mod('jedi')],
        \ ['ruff', executable('ruff')],
        \ ['black', executable('black')],
        \ ['flake8', executable('flake8')],
        \ ['pytest', executable('pytest') || s:py_mod('pytest')],
        \ ['ctags', executable('ctags')],
        \ ['git', executable('git')],
        \ ['rg', executable('rg')],
        \ ]
    echo printf('  %-12s %s', l:name, l:ok ? 'OK' : 'нет (опционально)')
  endfor
  echo ''
  echo 'Минимум: python3. Для IDE-навигации: pip install jedi'
  echo 'Формат/линт: ruff или black+flake8 (офлайн wheel/deb)'
  echo 'Сниппеты: :echo pyide#snippet#list()  или Tab после def/class/main/...'
endfunction

function! s:py_mod(name) abort
  call system(shellescape(pyide#project#python()) . ' -c ' . shellescape('import ' . a:name))
  return !v:shell_error
endfunction
