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
  " :terminal не через shell — нужен реальный путь, не 'python3' без PATH
  if l:py !~# '[/\\]' 
    let l:full = exepath(l:py)
    if !empty(l:full)
      return l:full
    endif
  endif
  if !executable(l:py)
    echohl ErrorMsg
    echom 'PyIDE: Python не найден: ' . l:py . '  (см. :PyIdeHealth, PATH)'
    echohl None
  endif
  return l:py
endfunction

function! s:module_exists(name) abort
  let l:py = s:python()
  call system(shellescape(l:py) . ' -c ' . shellescape('import ' . a:name))
  return !v:shell_error
endfunction

function! s:term_argv(argv, title) abort
  " Важно: НЕ shellescape для :terminal — иначе execve('''python3''') → «нет файла»
  if has('nvim')
    botright split
    resize 15
    execute 'terminal ' . join(map(copy(a:argv), {_, v -> fnameescape(v)}), ' ')
    execute 'file ' . a:title
    return
  endif

  if exists('*term_start')
    call term_start(a:argv, {
          \ 'term_name': a:title,
          \ 'term_rows': 15,
          \ 'cwd': pyide#project#root(),
          \ })
    wincmd J
    return
  endif

  if exists(':terminal') && has('terminal')
    " ++shell — через shell, кавычки уместны
    let l:cmd = join(map(copy(a:argv), {_, v -> shellescape(v)}), ' ')
    execute 'botright terminal ++rows=15 ++shell ' . l:cmd
    return
  endif

  let l:cmd = join(map(copy(a:argv), {_, v -> shellescape(v)}), ' ')
  let l:out = systemlist(l:cmd)
  call setqflist([], 'r', {'lines': l:out, 'title': a:title})
  copen
endfunction
