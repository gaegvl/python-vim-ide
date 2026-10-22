" Раскладка как VS Code:
" +--------+------------------+
" | tree   |     code         |
" |        +------------------+
" |        |     terminal     |
" +--------+------------------+
let s:term_buf = -1
let s:term_rows = get(g:, 'pyide_term_rows', 12)

function! pyide#layout#ide() abort
  " один буфер кода
  if winnr('$') > 1
    only
  endif

  " 1) дерево слева на всю высоту
  if bufwinnr('[PyIDE-Tree]') == -1
    call pyide#explorer#open()
  endif

  " 2) в окно кода (справа от дерева)
  call s:focus_code()

  " 3) терминал под кодом (не на всю ширину экрана)
  call pyide#layout#terminal_open_below_code()

  " 4) фокус снова в код
  call s:focus_code()
  redraw
  echo 'IDE: дерево | код | терминал   Space+l переключить, Space+e дерево, Space+` терминал'
endfunction

function! pyide#layout#toggle() abort
  let l:has_tree = bufwinnr('[PyIDE-Tree]') != -1
  let l:has_term = s:term_visible()
  if l:has_tree || l:has_term
    call pyide#layout#close_panels()
    echo 'Панели закрыты  (Space+l — снова IDE)'
  else
    call pyide#layout#ide()
  endif
endfunction

function! pyide#layout#close_panels() abort
  let l:tw = bufwinnr('[PyIDE-Tree]')
  if l:tw != -1
    execute l:tw . 'wincmd c'
  endif
  call pyide#layout#terminal_close()
endfunction

function! s:focus_code() abort
  for l:w in range(1, winnr('$'))
    let l:bn = winbufnr(l:w)
    let l:bt = getbufvar(l:bn, '&buftype')
    let l:name = bufname(l:bn)
    if l:name ==# '[PyIDE-Tree]' || l:name ==# '[PyIDE-Term]'
      continue
    endif
    if l:bt ==# 'terminal'
      continue
    endif
    if l:bt ==# '' || l:bt ==# 'help'
      execute l:w . 'wincmd w'
      return
    endif
  endfor
  wincmd l
endfunction

function! s:term_visible() abort
  if s:term_buf > 0 && bufexists(s:term_buf)
    return bufwinnr(s:term_buf) != -1
  endif
  " по имени
  return bufwinnr('[PyIDE-Term]') != -1
endfunction

function! pyide#layout#terminal_open_below_code() abort
  if s:term_visible()
    return
  endif

  call s:focus_code()

  " уже есть мёртвый буфер терминала — показать под кодом
  if s:term_buf > 0 && bufexists(s:term_buf)
    execute 'belowright sbuffer ' . s:term_buf
    execute 'resize ' . s:term_rows
    return
  endif

  if has('nvim')
    belowright split
    execute 'resize ' . s:term_rows
    execute 'terminal ' . &shell
    let s:term_buf = bufnr('%')
    silent! file [PyIDE-Term]
  elseif has('terminal')
    " ++curwin — в текущем split; сначала split
    belowright split
    execute 'resize ' . s:term_rows
    execute 'terminal ++curwin ++close ' . &shell
    let s:term_buf = bufnr('%')
    silent! file [PyIDE-Term]
  else
    belowright new
    execute 'resize ' . s:term_rows
    setlocal buftype=nofile bufhidden=hide noswapfile nobuflisted
    call setline(1, [
          \ '[PyIDE] Нет +terminal в этой сборке Vim.',
          \ 'Поставьте vim-nox (Huge). Пока: :!ls  или  :PyIdeRun',
          \ ])
    let s:term_buf = bufnr('%')
    silent! file [PyIDE-Term]
  endif

  setlocal nonumber norelativenumber
  " навигация из терминала в окна
  if exists(':tnoremap')
    tnoremap <buffer> <C-h> <C-w>h
    tnoremap <buffer> <C-j> <C-w>j
    tnoremap <buffer> <C-k> <C-w>k
    tnoremap <buffer> <C-l> <C-w>l
  endif
  nnoremap <buffer><silent> q :call pyide#layout#terminal_close()<CR>
endfunction

function! pyide#layout#terminal_toggle() abort
  if s:term_visible()
    call pyide#layout#terminal_close()
    call s:focus_code()
  else
    call pyide#layout#terminal_open_below_code()
  endif
endfunction

function! pyide#layout#terminal_close() abort
  let l:w = -1
  if s:term_buf > 0 && bufexists(s:term_buf)
    let l:w = bufwinnr(s:term_buf)
  endif
  if l:w == -1
    let l:w = bufwinnr('[PyIDE-Term]')
  endif
  if l:w != -1
    execute l:w . 'wincmd c'
  endif
endfunction

function! pyide#layout#focus_terminal() abort
  if !s:term_visible()
    call pyide#layout#terminal_open_below_code()
  endif
  let l:w = bufwinnr(s:term_buf)
  if l:w == -1
    let l:w = bufwinnr('[PyIDE-Term]')
  endif
  if l:w != -1
    execute l:w . 'wincmd w'
    if has('nvim') || mode() !=# 't'
      silent! startinsert
    endif
  endif
endfunction

function! pyide#layout#on_vim_enter() abort
  if !get(g:, 'pyide_auto_layout', 1)
    return
  endif
  if &diff
    return
  endif
  " git commit / rebase и т.п.
  if expand('%:t') =~# '^\(COMMIT_EDITMSG\|MERGE_MSG\|git-rebase-todo\)$'
    return
  endif
  call pyide#layout#ide()
endfunction
