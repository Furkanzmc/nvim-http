let s:initialized_client = 0
let s:script_path = fnamemodify(resolve(expand('<sfile>:p')), ':h')

if !exists('http_client_bind_hotkey')
    let g:http_client_bind_hotkey = 1
endif

if !exists('http_client_json_ft')
    let g:http_client_json_ft = 'javascript'
endif

if !exists('http_client_json_escape_utf')
    let g:http_client_json_escape_utf = 1
endif

if !exists('http_client_result_vsplit')
    let g:http_client_result_vsplit = 1
endif

if !exists('http_client_focus_output_window')
    let g:http_client_focus_output_window = 1
endif

if !exists('http_client_verify_ssl')
    let g:http_client_verify_ssl = 1
endif

if !exists('http_client_preserve_responses')
    let g:http_client_preserve_responses = 0
endif

function! s:run_python(type, args)
    if has('python')
        if a:type == "pyfile"
            execute ":pyfile " . a:args
        else
            execute ":python " . a:args
        endif
    elseif has('python3')
        if a:type == "pyfile"
            execute ":py3file " . a:args
        else
            execute ":python3 " . a:args
        endif
    else
        echohl ErrorMsg
        echomsg 'Error: this plugin requires vim compiled with python support.'
        echohl None
        finish
    endif
endfunction

function! http_client#do_request()
    if !s:initialized_client
        let s:initialized_client = 1
        call <SID>run_python("pyfile", s:script_path . '/http_client.py')
    endif

    call <SID>run_python("python", "do_request_from_buffer()")
endfunction
