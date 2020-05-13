setlocal colorcolumn=
setlocal signcolumn=no
setlocal nonumber

setlocal norelativenumber
setlocal cursorline
setlocal foldmethod=marker

setlocal conceallevel=2
setlocal commentstring=#\ %s

nmap <buffer> <silent> <leader>tt :SendHttpRequest<CR>
