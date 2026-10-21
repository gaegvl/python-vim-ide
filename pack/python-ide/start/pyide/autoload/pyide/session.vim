" Сохранение / загрузка сессии IDE на проект
function! s:session_file() abort
  let l:root = pyide#project#root()
  let l:dir = l:root . '/.pyide'
  if !isdirectory(l:dir)
    call mkdir(l:dir, 'p')
  endif
  return l:dir . '/Session.vim'
endfunction

function! pyide#session#save() abort
  let l:file = s:session_file()
  execute 'mksession! ' . fnameescape(l:file)
  " не коммитить сессии по умолчанию — .gitignore шаблон
  echo 'Session saved: ' . l:file
endfunction

function! pyide#session#load() abort
  let l:file = s:session_file()
  if !filereadable(l:file)
    echom 'Нет сессии: ' . l:file
    return
  endif
  execute 'source ' . fnameescape(l:file)
  echo 'Session loaded'
endfunction
