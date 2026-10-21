" Автодополнение Python: Jedi (если установлен) → иначе встроенный python3 + теги
let s:jedi_script = expand('<sfile>:p:h:h:h') . '/tools/jedi_bridge.py'
if !filereadable(s:jedi_script)
  let s:jedi_script = get(g:, 'pyide_root', '') . '/tools/jedi_bridge.py'
endif

function! pyide#complete#omnifunc(findstart, base) abort
  if a:findstart
    let l:line = getline('.')
    let l:col = col('.') - 1
    while l:col > 0 && l:line[l:col - 1] =~# '\w\|\.'
      let l:col -= 1
    endwhile
    return l:col
  endif

  let l:items = s:jedi_complete(a:base)
  if !empty(l:items)
    return l:items
  endif
  return s:fallback_complete(a:base)
endfunction

function! s:jedi_complete(base) abort
  if !filereadable(s:jedi_script) | return [] | endif
  let l:py = pyide#project#python()
  let l:src = join(getline(1, '$'), "\n")
  let l:tmp = tempname()
  call writefile(split(l:src, "\n", 1), l:tmp)
  let l:cmd = shellescape(l:py) . ' ' . shellescape(s:jedi_script)
        \ . ' complete ' . shellescape(l:tmp)
        \ . ' ' . line('.') . ' ' . col('.')
        \ . ' ' . shellescape(expand('%:p'))
  let l:out = system(l:cmd)
  call delete(l:tmp)
  if v:shell_error | return [] | endif
  try
    let l:data = json_decode(l:out)
  catch
    return []
  endtry
  if type(l:data) != v:t_list | return [] | endif
  let l:result = []
  for l:item in l:data
    if !empty(a:base) && stridx(get(l:item, 'word', ''), a:base) != 0
      continue
    endif
    call add(l:result, {
          \ 'word': get(l:item, 'word', ''),
          \ 'kind': get(l:item, 'kind', ''),
          \ 'menu': get(l:item, 'menu', ''),
          \ 'info': get(l:item, 'info', ''),
          \ 'icase': 1,
          \ })
  endfor
  return l:result
endfunction

function! s:fallback_complete(base) abort
  let l:words = {}
  " слова из буфера
  for l:w in split(join(getline(1, '$'), ' '), '\W\+')
    if len(l:w) >= 2 && (empty(a:base) || stridx(l:w, a:base) == 0)
      let l:words[l:w] = 1
    endif
  endfor
  " ключевые слова Python
  for l:kw in ['False','None','True','and','as','assert','async','await','break',
        \ 'class','continue','def','del','elif','else','except','finally','for',
        \ 'from','global','if','import','in','is','lambda','nonlocal','not','or',
        \ 'pass','raise','return','try','while','with','yield','self','cls',
        \ 'print','len','range','enumerate','zip','map','filter','open','isinstance',
        \ 'hasattr','getattr','setattr','property','staticmethod','classmethod',
        \ 'dataclass','Optional','List','Dict','Tuple','Any','Union']
    if empty(a:base) || stridx(l:kw, a:base) == 0
      let l:words[l:kw] = 1
    endif
  endfor
  " теги
  if !empty(tagfiles())
    for l:t in taglist('^' . a:base)
      let l:words[l:t.name] = 1
    endfor
  endif
  return map(sort(keys(l:words)), {_, w -> {'word': w, 'icase': 1}})
endfunction
