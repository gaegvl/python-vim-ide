" Шпаргалка горячих клавиш IDE
function! pyide#whichkey#show() abort
  let l:lines = [
        \ '=== PyIDE — leader = <Space> ===',
        \ '',
        \ 'Правка (как Ctrl+C / V / Z)',
        \ '  yy          копировать строку',
        \ '  v … y       выделить и копировать',
        \ '  "+y         копировать в буфер ОС',
        \ '  p / P       вставить после / перед',
        \ '  "+p         вставить из буфера ОС',
        \ '  u           отменить (как Ctrl+Z)',
        \ '  Ctrl-r      вернуть отменённое',
        \ '',
        \ 'Интерфейс (как VS Code)',
        \ '  l     вкл/выкл панели IDE    L     принудительно IDE-layout',
        \ '  e     дерево файлов',
        \ '  `     фокус в терминал       tt    терминал вкл/выкл',
        \ '  Ctrl-`      терминал вкл/выкл',
        \ '  Ctrl-w w    следующее окно (код ↔ терминал ↔ дерево)',
        \ '  Ctrl-w k/j  окно вверх/вниз (из кода в терминал и обратно)',
        \ '  В терминале: Ctrl-\ Ctrl-n — обычный режим Vim, потом Ctrl-w w',
        \ '  Ctrl-h/j/k/l — окна',
        \ '',
        \ 'Запуск',
        \ '  rr / F5     запустить открытый .py',
        \ '  rt / F6     тесты                rv    REPL',
        \ '  rd / F9     debug (pdb)',
        \ '',
        \ 'Файлы',
        \ '  ff    найти файл             fb    буферы',
        \ '  fg    grep                   fr    недавние',
        \ '  w     сохранить              q     выход   x  закрыть буфер',
        \ '',
        \ 'Код Python',
        \ '  rl / F7     lint             rf / F8  format py/json',
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
        \ '  ss    сохранить сессию       sl    загрузить сессию',
        \ '  /     комментарий            ?     эта справка (также F1)',
        \ '',
        \ 'Сниппеты (Insert + Tab): def class if for try with main pdb test ...',
        \ 'Команда :PyIdeHealth — проверка окружения / tools',
        \ ]
  botright 28new
  silent file [PyIDE-Help]
  setlocal buftype=nofile bufhidden=wipe noswapfile nobuflisted
  setlocal nonumber norelativenumber
  call setline(1, l:lines)
  setlocal nomodifiable
  nnoremap <buffer><silent> q :close<CR>
  nnoremap <buffer><silent> <Esc> :close<CR>
endfunction
