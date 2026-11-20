" Автоопределение virtualenv + PyIDE tools venv / --target
function! pyide#venv#auto() abort
  " 1) Явно заданный
  if exists('g:pyide_python_forced') && !empty(g:pyide_python_forced)
    let g:pyide_python = g:pyide_python_forced
    return
  endif

  let l:root = pyide#project#root()

  " 2) Venv проекта
  for l:name in ['.venv', 'venv', 'env']
    let l:py = l:root . '/' . l:name . '/bin/python'
    if executable(l:py)
      let g:pyide_python = l:py
      let g:pyide_venv = l:name
      let g:pyide_pythonpath = ''
      call s:prepend_bin(fnamemodify(l:py, ':h'))
      return
    endif
  endfor

  " 3) Активированный VIRTUAL_ENV
  if !empty($VIRTUAL_ENV) && executable($VIRTUAL_ENV . '/bin/python')
    let g:pyide_python = $VIRTUAL_ENV . '/bin/python'
    let g:pyide_venv = fnamemodify($VIRTUAL_ENV, ':t')
    let g:pyide_pythonpath = ''
    call s:prepend_bin($VIRTUAL_ENV . '/bin')
    return
  endif

  " 4) Глобальный PyIDE tools venv
  for l:ide in [
        \ expand('~/.local/share/pyide/venv/bin/python'),
        \ expand('~/pyide/venv/bin/python'),
        \ ]
    if executable(l:ide)
      let g:pyide_python = l:ide
      let g:pyide_venv = 'pyide'
      let g:pyide_pythonpath = ''
      call s:prepend_bin(fnamemodify(l:ide, ':h'))
      return
    endif
  endfor

  " 5) Режим --target (нет python3-venv) — packages в pyroot + bin/
  for l:pp in [
        \ expand('~/.local/share/pyide/pythonpath'),
        \ expand('~/pyide/pythonpath'),
        \ ]
    if filereadable(l:pp)
      let l:target = trim(readfile(l:pp)[0])
      if isdirectory(l:target)
        call s:apply_target(l:target)
        return
      endif
    endif
  endfor

  " 6) env.sh / прямой pyroot
  for l:target in [
        \ expand('~/.local/share/pyide/pyroot'),
        \ expand('~/pyide/pyroot'),
        \ ]
    if isdirectory(l:target)
      call s:apply_target(l:target)
      return
    endif
  endfor

  let g:pyide_python = 'python3'
  let g:pyide_pythonpath = ''
endfunction

function! s:apply_target(target) abort
  let g:pyide_pythonpath = a:target
  let g:pyide_venv = 'pyide-target'
  " PYTHONPATH для import jedi/pytest
  if empty($PYTHONPATH)
    let $PYTHONPATH = a:target
  elseif stridx(':' . $PYTHONPATH . ':', ':' . a:target . ':') < 0
    let $PYTHONPATH = a:target . ':' . $PYTHONPATH
  endif
  call s:prepend_bin(a:target . '/bin')
  " сброс кэша executable() после смены PATH
  let $PATH = $PATH
  if !empty($PYIDE_PYTHON) && executable($PYIDE_PYTHON)
    let g:pyide_python = $PYIDE_PYTHON
  else
    let g:pyide_python = 'python3'
  endif
endfunction

function! pyide#venv#name() abort
  return get(g:, 'pyide_venv', '')
endfunction

function! pyide#venv#python() abort
  return get(g:, 'pyide_python', 'python3')
endfunction

function! pyide#venv#pythonpath() abort
  return get(g:, 'pyide_pythonpath', '')
endfunction

" Есть ли бинарник в PATH или в pyroot/bin
function! pyide#venv#has_bin(name) abort
  if executable(a:name)
    return 1
  endif
  let l:pp = pyide#venv#pythonpath()
  if !empty(l:pp)
    let l:p = l:pp . '/bin/' . a:name
    if filereadable(l:p) || executable(l:p)
      return 1
    endif
  endif
  return 0
endfunction

function! s:prepend_bin(bin) abort
  if empty(a:bin) || !isdirectory(a:bin) | return | endif
  if stridx(':' . $PATH . ':', ':' . a:bin . ':') < 0
    let $PATH = a:bin . ':' . $PATH
  endif
  let $PATH = $PATH
endfunction
