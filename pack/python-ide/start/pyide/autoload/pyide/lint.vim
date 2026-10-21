" Диагностика: ruff → flake8 → pylint → py_compile
let s:diag = []
let s:idx = -1

function! pyide#lint#run() abort
  call pyide#lint#run_async()
endfunction

function! pyide#lint#run_async() abort
  if &filetype !=# 'python' | return | endif
  let l:file = expand('%:p')
  if empty(l:file) || !filereadable(l:file) | return | endif

  let l:cmd = s:pick_linter(l:file)
  if empty(l:cmd)
    return
  endif

  if exists('*job_start')
    let s:job_out = []
    call job_start(l:cmd, {
          \ 'out_cb': {_, m -> add(s:job_out, m)},
          \ 'err_cb': {_, m -> add(s:job_out, m)},
          \ 'exit_cb': {-> s:apply(s:job_out, l:file)},
          \ })
  else
    let l:out = systemlist(join(map(copy(l:cmd), {_, x -> shellescape(x)}), ' '))
    call s:apply(l:out, l:file)
  endif
endfunction

function! s:pick_linter(file) abort
  let l:py = pyide#project#python()
  if executable('ruff')
    return ['ruff', 'check', '--output-format', 'concise', a:file]
  endif
  if executable('flake8')
    return ['flake8', '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s', a:file]
  endif
  if executable('pylint')
    return ['pylint', '-f', 'parseable', '-r', 'n', a:file]
  endif
  " Всегда доступен py_compile
  return [l:py, '-m', 'py_compile', a:file]
endfunction

function! s:apply(lines, file) abort
  call sign_unplace('PyIdeLint', {'buffer': bufnr(a:file)})
  let s:diag = []
  let s:idx = -1
  for l:line in a:lines
    let l:m = matchlist(l:line, '\v^(.{-}):(\d+):(\d+):\s*(.*)$')
    if empty(l:m)
      let l:m = matchlist(l:line, '\v^(.{-}):(\d+):\s*(.*)$')
      if empty(l:m) | continue | endif
      let l:entry = {
            \ 'file': l:m[1], 'lnum': str2nr(l:m[2]), 'col': 1,
            \ 'text': l:m[3], 'type': s:sev(l:m[3])}
    else
      let l:entry = {
            \ 'file': l:m[1], 'lnum': str2nr(l:m[2]), 'col': str2nr(l:m[3]),
            \ 'text': l:m[4], 'type': s:sev(l:m[4])}
    endif
    " py_compile: File "x", line N
    call add(s:diag, l:entry)
    let l:sign = l:entry.type ==# 'E' ? 'PyIdeError' : (l:entry.type ==# 'W' ? 'PyIdeWarning' : 'PyIdeInfo')
    call sign_place(0, 'PyIdeLint', l:sign, a:file, {'lnum': l:entry.lnum})
  endfor

  " Специальный разбор py_compile stderr
  if empty(s:diag)
    for l:line in a:lines
      let l:m = matchlist(l:line, '\vFile "(.{-})", line (\d+)')
      if !empty(l:m)
        call add(s:diag, {'file': l:m[1], 'lnum': str2nr(l:m[2]), 'col': 1, 'text': l:line, 'type': 'E'})
        call sign_place(0, 'PyIdeLint', 'PyIdeError', a:file, {'lnum': str2nr(l:m[2])})
      endif
    endfor
  endif

  let g:pyide_lint_count = len(s:diag)
  if empty(s:diag)
    echo 'Lint: OK'
  else
    echo 'Lint: ' . len(s:diag) . ' issue(s)'
    call setqflist(map(copy(s:diag), {_, d -> {
          \ 'filename': d.file, 'lnum': d.lnum, 'col': d.col,
          \ 'text': d.text, 'type': d.type}}), 'r')
  endif
  call pyide#statusline#refresh()
endfunction

function! s:sev(text) abort
  if a:text =~? '^E\|^F\|^error\|Error\|invalid'
    return 'E'
  endif
  if a:text =~? '^W\|^warning\|Warning'
    return 'W'
  endif
  return 'I'
endfunction

function! pyide#lint#next() abort
  if empty(s:diag) | echom 'Нет диагностики' | return | endif
  let s:idx = (s:idx + 1) % len(s:diag)
  call s:jump(s:diag[s:idx])
endfunction

function! pyide#lint#prev() abort
  if empty(s:diag) | echom 'Нет диагностики' | return | endif
  let s:idx = s:idx <= 0 ? len(s:diag) - 1 : s:idx - 1
  call s:jump(s:diag[s:idx])
endfunction

function! s:jump(d) abort
  if fnamemodify(a:d.file, ':p') !=# expand('%:p')
    execute 'edit ' . fnameescape(a:d.file)
  endif
  call cursor(a:d.lnum, a:d.col)
  echohl WarningMsg | echo a:d.text | echohl None
endfunction

function! pyide#lint#count() abort
  return get(g:, 'pyide_lint_count', 0)
endfunction
