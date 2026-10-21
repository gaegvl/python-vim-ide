" pyide — офлайн Python IDE для Vim 9.1+
if exists('g:loaded_pyide') | finish | endif
let g:loaded_pyide = 1

" Команды
command! -nargs=0 PyIdeExplorerToggle call pyide#explorer#toggle()
command! -nargs=0 PyIdeExplorerOpen   call pyide#explorer#open()
command! -nargs=0 PyIdeFindFile       call pyide#fuzzy#files()
command! -nargs=0 PyIdeFindBuffer     call pyide#fuzzy#buffers()
command! -nargs=? PyIdeGrep           call pyide#fuzzy#grep(<q-args>)
command! -nargs=0 PyIdeRecent         call pyide#fuzzy#recent()

command! -nargs=* -complete=file PyIdeRun  call pyide#run#file(<q-args>)
command! -nargs=* PyIdeTest                call pyide#run#test(<q-args>)
command! -nargs=0 PyIdeLint                call pyide#lint#run()
command! -nargs=0 PyIdeFormat              call pyide#format#buffer()
command! -nargs=0 PyIdeOrganizeImports     call pyide#format#organize_imports()
command! -nargs=0 PyIdeDebug               call pyide#debug#start()
command! -nargs=0 PyIdeRepl                call pyide#run#repl()
command! -nargs=0 PyIdeTerminal            call pyide#run#terminal()

command! -nargs=0 PyIdeGotoDef      call pyide#nav#goto_definition()
command! -nargs=0 PyIdeGotoAssign   call pyide#nav#goto_assignment()
command! -nargs=0 PyIdeReferences   call pyide#nav#references()
command! -nargs=0 PyIdeDoc          call pyide#nav#doc()
command! -nargs=0 PyIdeRename       call pyide#nav#rename()
command! -nargs=0 PyIdeDiagNext     call pyide#lint#next()
command! -nargs=0 PyIdeDiagPrev     call pyide#lint#prev()
command! -nargs=0 PyIdeCodeAction   call pyide#nav#code_action()

command! -range -nargs=0 PyIdeToggleComment call pyide#comment#toggle(<line1>, <line2>)
command! -nargs=0 PyIdeGitStatus    call pyide#git#status()
command! -nargs=0 PyIdeGitBlame     call pyide#git#blame()
command! -nargs=0 PyIdeCtags        call pyide#nav#ctags()
command! -nargs=0 PyIdeHealth       call pyide#health#check()
command! -nargs=0 PyIdeOutline      call pyide#outline#toggle()
command! -nargs=0 PyIdeTodo         call pyide#todo#find()
command! -nargs=0 PyIdeBreakpoint   call pyide#breakpoint#toggle()
command! -nargs=0 PyIdeBreakClear   call pyide#breakpoint#clear()
command! -nargs=0 PyIdeHelp         call pyide#whichkey#show()
command! -nargs=0 PyIdeSessionSave  call pyide#session#save()
command! -nargs=0 PyIdeSessionLoad  call pyide#session#load()

" Знаки для диагностики и git
call sign_define('PyIdeError',   {'text': 'E>', 'texthl': 'ErrorMsg'})
call sign_define('PyIdeWarning', {'text': 'W>', 'texthl': 'WarningMsg'})
call sign_define('PyIdeInfo',    {'text': 'I>', 'texthl': 'MoreMsg'})
call sign_define('PyIdeGitAdd',  {'text': '+ ', 'texthl': 'DiffAdd'})
call sign_define('PyIdeGitMod',  {'text': '~ ', 'texthl': 'DiffChange'})
call sign_define('PyIdeGitDel',  {'text': '- ', 'texthl': 'DiffDelete'})

" Omni-completion для Python
augroup PyIdePlugin
  autocmd!
  autocmd FileType python setlocal omnifunc=pyide#complete#omnifunc
  autocmd FileType python setlocal keywordprg=:PyIdeDoc
  autocmd BufReadPost * call pyide#git#refresh()
  autocmd BufWritePost * call pyide#git#refresh()
  autocmd BufEnter * call pyide#recent#add(expand('%:p'))
augroup END

" Приветствие при первом запуске
if get(g:, 'pyide_show_banner', 1)
  autocmd VimEnter * ++once echom 'PyIDE загружен. :PyIdeHealth — проверка, <Space> — leader'
endif
