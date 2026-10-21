" Простой git gutter + status/blame без плагинов
function! pyide#git#refresh() abort
  if !executable('git') | return | endif
  let l:file = expand('%:p')
  if empty(l:file) || !filereadable(l:file) | return | endif
  call sign_unplace('PyIdeGit', {'buffer': bufnr('%')})
  let l:root = system('git -C ' . shellescape(expand('%:p:h')) . ' rev-parse --show-toplevel')
  if v:shell_error | return | endif
  let l:root = trim(l:root)
  let l:rel = l:file[len(l:root) + 1:]
  let l:diff = systemlist('git -C ' . shellescape(l:root) . ' diff -U0 --no-color -- ' . shellescape(l:rel))
  for l:line in l:diff
    let l:m = matchlist(l:line, '^@@ -\(\d\+\)\%(,\(\d\+\)\)\? +\(\d\+\)\%(,\(\d\+\)\)\? @@')
    if empty(l:m) | continue | endif
    let l:old_count = empty(l:m[2]) ? 1 : str2nr(l:m[2])
    let l:new_line = str2nr(l:m[3])
    let l:new_count = empty(l:m[4]) ? 1 : str2nr(l:m[4])
    if l:new_count == 0
      call sign_place(0, 'PyIdeGit', 'PyIdeGitDel', '%', {'lnum': max([1, l:new_line])})
    elseif l:old_count == 0
      for l:i in range(l:new_count)
        call sign_place(0, 'PyIdeGit', 'PyIdeGitAdd', '%', {'lnum': l:new_line + l:i})
      endfor
    else
      for l:i in range(l:new_count)
        call sign_place(0, 'PyIdeGit', 'PyIdeGitMod', '%', {'lnum': l:new_line + l:i})
      endfor
    endif
  endfor
endfunction

function! pyide#git#branch() abort
  if !executable('git') | return '' | endif
  let l:b = system('git -C ' . shellescape(expand('%:p:h')) . ' rev-parse --abbrev-ref HEAD')
  if v:shell_error | return '' | endif
  return trim(l:b)
endfunction

function! pyide#git#status() abort
  if !executable('git') | echom 'git не найден' | return | endif
  let l:out = systemlist('git -C ' . shellescape(pyide#project#root()) . ' status -sb')
  call s:panel(l:out, 'GitStatus')
endfunction

function! pyide#git#blame() abort
  if !executable('git') | echom 'git не найден' | return | endif
  let l:file = expand('%:p')
  let l:out = systemlist('git -C ' . shellescape(expand('%:p:h'))
        \ . ' blame -L ' . line('.') . ',' . line('.') . ' -- ' . shellescape(l:file))
  echo join(l:out, "\n")
endfunction

function! s:panel(lines, title) abort
  botright 12new
  execute 'file ' . a:title
  setlocal buftype=nofile bufhidden=wipe noswapfile nobuflisted
  call setline(1, a:lines)
  setlocal nomodifiable
  nnoremap <buffer><silent> q :close<CR>
endfunction
