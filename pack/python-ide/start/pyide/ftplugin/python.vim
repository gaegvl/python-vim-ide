" Python buffer defaults for PyIDE
if exists('b:did_pyide_ftplugin') | finish | endif
let b:did_pyide_ftplugin = 1

setlocal expandtab shiftwidth=4 softtabstop=4 tabstop=4
setlocal textwidth=88
setlocal formatoptions+=croql
setlocal commentstring=#\ %s
setlocal suffixesadd=.py
setlocal include=^\\s*\\(from\\\|import\\)
setlocal define=^\\s*\\(def\\\|class\\)\\s\\+

" Быстрый запуск текущего файла
nnoremap <buffer><silent> <F5> :PyIdeRun<CR>
nnoremap <buffer><silent> <F6> :PyIdeTest<CR>
nnoremap <buffer><silent> <F7> :PyIdeLint<CR>
nnoremap <buffer><silent> <F8> :PyIdeFormat<CR>
nnoremap <buffer><silent> <F9> :PyIdeDebug<CR>

" Дополнение после точки (<C-x><C-o> / Jedi)
inoremap <buffer> . .<C-x><C-o>

" Автозакрытие скобок (лёгкое)
inoremap <buffer> ( ()<Left>
inoremap <buffer> [ []<Left>
inoremap <buffer> { {}<Left>
inoremap <buffer> ' ''<Left>
inoremap <buffer> " ""<Left>
