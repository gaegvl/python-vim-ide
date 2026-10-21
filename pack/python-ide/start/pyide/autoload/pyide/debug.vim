" Отладка через :Termdebug (gdb) не подходит для Python —
" используем pdb в терминале + breakpoints через set_trace
function! pyide#debug#start() abort
  update
  let l:py = pyide#project#python()
  let l:file = expand('%:p')
  " Вставить breakpoint на текущей строке, если ещё нет
  let l:line = getline('.')
  if l:line !~# 'breakpoint(\|pdb\.set_trace\|breakpoint'
    let l:choice = confirm('Добавить breakpoint() на строку ' . line('.') . '?', "&Yes\n&No\n&Run without", 1)
    if l:choice == 1
      call append(line('.') - 1, repeat(' ', indent('.')) . 'breakpoint()')
      update
    elseif l:choice == 0 || l:choice == 3
      " run without / cancel handled
    endif
    if l:choice == 0 | return | endif
  endif
  let l:cmd = shellescape(l:py) . ' -m pdb ' . shellescape(l:file)
  if has('nvim')
    botright split | resize 15
    execute 'terminal ' . l:cmd
  elseif has('terminal')
    execute 'botright terminal ++rows=15 ' . l:cmd
  else
    execute '!' . l:cmd
  endif
endfunction
