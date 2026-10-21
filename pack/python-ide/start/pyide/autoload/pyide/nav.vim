" Навигация: goto / refs / doc / rename / ctags
let s:bridge = ''

function! s:bridge_path() abort
  if empty(s:bridge)
    let s:bridge = get(g:, 'pyide_root', '') . '/tools/jedi_bridge.py'
  endif
  return s:bridge
endfunction

function! s:run_bridge(op, ...) abort
  let l:py = pyide#project#python()
  let l:src = join(getline(1, '$'), "\n")
  let l:tmp = tempname()
  call writefile(split(l:src, "\n", 1), l:tmp)
  let l:cmd = shellescape(l:py) . ' ' . shellescape(s:bridge_path())
        \ . ' ' . a:op . ' ' . shellescape(l:tmp)
        \ . ' ' . line('.') . ' ' . col('.')
        \ . ' ' . shellescape(expand('%:p'))
  if a:0
    let l:cmd .= ' ' . shellescape(a:1)
  endif
  let l:out = system(l:cmd)
  call delete(l:tmp)
  if v:shell_error
    return v:null
  endif
  try
    return json_decode(l:out)
  catch
    return v:null
  endtry
endfunction

function! pyide#nav#goto_definition() abort
  let l:data = s:run_bridge('goto')
  if s:jump_list(l:data) | return | endif
  " fallback: tags
  try
    execute 'tag ' . expand('<cword>')
  catch
    echom 'Определение не найдено (установите jedi или :PyIdeCtags)'
  endtry
endfunction

function! pyide#nav#goto_assignment() abort
  let l:data = s:run_bridge('assignment')
  if s:jump_list(l:data) | return | endif
  call pyide#nav#goto_definition()
endfunction

function! pyide#nav#references() abort
  let l:data = s:run_bridge('references')
  if type(l:data) != v:t_list || empty(l:data)
    " fallback grep
    call pyide#fuzzy#grep(expand('<cword>'))
    return
  endif
  call setqflist(map(copy(l:data), {_, d -> {
        \ 'filename': d.file, 'lnum': d.line, 'col': d.col,
        \ 'text': get(d, 'desc', d.name)}}), 'r')
  copen
endfunction

function! pyide#nav#doc() abort
  let l:data = s:run_bridge('doc')
  let l:doc = type(l:data) == v:t_dict ? get(l:data, 'doc', '') : ''
  if empty(l:doc)
    " pydoc fallback
    let l:word = expand('<cword>')
    let l:out = systemlist(pyide#project#python() . ' -m pydoc ' . shellescape(l:word))
    let l:doc = join(l:out, "\n")
  endif
  call s:show_preview(l:doc)
endfunction

function! pyide#nav#rename() abort
  let l:old = expand('<cword>')
  if empty(l:old) | return | endif
  let l:new = input('Rename ' . l:old . ' → ', l:old)
  if empty(l:new) || l:new ==# l:old | return | endif
  let l:data = s:run_bridge('rename', l:new)
  if type(l:data) == v:t_dict && get(l:data, 'ok')
    silent edit!
    echo 'Renamed'
    return
  endif
  " Простой rename в текущем буфере
  execute '%s/\<' . escape(l:old, '\') . '\>/' . escape(l:new, '\/') . '/gc'
endfunction

function! pyide#nav#code_action() abort
  echo "Code actions:\n  [f] format\n  [i] organize imports\n  [l] lint\n  [r] rename"
  let l:c = nr2char(getchar())
  if l:c ==# 'f' | call pyide#format#buffer()
  elseif l:c ==# 'i' | call pyide#format#organize_imports()
  elseif l:c ==# 'l' | call pyide#lint#run()
  elseif l:c ==# 'r' | call pyide#nav#rename()
  endif
endfunction

function! pyide#nav#ctags() abort
  let l:root = pyide#project#root()
  if !executable('ctags')
    echohl ErrorMsg | echom 'ctags не найден. apt install universal-ctags (офлайн .deb)' | echohl None
    return
  endif
  let l:cmd = 'ctags -R --languages=Python --python-kinds=-i -f '
        \ . shellescape(l:root . '/tags') . ' ' . shellescape(l:root)
  call system(l:cmd)
  if v:shell_error
    echom 'ctags error'
  else
    execute 'set tags+=' . fnameescape(l:root . '/tags')
    echo 'Tags: ' . l:root . '/tags'
  endif
endfunction

function! s:jump_list(data) abort
  if type(a:data) != v:t_list || empty(a:data)
    return 0
  endif
  if type(a:data) == v:t_dict && has_key(a:data, 'error')
    return 0
  endif
  let l:d = a:data[0]
  if empty(get(l:d, 'file', '')) | return 0 | endif
  if fnamemodify(l:d.file, ':p') !=# expand('%:p')
    execute 'edit ' . fnameescape(l:d.file)
  endif
  call cursor(l:d.line, l:d.col)
  return 1
endfunction

function! s:show_preview(text) abort
  pedit PyIDE-Doc
  wincmd P
  setlocal buftype=nofile bufhidden=wipe noswapfile nobuflisted
  setlocal filetype=markdown modifiable
  silent %delete _
  call setline(1, split(a:text, "\n"))
  setlocal nomodifiable
  nnoremap <buffer><silent> q :pclose<CR>
  wincmd p
endfunction
