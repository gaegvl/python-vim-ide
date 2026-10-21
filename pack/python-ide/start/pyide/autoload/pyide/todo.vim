" TODO/FIXME по проекту → quickfix
function! pyide#todo#find() abort
  let l:root = pyide#project#root()
  let l:script = get(g:, 'pyide_root', '') . '/tools/todos.py'
  let l:out = system(shellescape(pyide#project#python()) . ' ' . shellescape(l:script) . ' ' . shellescape(l:root))
  try
    let l:data = json_decode(l:out)
  catch
    echom 'TODO: ошибка'
    return
  endtry
  if empty(l:data)
    echom 'TODO/FIXME не найдены'
    return
  endif
  call setqflist(map(copy(l:data), {_, d -> {
        \ 'filename': d.file,
        \ 'lnum': d.line,
        \ 'text': '[' . d.kind . '] ' . d.text}}), 'r')
  copen
  echo 'Найдено: ' . len(l:data)
endfunction
