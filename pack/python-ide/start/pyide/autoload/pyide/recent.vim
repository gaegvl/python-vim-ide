" Недавние файлы
let s:list = []
let s:max = 50

function! pyide#recent#add(path) abort
  if empty(a:path) || !filereadable(a:path) | return | endif
  if a:path =~# 'PyIDE-\|\[PyIDE'
    return
  endif
  call filter(s:list, {_, p -> p !=# a:path})
  call insert(s:list, a:path, 0)
  if len(s:list) > s:max
    let s:list = s:list[: s:max - 1]
  endif
endfunction

function! pyide#recent#list() abort
  return copy(s:list)
endfunction
