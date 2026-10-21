" Простые сниппеты Python (Tab после триггера), без UltiSnips
let s:snippets = {
      \ 'def':       ["def name(args):", "    pass"],
      \ 'class':     ["class Name:", "    def __init__(self):", "        pass"],
      \ 'if':        ["if cond:", "    pass"],
      \ 'for':       ["for item in iterable:", "    pass"],
      \ 'while':     ["while cond:", "    pass"],
      \ 'try':       ["try:", "    pass", "except Exception as e:", "    raise"],
      \ 'with':      ["with expr as var:", "    pass"],
      \ 'main':      ["def main():", "    pass", "", "if __name__ == '__main__':", "    main()"],
      \ 'pdb':       ["breakpoint()"],
      \ 'log':       ["import logging", "logger = logging.getLogger(__name__)"],
      \ 'dataclass': ["from dataclasses import dataclass", "", "@dataclass", "class Name:", "    field: str"],
      \ 'prop':      ["@property", "def name(self):", "    return self._name"],
      \ 'test':      ["def test_name():", "    assert True"],
      \ 'from':      ["from module import name"],
      \ 'imp':       ["import module"],
      \ 'doc':       ['"""description"""'],
      \ 'init':      ["def __init__(self):", "    pass"],
      \ 'super':     ["super().__init__()"],
      \ }

function! pyide#snippet#expand_or_tab() abort
  let l:line = getline('.')
  let l:col = col('.') - 1
  let l:before = l:col == 0 ? '' : l:line[: l:col - 1]
  let l:word = matchstr(l:before, '\k\+$')
  if has_key(s:snippets, l:word)
    return s:expand(l:word)
  endif
  if pumvisible()
    return "\<C-y>"
  endif
  return "\<Tab>"
endfunction

function! s:expand(trigger) abort
  let l:body = s:snippets[a:trigger]
  let l:indent = matchstr(getline('.'), '^\s*')
  let l:keys = repeat("\<BS>", len(a:trigger))
  let l:keys .= l:body[0]
  for l:l in l:body[1:]
    let l:keys .= "\<CR>" . l:indent . l:l
  endfor
  return l:keys
endfunction

function! pyide#snippet#jump_back() abort
  return "\<C-d>"
endfunction

function! pyide#snippet#list() abort
  echo 'Сниппеты: ' . join(sort(keys(s:snippets)), ', ')
endfunction
