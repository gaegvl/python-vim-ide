" Outline: классы и функции текущего файла
let s:bufname = '[PyIDE-Outline]'

function! pyide#outline#toggle() abort
  let l:w = bufwinnr(s:bufname)
  if l:w != -1
    execute l:w . 'wincmd c'
    return
  endif
  call pyide#outline#open()
endfunction

function! pyide#outline#open() abort
  if &filetype !=# 'python'
    echom 'Outline: только для Python'
    return
  endif
  let l:file = expand('%:p')
  let l:script = get(g:, 'pyide_root', '') . '/tools/symbols.py'
  let l:out = system(shellescape(pyide#project#python()) . ' ' . shellescape(l:script) . ' ' . shellescape(l:file))
  try
    let l:data = json_decode(l:out)
  catch
    echom 'Outline: ошибка разбора'
    return
  endtry
  let l:syms = get(l:data, 'symbols', [])
  botright 14new
  silent execute 'file ' . fnameescape(s:bufname)
  setlocal buftype=nofile bufhidden=wipe noswapfile nobuflisted
  setlocal filetype=pyideoutline nonumber norelativenumber
  let b:pyide_outline = l:syms
  let b:pyide_outline_file = l:file
  setlocal modifiable
  silent %delete _
  if empty(l:syms)
    call setline(1, '  (пусто)')
  else
    let l:i = 1
    for l:s in l:syms
      let l:pad = repeat('  ', get(l:s, 'depth', 0))
      let l:mark = l:s.kind ==# 'C' ? 'C ' : 'ƒ '
      call setline(l:i, printf('%s%s%s  :%d', l:pad, l:mark, l:s.name, l:s.line))
      let l:i += 1
    endfor
  endif
  setlocal nomodifiable
  nnoremap <buffer><silent> <CR> :call <SID>jump()<CR>
  nnoremap <buffer><silent> o    :call <SID>jump()<CR>
  nnoremap <buffer><silent> q    :close<CR>
endfunction

function! s:jump() abort
  let l:idx = line('.') - 1
  if l:idx < 0 || l:idx >= len(get(b:, 'pyide_outline', [])) | return | endif
  let l:s = b:pyide_outline[l:idx]
  let l:file = b:pyide_outline_file
  wincmd p
  if expand('%:p') !=# l:file
    execute 'edit ' . fnameescape(l:file)
  endif
  call cursor(l:s.line, get(l:s, 'col', 1))
  normal! zz
endfunction
