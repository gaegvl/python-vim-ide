" gcc-подобный toggle комментариев для Python / generic
function! pyide#comment#toggle(line1, line2) abort
  let l:cs = s:comment_string()
  let l:lines = getline(a:line1, a:line2)
  let l:all_commented = 1
  for l:l in l:lines
    if l:l =~# '^\s*$' | continue | endif
    if l:l !~# '^\s*' . escape(l:cs, '.*[]~') 
      let l:all_commented = 0
      break
    endif
  endfor
  for l:nr in range(a:line1, a:line2)
    let l:l = getline(l:nr)
    if l:l =~# '^\s*$' | continue | endif
    if l:all_commented
      call setline(l:nr, substitute(l:l, '^\(\s*\)' . escape(l:cs, '.*[]~') . ' ?', '\1', ''))
    else
      let l:indent = matchstr(l:l, '^\s*')
      call setline(l:nr, l:indent . l:cs . ' ' . l:l[len(l:indent):])
    endif
  endfor
endfunction

function! s:comment_string() abort
  if &filetype ==# 'python' || &filetype ==# 'sh' || &filetype ==# 'yaml' || &filetype ==# 'toml'
    return '#'
  endif
  if &filetype =~# 'javascript\|typescript\|c\|cpp\|java\|go\|rust'
    return '//'
  endif
  if &filetype ==# 'vim'
    return '"'
  endif
  let l:parts = split(&commentstring, '%s')
  return empty(l:parts) ? '#' : trim(l:parts[0])
endfunction
