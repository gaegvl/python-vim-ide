" Отладка: pdb (всегда) или debugpy если установлен
function! pyide#debug#start() abort
  update
  let l:py = pyide#project#python()
  let l:file = expand('%:p')
  call pyide#breakpoint#refresh()

  let l:has_bp = 0
  for l:nr in range(1, line('$'))
    if getline(l:nr) =~# '^\s*breakpoint()\s*$'
      let l:has_bp = 1
      break
    endif
  endfor

  if !l:has_bp
    let l:choice = confirm('Нет breakpoint(). Добавить на строку ' . line('.') . '?', "&Yes\n&Run anyway\n&Cancel", 1)
    if l:choice == 1
      call pyide#breakpoint#toggle()
      update
    elseif l:choice == 0 || l:choice == 3
      return
    endif
  endif

  " debugpy — если модуль есть (для внешней IDE/attach); иначе классический pdb
  let l:cmd = shellescape(l:py) . ' -m pdb ' . shellescape(l:file)
  call system(shellescape(l:py) . ' -c ' . shellescape('import debugpy'))
  if !v:shell_error && get(g:, 'pyide_use_debugpy', 0)
    let l:port = get(g:, 'pyide_debugpy_port', 5678)
    let l:cmd = shellescape(l:py) . ' -m debugpy --listen ' . l:port
          \ . ' --wait-for-client ' . shellescape(l:file)
    echo 'debugpy listen :' . l:port
  endif

  if has('nvim')
    botright split | resize 15
    execute 'terminal ' . l:cmd
  elseif has('terminal')
    execute 'botright terminal ++rows=15 ' . l:cmd
  else
    execute '!' . l:cmd
  endif
endfunction
