" =============================================================================
" Python Vim IDE — офлайн-конфиг для Vim 9.1+ / Neovim (Astra Linux)
" Скопируйте каталог python-vim-ide на сервер и добавьте в ~/.vimrc:
"   source /path/to/python-vim-ide/vimrc
" =============================================================================

if &compatible | set nocompatible | endif

" Корень пакета (каталог, где лежит этот vimrc)
let g:pyide_root = expand('<sfile>:p:h')
let &runtimepath = g:pyide_root . ',' . &runtimepath
let &packpath = g:pyide_root . ',' . &packpath

" --- Базовые настройки редактора -------------------------------------------
set encoding=utf-8
set fileencodings=utf-8,cp1251,koi8-r,latin1
set number relativenumber
set cursorline
set signcolumn=yes
set colorcolumn=88
set scrolloff=4 sidescrolloff=8
set mouse=a
set clipboard=unnamedplus
set hidden
set updatetime=300
set timeoutlen=500
set splitbelow splitright
set wildmenu wildmode=longest:full,full
set wildignore+=*/.git/*,*/__pycache__/*,*/.venv/*,*/venv/*,*.pyc,*.pyo
set completeopt=menuone,noinsert,noselect,preview
set shortmess+=c
set ignorecase smartcase
set incsearch hlsearch
set expandtab shiftwidth=4 softtabstop=4 tabstop=4
set autoindent smartindent
set foldmethod=indent foldlevelstart=99
set laststatus=2
set showtabline=2
set termguicolors
set background=dark
syntax enable
filetype plugin indent on

" --- История / бэкапы -------------------------------------------------------
let s:state = expand('~/.local/share/pyide')
if !isdirectory(s:state) | call mkdir(s:state, 'p') | endif
let &undodir = s:state . '/undo'
let &backupdir = s:state . '/backup'
let &directory = s:state . '/swap'
for s:d in [&undodir, &backupdir, &directory]
  if !isdirectory(s:d) | call mkdir(s:d, 'p') | endif
endfor
set undofile backup

" --- Цветовая схема (встроенная, без интернета) -----------------------------
try
  colorscheme desert
catch
endtry

" Подсветка trailing whitespace
highlight PyIdeTrailing ctermbg=240 guibg=#3a3a3a
match PyIdeTrailing /\s\+$/

" --- Python: интерпретатор / venv -------------------------------------------
" Приоритет: $VIRTUAL_ENV → .venv → venv → python3
function! PyIdeDetectPython() abort
  if !empty($VIRTUAL_ENV) && executable($VIRTUAL_ENV . '/bin/python')
    return $VIRTUAL_ENV . '/bin/python'
  endif
  for l:cand in ['.venv/bin/python', 'venv/bin/python', 'env/bin/python']
    if executable(l:cand)
      return fnamemodify(l:cand, ':p')
    endif
  endfor
  return 'python3'
endfunction
let g:pyide_python = PyIdeDetectPython()

" --- Горячие клавиши IDE (leader = пробел) ----------------------------------
let mapleader = "\<Space>"
let maplocalleader = "\\"

" Файлы / навигация
nnoremap <silent> <leader>e  :PyIdeExplorerToggle<CR>
nnoremap <silent> <leader>ff :PyIdeFindFile<CR>
nnoremap <silent> <leader>fb :PyIdeFindBuffer<CR>
nnoremap <silent> <leader>fg :PyIdeGrep<CR>
nnoremap <silent> <leader>fr :PyIdeRecent<CR>
nnoremap <silent> <leader>w  :w<CR>
nnoremap <silent> <leader>q  :q<CR>
nnoremap <silent> <leader>x  :bd<CR>

" Python
nnoremap <silent> <leader>rr :PyIdeRun<CR>
nnoremap <silent> <leader>rt :PyIdeTest<CR>
nnoremap <silent> <leader>rl :PyIdeLint<CR>
nnoremap <silent> <leader>rf :PyIdeFormat<CR>
nnoremap <silent> <leader>ri :PyIdeOrganizeImports<CR>
nnoremap <silent> <leader>rd :PyIdeDebug<CR>
nnoremap <silent> <leader>rv :PyIdeRepl<CR>
nnoremap <silent> <leader>o  :PyIdeOutline<CR>
nnoremap <silent> <leader>td :PyIdeTodo<CR>
nnoremap <silent> <leader>b  :PyIdeBreakpoint<CR>
nnoremap <silent> <leader>bc :PyIdeBreakClear<CR>

" Навигация по коду
nnoremap <silent> gd :PyIdeGotoDef<CR>
nnoremap <silent> gD :PyIdeGotoAssign<CR>
nnoremap <silent> gr :PyIdeReferences<CR>
nnoremap <silent> K  :PyIdeDoc<CR>
nnoremap <silent> <leader>rn :PyIdeRename<CR>
nnoremap <silent> ]d :PyIdeDiagNext<CR>
nnoremap <silent> [d :PyIdeDiagPrev<CR>
nnoremap <silent> <leader>ca :PyIdeCodeAction<CR>

" Окна / вкладки
nnoremap <C-h> <C-w>h
nnoremap <C-j> <C-w>j
nnoremap <C-k> <C-w>k
nnoremap <C-l> <C-w>l
nnoremap <silent> <leader>tn :tabnew<CR>
nnoremap <silent> <leader>tc :tabclose<CR>
nnoremap <silent> <leader>=  <C-w>=

" Комментарии / сниппеты
nnoremap <silent> <leader>/ :PyIdeToggleComment<CR>
vnoremap <silent> <leader>/ :PyIdeToggleComment<CR>
inoremap <silent> <Tab> <C-r>=pyide#snippet#expand_or_tab()<CR>
inoremap <silent> <S-Tab> <C-r>=pyide#snippet#jump_back()<CR>

" Поиск
nnoremap <silent> <leader>h :nohlsearch<CR>

" Git
nnoremap <silent> <leader>gs :PyIdeGitStatus<CR>
nnoremap <silent> <leader>gb :PyIdeGitBlame<CR>

" Терминал
nnoremap <silent> <leader>tt :PyIdeTerminal<CR>

" Tags / сессия / справка
nnoremap <silent> <leader>ct :PyIdeCtags<CR>
nnoremap <silent> <leader>ss :PyIdeSessionSave<CR>
nnoremap <silent> <leader>sl :PyIdeSessionLoad<CR>
nnoremap <silent> <leader>?  :PyIdeHelp<CR>

" Автоформат при сохранении (Python + JSON). Отключить: let g:pyide_format_on_save = 0
let g:pyide_format_on_save = get(g:, 'pyide_format_on_save', 1)

" --- Автокоманды ------------------------------------------------------------
augroup PyIdeGlobal
  autocmd!
  autocmd BufWritePre *.py,*.json call pyide#format#on_save()
  autocmd BufWritePost *.py call pyide#lint#run_async()
  autocmd BufEnter *.py call pyide#venv#auto()
  autocmd VimEnter * call pyide#venv#auto()
  autocmd VimEnter * call pyide#statusline#setup()
augroup END

" Загрузка пакета (packadd не нужен для start/)
runtime! pack/python-ide/start/pyide/plugin/pyide.vim
