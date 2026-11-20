" Отладка: pdb (всегда) или debugpy если установлен
function! pyide#debug#start() abort
  update
  call pyide#venv#auto()
  let l:py = pyide#project#python()
  if l:py !~# '[/\\]'
    let l:full = exepath(l:py)
    if !empty(l:full) | let l:py = l:full | endif
  endif
  let l:file = expand('%:p')
  if empty(l:file) || !filereadable(l:file)
    echohl ErrorMsg | echom 'PyIdeDebug: сохраните файл на диск' | echohl None
    return
  endif
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

  let l:argv = [l:py, '-m', 'pdb', l:file]
  call system(shellescape(l:py) . ' -c ' . shellescape('import debugpy'))
  if !v:shell_error && get(g:, 'pyide_use_debugpy', 0)
    let l:port = get(g:, 'pyide_debugpy_port', 5678)
    let l:argv = [l:py, '-m', 'debugpy', '--listen', string(l:port),
          \ '--wait-for-client', l:file]
    echo 'debugpy listen :' . l:port
  endif

  let l:cmd = join(map(copy(l:argv), {_, v -> shellescape(v)}), ' ')
  if has('nvim')
    botright split | resize 15
    call termopen(l:cmd)
  elseif has('terminal')
    execute 'botright terminal ++rows=15 ++shell ++norestore ' . l:cmd
  else
    execute '!' . l:cmd
  endif
endfunction

