augroup nvim_http_ftdetect
    au!
    autocmd! BufRead,BufNewFile *.http setlocal filetype=http
augroup END
