" Форматирование: Python (ruff/black) + JSON (jq / python json.tool)
let g:pyide_format_on_save = get(g:, 'pyide_format_on_save', 1)
let g:pyide_json_indent = get(g:, 'pyide_json_indent', 2)

function! pyide#format#on_save() abort
  if !g:pyide_format_on_save | return | endif
  call pyide#format#buffer()
endfunction

function! pyide#format#buffer() abort
  if &filetype ==# 'json' || expand('%:e') ==# 'json'
    call s:format_json()
    return
  endif
  if &filetype ==# 'python'
    call s:format_python()
    return
  endif
  echom 'Format: поддерживаются python и json'
endfunction

function! s:format_python() abort
  let l:view = winsaveview()
  let l:file = expand('%:p')
  update

  if executable('ruff')
    call system('ruff format ' . shellescape(l:file))
    if !v:shell_error
      silent edit!
      call winrestview(l:view)
      echo 'Formatted with ruff'
      return
    endif
  endif
  if executable('black')
    call system('black -q ' . shellescape(l:file))
    if !v:shell_error
      silent edit!
      call winrestview(l:view)
      echo 'Formatted with black'
      return
    endif
  endif
  if executable('autopep8')
    call system('autopep8 -i ' . shellescape(l:file))
    if !v:shell_error
      silent edit!
      call winrestview(l:view)
      echo 'Formatted with autopep8'
      return
    endif
  endif

  silent! %s/\s\+$//e
  if !empty(getline('$'))
    call append(line('$'), '')
  endif
  call winrestview(l:view)
  echo 'Trimmed whitespace (установите ruff/black офлайн для полного формата)'
endfunction

function! s:format_json() abort
  let l:view = winsaveview()
  let l:file = expand('%:p')
  update

  " 1) jq — если есть в системе
  if executable('jq')
    let l:tmp = tempname()
    call system('jq --indent ' . g:pyide_json_indent . ' . ' . shellescape(l:file) . ' > ' . shellescape(l:tmp))
    if !v:shell_error && getfsize(l:tmp) > 0
      call rename(l:tmp, l:file)
      silent edit!
      call winrestview(l:view)
      echo 'JSON formatted with jq'
      return
    endif
    call delete(l:tmp)
  endif

  " 2) python json.tool / свой скрипт (всегда офлайн)
  let l:script = get(g:, 'pyide_root', '') . '/tools/json_format.py'
  let l:py = pyide#project#python()
  let l:tmp = tempname()
  if filereadable(l:script)
    let l:cmd = shellescape(l:py) . ' ' . shellescape(l:script)
          \ . ' --indent ' . g:pyide_json_indent
          \ . ' ' . shellescape(l:file) . ' ' . shellescape(l:tmp)
  else
    let l:cmd = shellescape(l:py) . ' -m json.tool --no-ensure-ascii '
          \ . shellescape(l:file) . ' > ' . shellescape(l:tmp)
  endif
  call system(l:cmd)
  if v:shell_error || getfsize(l:tmp) <= 0
    call delete(l:tmp)
    " Показать ошибку парсинга
    let l:err = system(shellescape(l:py) . ' -c '
          \ . shellescape('import json,sys; json.load(open(sys.argv[1],encoding="utf-8"))')
          \ . ' ' . shellescape(l:file))
    echohl ErrorMsg
    echo 'JSON format failed: ' . (empty(trim(l:err)) ? 'invalid JSON' : trim(l:err))
    echohl None
    call winrestview(l:view)
    return
  endif
  call rename(l:tmp, l:file)
  silent edit!
  call winrestview(l:view)
  echo 'JSON formatted with python'
endfunction

function! pyide#format#organize_imports() abort
  let l:file = expand('%:p')
  update
  if executable('ruff')
    call system('ruff check --select I --fix ' . shellescape(l:file))
    silent edit!
    echo 'Imports organized (ruff)'
    return
  endif
  if executable('isort')
    call system('isort ' . shellescape(l:file))
    silent edit!
    echo 'Imports organized (isort)'
    return
  endif
  echom 'Нужен ruff или isort'
endfunction
