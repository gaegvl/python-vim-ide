" Запуск Python / pytest / REPL / терминал
function! pyide#run#file(...) abort
  update
  let l:py = pyide#project#python()
  let l:file = expand('%:p')
  let l:args = a:0 && !empty(a:1) ? a:1 : ''
  let l:cmd = shellescape(l:py) . ' ' . shellescape(l:file) . (empty(l:args) ? '' : ' ' . l:args)
  call s:term(l:cmd, 'PyRun')
endfunction

function! pyide#run#test(...) abort
  update
  let l:py = pyide#project#python()
  let l:root = pyide#project#root()
  let l:extra = a:0 && !empty(a:1) ? a:1 : ''
  let l:cmd = ''
  if executable('pytest') || s:module_exists('pytest')
    let l:cmd = shellescape(l:py) . ' -m pytest -q ' . shellescape(l:root)
          \ . (empty(l:extra) ? '' : ' ' . l:extra)
  else
    let l:cmd = shellescape(l:py) . ' -m unittest discover -s ' . shellescape(l:root)
  endif
  call s:term(l:cmd, 'PyTest')
endfunction

function! pyide#run#repl() abort
  let l:py = pyide#project#python()
  call s:term(shellescape(l:py), 'PyREPL')
endfunction

function! pyide#run#terminal() abort
  call s:term(&shell, 'Terminal')
endfunction

function! s:module_exists(name) abort
  let l:py = pyide#project#python()
  call system(shellescape(l:py) . ' -c ' . shellescape('import ' . a:name))
  return !v:shell_error
endfunction

function! s:term(cmd, title) abort
  if has('nvim')
    botright split
    resize 15
    execute 'terminal ' . a:cmd
    execute 'file ' . a:title
  elseif exists(':terminal') && has('terminal')
    execute 'botright terminal ++rows=15 ' . a:cmd
  else
    " Fallback: quickfix через system
    let l:out = systemlist(a:cmd)
    call setqflist([], 'r', {'lines': l:out})
    copen
  endif
endfunction
