" Шпаргалка горячих клавиш IDE
function! pyide#whichkey#show() abort
  let l:lines = [
        \ '=== PyIDE — leader = <Space> ===',
        \ '',
        \ 'Файлы',
        \ '  e     дерево файлов          ff    найти файл',
        \ '  fb    буферы                 fg    grep по проекту',
        \ '  fr    недавние               w     сохранить',
        \ '',
        \ 'Код Python',
        \ '  rr    запуск (F5)            rt    тесты (F6)',
        \ '  rl    lint (F7)              rf    format (F8)',
        \ '  rd    debug pdb (F9)         rv    REPL',
        \ '  ri    organize imports       o     outline символов',
        \ '  td    TODO/FIXME             b     toggle breakpoint',
        \ '  bc    clear breakpoints',
        \ '',
        \ 'Навигация',
        \ '  gd    определение            gr    ссылки',
        \ '  K     документация           ]d [d диагностика',
        \ '  rn    rename                 ca    code actions',
        \ '  ct    ctags',
        \ '',
        \ 'Git / прочее',
        \ '  gs    git status             gb    blame',
        \ '  tt    терминал               ss    сохранить сессию',
        \ '  sl    загрузить сессию       ?     эта справка',
        \ '  /     комментарий',
        \ '',
        \ 'Сниппеты (Insert + Tab): def class if for try with main pdb test ...',
        \ 'Команда :PyIdeHealth — проверка окружения',
        \ ]
  botright 22new
  silent file [PyIDE-Help]
  setlocal buftype=nofile bufhidden=wipe noswapfile nobuflisted
  setlocal nonumber norelativenumber
  call setline(1, l:lines)
  setlocal nomodifiable
  nnoremap <buffer><silent> q :close<CR>
  nnoremap <buffer><silent> <Esc> :close<CR>
endfunction
