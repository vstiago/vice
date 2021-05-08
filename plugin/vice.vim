let s:plugin_root_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h')

python3 << EOF
import sys
from os.path import normpath, join
import vim
plugin_root_dir = vim.eval('s:plugin_root_dir')
python_root_dir = normpath(join(plugin_root_dir, '..', 'python'))
sys.path.insert(0, python_root_dir)
import vice.view as vice
EOF

function! ViceViewAssembly(compiler, parameters)
  python3 vice.view_assembly(vim.eval('a:compiler'), vim.eval('a:parameters'))
  augroup ViceOnChange
    autocmd! * 
    autocmd TextChanged <buffer> call ViceScheduleUpdate()
    autocmd TextChangedI <buffer> call ViceScheduleUpdate()
    autocmd CursorMoved <buffer> call ViceCursorMoved()
    autocmd CursorMoved vice*.s call ViceCursorMoved()
  augroup END
endfunction


function! ViceCursorMoved()
  python3 vice.cursor_moved()
endfunction


function! ViceClearLines()
  python3 vice.clear_lines()
endfunction


function! ViceAddLines()
  python3 vice.add_lines()
endfunction


function! ViceToggleLines()
  python3 vice.toggle_lines()
endfunction


function! ViceScheduleUpdate()
  python3 vice.schedule_update()
endfunction


function! ViceUpdateAssembly(timer_id)
  python3 vice.update_assembly()
endfunction


" Dark
highlight ViceLine1 ctermbg=18 guibg=#000087 " DarkBlue
highlight ViceLine2 ctermbg=22 guibg=#005f00 " DarkGreen
highlight ViceLine3 ctermbg=54 guibg=#5f0087 " Purple4
highlight ViceLine4 ctermbg=59 guibg=#5f5f5f " Grey37
highlight ViceLine5 ctermbg=89 guibg=#87005f " DeepPink4
highlight ViceLine6 ctermbg=124 guibg=#af0000 " Red3
highlight ViceLine7 ctermbg=3 guibg=#808000 " Olive
highlight ViceLine8 ctermbg=90 guibg=#870087 " DarkMagenta
highlight ViceLine9 ctermbg=6 guibg=#008080 " Teal
highlight ViceLine10 ctermbg=17 guibg=#00005f " NavyBlue
highlight ViceLine11 ctermbg=6 guibg=#008000 " Green
highlight ViceLine12 ctermbg=94 guibg=#875f00 " Orange4
highlight ViceLine13 ctermbg=237 guibg=#3a3a3a " Grey23
highlight ViceLine14 ctermbg=52 guibg=#5f0000 " DarkRed
highlight ViceLine15 ctermbg=23 guibg=#005f5f " DeepSkyBlue4
highlight ViceLine16 ctermbg=1 guibg=#800000 " Maroon

" Light

sign define vice_sign_1 linehl=ViceLine1
sign define vice_sign_2 linehl=ViceLine2
sign define vice_sign_3 linehl=ViceLine3
sign define vice_sign_4 linehl=ViceLine4
sign define vice_sign_5 linehl=ViceLine5
sign define vice_sign_6 linehl=ViceLine6
sign define vice_sign_7 linehl=ViceLine7
sign define vice_sign_8 linehl=ViceLine8
sign define vice_sign_9 linehl=ViceLine9
sign define vice_sign_10 linehl=ViceLine10
sign define vice_sign_11 linehl=ViceLine11
sign define vice_sign_12 linehl=ViceLine12
sign define vice_sign_13 linehl=ViceLine13
sign define vice_sign_14 linehl=ViceLine14
sign define vice_sign_15 linehl=ViceLine15
sign define vice_sign_16 linehl=ViceLine16

nnoremap <silent> ,, :call ViceViewAssembly('gcc', '')<CR>
nnoremap <silent> ,. :call ViceViewAssembly('clang', '')<CR>
nnoremap <silent> ,a :call ViceToggleLines()<CR>

