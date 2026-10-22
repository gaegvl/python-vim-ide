" =============================================================================
" Python Vim IDE — офлайн-конфиг для Vim 9.1+ / Neovim (Astra Linux)
" Скопируйте каталог python-vim-ide на сервер и добавьте в ~/.vimrc:
"   source /path/to/python-vim-ide/vimrc
" =============================================================================

if &compatible | set nocompatible | endif

" Leader = Space — ОБЯЗАТЕЛЬНО до любых map; Space сам по себе ничего не делает
let mapleader = ' '
let maplocalleader = '\'
nnoremap <Space> <Nop>
vnoremap <Space> <Nop>
" Чуть больше времени на вторую клавишу после Space (было 500)
set timeout ttimeout
set timeoutlen=1200
set ttimeoutlen=50

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

" --- Мышь: клик = курсор, колесо = скролл, тянуть = выделение --------------
set mouse=a
set mousemodel=popup_setpos
set mousefocus
" Современные терминалы (GNOME/Kitty/Windows Terminal/SSH)
if has('mouse_sgr')
  set ttymouse=sgr
elseif has('mouse_xterm')
  set ttymouse=xterm2
endif
" Колесо мыши (на случай старых терминалов без авто-скролла)
nnoremap <silent> <ScrollWheelUp>     3<C-y>
nnoremap <silent> <ScrollWheelDown>   3<C-e>
inoremap <silent> <ScrollWheelUp>     <C-o>3<C-y>
inoremap <silent> <ScrollWheelDown>   <C-o>3<C-e>
nnoremap <silent> <S-ScrollWheelUp>   <C-u>
nnoremap <silent> <S-ScrollWheelDown> <C-d>
" Двойной клик — слово; тройной — строка (как обычно в Vim с mouse=a)
set clipboard=unnamedplus
set hidden
set updatetime=300
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

" --- Горячие клавиши IDE (Space = leader) -----------------------------------
" Явно <Space>..., не только <leader> — надёжнее на разных Vim/Astra

" Файлы / навигация
nnoremap <silent> <Space>e  :PyIdeExplorerToggle<CR>
nnoremap <silent> <Space>ff :PyIdeFindFile<CR>
nnoremap <silent> <Space>fb :PyIdeFindBuffer<CR>
nnoremap <silent> <Space>fg :PyIdeGrep<CR>
nnoremap <silent> <Space>fr :PyIdeRecent<CR>
nnoremap <silent> <Space>w  :w<CR>
nnoremap <silent> <Space>q  :q<CR>
nnoremap <silent> <Space>x  :bd<CR>

" Python
nnoremap <silent> <Space>rr :PyIdeRun<CR>
nnoremap <silent> <Space>rt :PyIdeTest<CR>
nnoremap <silent> <Space>rl :PyIdeLint<CR>
nnoremap <silent> <Space>rf :PyIdeFormat<CR>
nnoremap <silent> <Space>ri :PyIdeOrganizeImports<CR>
nnoremap <silent> <Space>rd :PyIdeDebug<CR>
nnoremap <silent> <Space>rv :PyIdeRepl<CR>
nnoremap <silent> <Space>o  :PyIdeOutline<CR>
nnoremap <silent> <Space>td :PyIdeTodo<CR>
nnoremap <silent> <Space>b  :PyIdeBreakpoint<CR>
nnoremap <silent> <Space>bc :PyIdeBreakClear<CR>

" Навигация по коду
nnoremap <silent> gd :PyIdeGotoDef<CR>
nnoremap <silent> gD :PyIdeGotoAssign<CR>
nnoremap <silent> gr :PyIdeReferences<CR>
nnoremap <silent> K  :PyIdeDoc<CR>
nnoremap <silent> <Space>rn :PyIdeRename<CR>
nnoremap <silent> ]d :PyIdeDiagNext<CR>
nnoremap <silent> [d :PyIdeDiagPrev<CR>
nnoremap <silent> <Space>ca :PyIdeCodeAction<CR>

" Окна / вкладки
nnoremap <C-h> <C-w>h
nnoremap <C-j> <C-w>j
nnoremap <C-k> <C-w>k
nnoremap <C-l> <C-w>l
nnoremap <silent> <Space>tn :tabnew<CR>
nnoremap <silent> <Space>tc :tabclose<CR>
nnoremap <silent> <Space>=  <C-w>=

" Комментарии / сниппеты
nnoremap <silent> <Space>/ :PyIdeToggleComment<CR>
vnoremap <silent> <Space>/ :PyIdeToggleComment<CR>
inoremap <silent> <Tab> <C-r>=pyide#snippet#expand_or_tab()<CR>
inoremap <silent> <S-Tab> <C-r>=pyide#snippet#jump_back()<CR>

" Поиск
nnoremap <silent> <Space>h :nohlsearch<CR>

" Git
nnoremap <silent> <Space>gs :PyIdeGitStatus<CR>
nnoremap <silent> <Space>gb :PyIdeGitBlame<CR>

" Терминал
nnoremap <silent> <Space>tt :PyIdeTermToggle<CR>
nnoremap <silent> <Space>`  :PyIdeTermFocus<CR>
nnoremap <silent> <C-`>     :PyIdeTermToggle<CR>
nnoremap <silent> <Space>l  :PyIdeLayoutToggle<CR>
nnoremap <silent> <Space>L  :PyIdeLayout<CR>

" Tags / сессия / справка (F1 тоже — если Space? не ловится терминалом)
nnoremap <silent> <Space>ct :PyIdeCtags<CR>
nnoremap <silent> <Space>ss :PyIdeSessionSave<CR>
nnoremap <silent> <Space>sl :PyIdeSessionLoad<CR>
nnoremap <silent> <Space>?  :PyIdeHelp<CR>
nnoremap <silent> <F1>      :PyIdeHelp<CR>

" Автоформат при сохранении (Python + JSON). Отключить: let g:pyide_format_on_save = 0
let g:pyide_format_on_save = get(g:, 'pyide_format_on_save', 1)
" Авто-раскладка IDE при старте. Отключить: let g:pyide_auto_layout = 0
let g:pyide_auto_layout = get(g:, 'pyide_auto_layout', 1)
let g:pyide_explorer_width = get(g:, 'pyide_explorer_width', 28)
let g:pyide_term_rows = get(g:, 'pyide_term_rows', 12)

" --- Автокоманды ------------------------------------------------------------
augroup PyIdeGlobal
  autocmd!
  autocmd BufWritePre *.py,*.json call pyide#format#on_save()
  autocmd BufWritePost *.py call pyide#lint#run_async()
  autocmd BufEnter *.py call pyide#venv#auto()
  autocmd VimEnter * call pyide#venv#auto()
  autocmd VimEnter * call pyide#statusline#setup()
  " Раскладка VS Code: дерево | код | терминал (выкл: let g:pyide_auto_layout = 0)
  autocmd VimEnter * nested call pyide#layout#on_vim_enter()
augroup END

" Загрузка пакета (packadd не нужен для start/)
runtime! pack/python-ide/start/pyide/plugin/pyide.vim
