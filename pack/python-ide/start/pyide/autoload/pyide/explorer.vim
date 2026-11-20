" Боковая панель файлов (без NERDTree / без сети)
let s:bufname = '[PyIDE-Tree]'
let s:width = get(g:, 'pyide_explorer_width', 32)

function! pyide#explorer#toggle() abort
  let l:w = bufwinnr(s:bufname)
  if l:w != -1
    execute l:w . 'wincmd c'
    return
  endif
  call pyide#explorer#open()
endfunction

function! pyide#explorer#open() abort
  let l:root = pyide#project#root()
  execute 'topleft vertical ' . s:width . ' new'
  silent execute 'file ' . fnameescape(s:bufname)
  setlocal buftype=nofile bufhidden=wipe noswapfile nobuflisted
  setlocal nonumber norelativenumber signcolumn=no
  setlocal nowrap cursorline
  setlocal filetype=pyidetree
  let b:pyide_root = l:root
  let b:pyide_expanded = {}
  call s:render(l:root)
  nnoremap <buffer><silent> <CR> :call <SID>enter()<CR>
  nnoremap <buffer><silent> o    :call <SID>enter()<CR>
  " Мышь только в дереве; LeftMouse+enter после edit уезжал в чужой буфер → E121
  nnoremap <buffer><silent> <LeftRelease> :call <SID>enter()<CR>
  nnoremap <buffer><silent> <2-LeftMouse> :call <SID>enter()<CR>
  nnoremap <buffer><silent> q    :close<CR>
  nnoremap <buffer><silent> R    :call <SID>refresh()<CR>
  nnoremap <buffer><silent> -    :call <SID>up()<CR>
  nnoremap <buffer><silent> cd   :call <SID>cd_here()<CR>
endfunction

function! s:in_tree() abort
  return bufname('%') ==# s:bufname && exists('b:pyide_lines')
endfunction

function! s:list_dir(path) abort
  let l:entries = []
  let l:dirs = []
  let l:files = []
  for l:name in readdir(a:path, {n -> n !~# '^\.\($\|git$\)' && n !=# '__pycache__'})
    let l:full = a:path . '/' . l:name
    if isdirectory(l:full)
      call add(l:dirs, l:name)
    else
      call add(l:files, l:name)
    endif
  endfor
  call sort(l:dirs) | call sort(l:files)
  return map(l:dirs, {_, v -> {'name': v, 'dir': 1}}) + map(l:files, {_, v -> {'name': v, 'dir': 0}})
endfunction

function! s:render(root) abort
  setlocal modifiable
  silent %delete _
  let b:pyide_lines = []
  call setline(1, '# ' . fnamemodify(a:root, ':t') . '/')
  call add(b:pyide_lines, {'path': a:root, 'dir': 1, 'depth': -1})
  call s:render_tree(a:root, 0)
  setlocal nomodifiable
endfunction

function! s:render_tree(path, depth) abort
  for l:e in s:list_dir(a:path)
    let l:full = a:path . '/' . l:e.name
    let l:pad = repeat('  ', a:depth)
    let l:mark = l:e.dir ? (has_key(get(b:, 'pyide_expanded', {}), l:full) ? '▾ ' : '▸ ') : '  '
    call append(line('$'), l:pad . l:mark . l:e.name . (l:e.dir ? '/' : ''))
    call add(b:pyide_lines, {'path': l:full, 'dir': l:e.dir, 'depth': a:depth})
    if l:e.dir && has_key(get(b:, 'pyide_expanded', {}), l:full)
      call s:render_tree(l:full, a:depth + 1)
    endif
  endfor
endfunction

function! s:enter() abort
  if !s:in_tree()
    return
  endif
  let l:lines = b:pyide_lines
  let l:idx = line('.') - 1
  if l:idx < 0 || l:idx >= len(l:lines) | return | endif
  let l:item = l:lines[l:idx]
  if l:item.dir
    if !exists('b:pyide_expanded')
      let b:pyide_expanded = {}
    endif
    if has_key(b:pyide_expanded, l:item.path)
      call remove(b:pyide_expanded, l:item.path)
    else
      let b:pyide_expanded[l:item.path] = 1
    endif
    let l:ln = line('.')
    call s:render(b:pyide_root)
    call cursor(l:ln, 1)
  else
    " открыть файл в окне кода, не теряя дерево
    let l:path = l:item.path
    wincmd p
    if bufname('%') ==# s:bufname
      wincmd l
    endif
    execute 'edit ' . fnameescape(l:path)
  endif
endfunction

function! s:refresh() abort
  if !s:in_tree() || !exists('b:pyide_root')
    return
  endif
  call s:render(b:pyide_root)
endfunction

function! s:up() abort
  if !s:in_tree() || !exists('b:pyide_root')
    return
  endif
  let b:pyide_root = fnamemodify(b:pyide_root, ':h')
  let b:pyide_expanded = {}
  call s:render(b:pyide_root)
endfunction

function! s:cd_here() abort
  if !s:in_tree()
    return
  endif
  let l:lines = b:pyide_lines
  let l:idx = line('.') - 1
  if l:idx < 0 || l:idx >= len(l:lines) | return | endif
  let l:item = l:lines[l:idx]
  let l:dir = l:item.dir ? l:item.path : fnamemodify(l:item.path, ':h')
  execute 'cd ' . fnameescape(l:dir)
  echom 'cd ' . l:dir
endfunction
