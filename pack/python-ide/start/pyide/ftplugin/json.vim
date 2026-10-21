" JSON buffer defaults for PyIDE
if exists('b:did_pyide_json') | finish | endif
let b:did_pyide_json = 1

setlocal expandtab shiftwidth=2 softtabstop=2 tabstop=2
setlocal formatoptions-=t
setlocal commentstring=//\ %s

nnoremap <buffer><silent> <F8> :PyIdeFormat<CR>
nnoremap <buffer><silent> <leader>rf :PyIdeFormat<CR>

" Автозакрытие скобок
inoremap <buffer> { {}<Left>
inoremap <buffer> [ []<Left>
inoremap <buffer> " ""<Left>
