" Statusline в стиле IDE
function! pyide#statusline#setup() abort
  set statusline=%{%pyide#statusline#render()%}
  set tabline=%!pyide#statusline#tabline()
endfunction

function! pyide#statusline#refresh() abort
  redrawstatus
endfunction

function! pyide#statusline#render() abort
  let l:mode = s:mode_label()
  let l:git = pyide#git#branch()
  let l:git = empty(l:git) ? '' : ' | ' . l:git
  let l:venv = pyide#venv#name()
  let l:venv = empty(l:venv) ? '' : ' | venv:' . l:venv
  let l:lint = pyide#lint#count()
  let l:lint = l:lint ? (' | lint:' . l:lint) : ' | ok'
  let l:mod = &modified ? ' [+]' : ''
  let l:ro = &readonly ? ' [RO]' : ''
  return ' ' . l:mode . ' | %f' . l:mod . l:ro . l:git . l:venv
        \ . '%=%y | %l:%c | %p%%' . l:lint . ' '
endfunction

function! pyide#statusline#tabline() abort
  let l:s = ''
  for l:t in range(1, tabpagenr('$'))
    let l:s .= (l:t == tabpagenr() ? '%#TabLineSel#' : '%#TabLine#')
    let l:s .= '%' . l:t . 'T ' . l:t . ' '
    let l:buflist = tabpagebuflist(l:t)
    let l:winnr = tabpagewinnr(l:t)
    let l:name = bufname(l:buflist[l:winnr - 1])
    let l:s .= (empty(l:name) ? '[No Name]' : fnamemodify(l:name, ':t')) . ' '
  endfor
  let l:s .= '%#TabLineFill#%T'
  return l:s
endfunction

function! s:mode_label() abort
  let l:m = mode()
  return get({
        \ 'n': 'NORMAL', 'i': 'INSERT', 'v': 'VISUAL', 'V': 'V-LINE',
        \ "\<C-v>": 'V-BLOCK', 'R': 'REPLACE', 'c': 'CMD', 't': 'TERM',
        \ }, l:m, toupper(l:m))
endfunction
