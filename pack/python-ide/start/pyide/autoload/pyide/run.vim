" Запуск Python / pytest / REPL / терминал
function! pyide#run#file(...) abort
  update
  call pyide#venv#auto()
  let l:py = s:python()
  let l:file = expand('%:p')
  if empty(l:file) || !filereadable(l:file)
    echohl ErrorMsg | echom 'PyIdeRun: сохраните файл на диск перед запуском' | echohl None
    return
  endif
  let l:argv = [l:py, l:file]
  if a:0 && !empty(a:1)
    let l:argv += split(a:1)
  endif
  echom 'PyIdeRun: ' . join(l:argv, ' ')
  call s:term_argv(l:argv, 'PyRun')
endfunction

function! pyide#run#test(...) abort
  update
  call pyide#venv#auto()
  let l:py = s:python()
  let l:root = pyide#project#root()
  let l:argv = []
  if executable('pytest') || s:module_exists('pytest')
    let l:argv = [l:py, '-m', 'pytest', '-q', l:root]
  else
    let l:argv = [l:py, '-m', 'unittest', 'discover', '-s', l:root]
  endif
  if a:0 && !empty(a:1)
    let l:argv += split(a:1)
  endif
  call s:term_argv(l:argv, 'PyTest')
endfunction

function! pyide#run#repl() abort
  call pyide#venv#auto()
  call s:term_argv([s:python()], 'PyREPL')
endfunction

function! pyide#run#terminal() abort
  call pyide#layout#focus_terminal()
endfunction

function! s:python() abort
  let l:py = pyide#project#python()
  if empty(l:py)
    let l:py = 'python3'
  endif
  if l:py !~# '[/\\]'
    let l:full = exepath(l:py)
    if !empty(l:full)
      return l:full
    endif
    " типичные пути Astra/Linux
    for l:cand in ['/usr/bin/python3', '/bin/python3', '/usr/local/bin/python3']
      if executable(l:cand)
        return l:cand
      endif
    endfor
  endif
  if !executable(l:py)
    echohl ErrorMsg
    echom 'PyIDE: Python не найден: ' . l:py . '  (:PyIdeHealth, which python3)'
    echohl None
  endif
  return l:py
endfunction

function! s:module_exists(name) abort
  let l:py = s:python()
  call system(shellescape(l:py) . ' -c ' . shellescape('import ' . a:name))
  return !v:shell_error
endfunction

function! s:close_run_win() abort
  if &buftype ==# 'terminal'
    if mode() =~# 't'
      call feedkeys("\<C-\>\<C-n>", 'n')
    endif
    close
  else
    close
  endif
endfunction

function! s:map_close() abort
  " q закрывает окно вывода F5 (из normal-режима терминала)
  nnoremap <buffer><silent> q :call <SID>close_run_win()<CR>
  nnoremap <buffer><silent> <Esc><Esc> :call <SID>close_run_win()<CR>
endfunction

function! s:term_argv(argv, title) abort
  " Через shell (++shell): PATH и кавычки работают как в обычном терминале.
  " Без ++shell Vim делает execve первого аргумента — 'python3' в кавычках ломается.
  let l:cmd = join(map(copy(a:argv), {_, v -> shellescape(v)}), ' ')

  if has('nvim')
    botright split
    resize 15
    call termopen(l:cmd, {'cwd': pyide#project#root()})
    execute 'file ' . a:title
    call s:map_close()
    return
  endif

  if exists(':terminal') && has('terminal')
    execute 'botright terminal ++rows=15 ++shell ++norestore ' . l:cmd
    try
      execute 'file ' . a:title
    catch
    endtry
    call s:map_close()
    return
  endif

  " Fallback без +terminal
  let l:out = systemlist(l:cmd)
  echo join(l:out, "\n")
endfunction
