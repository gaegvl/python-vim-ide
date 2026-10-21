" Автоопределение virtualenv
function! pyide#venv#auto() abort
  let l:root = pyide#project#root()
  for l:name in ['.venv', 'venv', 'env']
    let l:py = l:root . '/' . l:name . '/bin/python'
    if executable(l:py)
      let g:pyide_python = l:py
      let g:pyide_venv = l:name
      return
    endif
  endfor
  if !empty($VIRTUAL_ENV) && executable($VIRTUAL_ENV . '/bin/python')
    let g:pyide_python = $VIRTUAL_ENV . '/bin/python'
    let g:pyide_venv = fnamemodify($VIRTUAL_ENV, ':t')
  endif
endfunction

function! pyide#venv#name() abort
  return get(g:, 'pyide_venv', '')
endfunction

function! pyide#venv#python() abort
  return get(g:, 'pyide_python', 'python3')
endfunction
