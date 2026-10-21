" Форматирование: ruff format → black → autopep8 → встроенный indent
let g:pyide_format_on_save = get(g:, 'pyide_format_on_save', 0)

function! pyide#format#on_save() abort
  if !g:pyide_format_on_save | return | endif
  if &filetype !=# 'python' | return | endif
  call pyide#format#buffer()
endfunction

function! pyide#format#buffer() abort
  if &filetype !=# 'python' | return | endif
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

  " Минимальный fallback: trim trailing space + ensure final newline
  silent! %s/\s\+$//e
  if !empty(getline('$'))
    call append(line('$'), '')
  endif
  call winrestview(l:view)
  echo 'Trimmed whitespace (установите ruff/black офлайн для полного формата)'
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
