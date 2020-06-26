setlocal colorcolumn=
setlocal signcolumn=no
setlocal nonumber

setlocal norelativenumber
setlocal cursorline
setlocal foldmethod=marker

setlocal commentstring=#\ %s

nmap <buffer> <silent> <leader>tt :SendHttpRequest<CR>
