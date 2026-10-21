" Точки останова: знак + вставка/удаление breakpoint()
call sign_define('PyIdeBreak', {'text': '● ', 'texthl': 'ErrorMsg'})

function! pyide#breakpoint#toggle() abort
  if &filetype !=# 'python' | return | endif
  let l:lnum = line('.')
  let l:line = getline(l:lnum)
  if l:line =~# '^\s*breakpoint()\s*$'
    execute l:lnum . 'delete _'
    call sign_unplace('PyIdeBreak', {'buffer': bufnr('%'), 'lnum': l:lnum})
    " сдвинуть знаки после удаления — проще пересканировать
    call pyide#breakpoint#refresh()
    return
  endif
  " если breakpoint на предыдущей строке того же блока
  if l:lnum > 1 && getline(l:lnum - 1) =~# '^\s*breakpoint()\s*$'
    execute (l:lnum - 1) . 'delete _'
    call pyide#breakpoint#refresh()
    return
  endif
  let l:indent = matchstr(l:line, '^\s*')
  if l:line =~# '^\s*$'
    call setline(l:lnum, l:indent . 'breakpoint()')
  else
    call append(l:lnum - 1, l:indent . 'breakpoint()')
  endif
  call pyide#breakpoint#refresh()
endfunction

function! pyide#breakpoint#clear() abort
  let l:view = winsaveview()
  silent! g/^\s*breakpoint()\s*$/d
  call pyide#breakpoint#refresh()
  call winrestview(l:view)
  echo 'Breakpoints cleared'
endfunction

function! pyide#breakpoint#refresh() abort
  call sign_unplace('PyIdeBreak', {'buffer': bufnr('%')})
  for l:nr in range(1, line('$'))
    if getline(l:nr) =~# '^\s*breakpoint()\s*$'
      call sign_place(0, 'PyIdeBreak', 'PyIdeBreak', '%', {'lnum': l:nr})
    endif
  endfor
endfunction

augroup PyIdeBreak
  autocmd!
  autocmd BufReadPost,BufWritePost *.py call pyide#breakpoint#refresh()
augroup END
