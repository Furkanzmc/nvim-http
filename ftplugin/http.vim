setlocal foldmethod=marker

command! -buffer -nargs=0 HTTPClientDoRequest call http_client#do_request()

if g:http_client_bind_hotkey
    silent! nnoremap <buffer> <unique> <leader>tt :HTTPClientDoRequest<cr>
endif
