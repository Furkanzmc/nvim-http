" Initial code taken from:
" https://github.com/nicwest/vim-http/blob/master/syntax/http.vim

if exists("b:current_syntax")
    finish
endif

syn keyword HttpMethod  OPTIONS GET HEAD POST PUT DELETE TRACE CONNECT PATCH contained
syn match HttpVariable '\$[aA-zZ]\w\+'
syn match HttpPayloadVariable ':[aA-zZ]\w\+'
syn match HttpUrl  '\(https\|http\)\?:\/\/\(\w\+\(:\w\+\)\?@\)\?\([A-Za-z][-_0-9A-Za-z]*\.\)\{1,}\(\w\{2,}\.\?\)\{1,}\(:[0-9]\{1,5}\)\?\S*'
syn match HttpComment '^# .*$' contains=HttpVariable,HttpPayloadVariable,HttpUrl

syn match HttpProto 'HTTP/[0-9.]\+' contained
syn match HttpStatusCode '[0-9]\{3\}' contained
syn match HttpStatus '[0-9]\{3\} .*$' contained contains=HttpStatusCode
syn match HttpHeaderKey '^[aA-zZ][A-Za-z0-9\-]*:' contained
syn match HttpURILine '^\(OPTIONS\|GET\|HEAD\|POST\|PUT\|DELETE\|TRACE\|CONNECT\|PATCH\)\( .*\)\?\(HTTP/[0-9.]\+\)\?$'  contains=HttpMethod,HttpProto,HttpVariable,HttpUrl contained
syn match HttpResponseLine '^HTTP/[0-9.]\+ [0-9]\{3\}.*$' contains=HttpProto,HttpStatus contained
syn match HttpHeaderLine '^[aA-zZ][A-Za-z0-9\-]*: .*$' contains=HttpHeaderKey contained

syn region HttpHeader start='^\(OPTIONS\|GET\|HEAD\|POST\|PUT\|DELETE\|TRACE\|CONNECT\|PATCH\)\( .*\)\?\(HTTP/[0-9.]\+\)\?$' end='\n\s*\n' contains=HttpURILine,HttpHeaderLine
syn region HttpHeader start='^HTTP/[0-9.]\+ [0-9]\{3\}.*$' end='\n\s*\n' contains=HttpResponseLine,HttpHeaderLine

hi link HttpMethod Type
hi link HttpProto  Statement
hi link HttpHeaderKey Identifier
hi link HttpStatus String
hi link HttpStatusCode Number
hi link HttpVariable Identifier
hi link HttpPayloadVariable Identifier
hi link HttpUrl String
hi link HttpComment Comment

let b:current_syntax = 'http'
