" Автоопределение virtualenv + PyIDE tools venv
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
      call s:prepend_bin(fnamemodify(l:py, ':h'))
      return
    endif
  endfor

  " 3) Активированный VIRTUAL_ENV
  if !empty($VIRTUAL_ENV) && executable($VIRTUAL_ENV . '/bin/python')
    let g:pyide_python = $VIRTUAL_ENV . '/bin/python'
    let g:pyide_venv = fnamemodify($VIRTUAL_ENV, ':t')
    call s:prepend_bin($VIRTUAL_ENV . '/bin')
    return
  endif

  " 4) Глобальный PyIDE tools venv (из bin/install-tools.sh)
  for l:ide in [
        \ expand('~/.local/share/pyide/venv/bin/python'),
        \ expand('~/pyide/venv/bin/python'),
        \ ]
    if executable(l:ide)
      let g:pyide_python = l:ide
      let g:pyide_venv = 'pyide'
      call s:prepend_bin(fnamemodify(l:ide, ':h'))
      return
    endif
  endfor

  " 5) Режим --target (нет python3-venv)
  for l:pp in [
        \ expand('~/.local/share/pyide/pythonpath'),
        \ expand('~/pyide/pythonpath'),
        \ ]
    if filereadable(l:pp)
      let l:target = trim(readfile(l:pp)[0])
      if isdirectory(l:target)
        let $PYTHONPATH = l:target . (empty($PYTHONPATH) ? '' : ':' . $PYTHONPATH)
        call s:prepend_bin(l:target . '/bin')
        let g:pyide_venv = 'pyide-target'
        break
      endif
    endif
  endfor

  let g:pyide_python = 'python3'
endfunction

function! pyide#venv#name() abort
  return get(g:, 'pyide_venv', '')
endfunction

function! pyide#venv#python() abort
  return get(g:, 'pyide_python', 'python3')
endfunction

function! s:prepend_bin(bin) abort
  if empty(a:bin) || !isdirectory(a:bin) | return | endif
  if stridx(':' . $PATH . ':', ':' . a:bin . ':') < 0
    let $PATH = a:bin . ':' . $PATH
  endif
endfunction
