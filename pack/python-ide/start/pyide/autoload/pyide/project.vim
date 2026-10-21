" Корень проекта
function! pyide#project#root(...) abort
  let l:start = a:0 ? a:1 : expand('%:p:h')
  if empty(l:start) | let l:start = getcwd() | endif
  let l:markers = ['.git', 'pyproject.toml', 'setup.py', 'setup.cfg',
        \ 'requirements.txt', 'Pipfile', 'manage.py', '.venv', 'venv']
  let l:dir = l:start
  while l:dir !=# '/' && !empty(l:dir)
    for l:m in l:markers
      if filereadable(l:dir . '/' . l:m) || isdirectory(l:dir . '/' . l:m)
        return l:dir
      endif
    endfor
    let l:dir = fnamemodify(l:dir, ':h')
  endwhile
  return getcwd()
endfunction

function! pyide#project#python() abort
  if exists('g:pyide_python') && !empty(g:pyide_python)
    return g:pyide_python
  endif
  return 'python3'
endfunction

function! pyide#project#files(...) abort
  let l:root = a:0 ? a:1 : pyide#project#root()
  let l:pat = a:0 > 1 ? a:2 : '**/*.py'
  let l:files = globpath(l:root, l:pat, 0, 1)
  call filter(l:files, {_, f -> f !~# '/\(\.git\|__pycache__\|\.venv\|venv\|\.tox\|node_modules\)/'})
  return l:files
endfunction
