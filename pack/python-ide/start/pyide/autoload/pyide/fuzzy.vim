" Fuzzy-поиск файлов/буферов/grep без fzf (чистый Vim)
function! s:prompt(title, items, Callback) abort
  let l:filter = ''
  while 1
    let l:matched = s:filter_items(a:items, l:filter)
    redraw
    echo a:title . ' > ' . l:filter . '  (' . len(l:matched) . ')'
    let l:preview = l:matched[:14]
    for l:i in range(len(l:preview))
      echom printf('  %2d  %s', l:i + 1, l:preview[l:i])
    endfor
    let l:c = getchar()
    if type(l:c) == v:t_number
      if l:c == 27 | redraw | echo '' | return | endif
      if l:c == 13
        if empty(l:matched) | continue | endif
        redraw | echo ''
        call a:Callback(l:matched[0])
        return
      endif
      if l:c == 8 || l:c == 127
        let l:filter = l:filter[:-2]
      elseif l:c == 9 && len(l:matched)
        redraw | echo ''
        call a:Callback(l:matched[0])
        return
      elseif l:c >= 48 && l:c <= 57 && l:c != 48
        let l:n = l:c - 48
        if l:n <= len(l:matched)
          redraw | echo ''
          call a:Callback(l:matched[l:n - 1])
          return
        endif
      elseif l:c >= 32
        let l:filter .= nr2char(l:c)
      endif
    else
      if l:c ==# "\<BS>"
        let l:filter = l:filter[:-2]
      endif
    endif
  endwhile
endfunction

function! s:filter_items(items, filter) abort
  if empty(a:filter) | return a:items[:199] | endif
  let l:parts = split(tolower(a:filter), '\s\+')
  let l:out = []
  for l:item in a:items
    let l:low = tolower(l:item)
    let l:ok = 1
    for l:p in l:parts
      if stridx(l:low, l:p) < 0
        let l:ok = 0
        break
      endif
    endfor
    if l:ok
      call add(l:out, l:item)
      if len(l:out) >= 200 | break | endif
    endif
  endfor
  return l:out
endfunction

function! pyide#fuzzy#files() abort
  let l:root = pyide#project#root()
  let l:files = []
  " Все исходники, не только py
  for l:pat in ['**/*.py', '**/*.toml', '**/*.cfg', '**/*.ini', '**/*.md', '**/*.txt', '**/*.yml', '**/*.yaml', '**/*.json']
    call extend(l:files, pyide#project#files(l:root, l:pat))
  endfor
  call uniq(sort(l:files))
  let l:rel = map(copy(l:files), {_, f -> fnamemodify(f, ':.' )})
  call s:prompt('Find file', l:rel, {f -> execute('edit ' . fnameescape(f))})
endfunction

function! pyide#fuzzy#buffers() abort
  let l:bufs = []
  for l:b in range(1, bufnr('$'))
    if buflisted(l:b) && !empty(bufname(l:b))
      call add(l:bufs, bufname(l:b))
    endif
  endfor
  call s:prompt('Buffers', l:bufs, {f -> execute('buffer ' . fnameescape(f))})
endfunction

function! pyide#fuzzy#grep(...) abort
  let l:query = a:0 && !empty(a:1) ? a:1 : input('Grep> ')
  if empty(l:query) | return | endif
  let l:root = pyide#project#root()
  let l:cmd = ''
  if executable('rg')
    let l:cmd = 'rg --vimgrep --no-heading -n -S ' . shellescape(l:query) . ' ' . shellescape(l:root)
  elseif executable('grep')
    let l:cmd = 'grep -RIn --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=.venv --exclude-dir=venv '
          \ . shellescape(l:query) . ' ' . shellescape(l:root)
  else
    echohl ErrorMsg | echom 'Нет rg/grep' | echohl None
    return
  endif
  let l:out = systemlist(l:cmd)
  if empty(l:out)
    echom 'Ничего не найдено'
    return
  endif
  call setqflist([], 'r', {'lines': l:out, 'efm': '%f:%l:%c:%m,%f:%l:%m'})
  copen
endfunction

function! pyide#fuzzy#recent() abort
  let l:items = pyide#recent#list()
  if empty(l:items)
    echom 'Нет недавних файлов'
    return
  endif
  call s:prompt('Recent', l:items, {f -> execute('edit ' . fnameescape(f))})
endfunction
