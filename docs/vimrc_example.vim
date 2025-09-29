" Minimal vimrc for SNES-IDE contributors
set nocompatible
filetype plugin indent on
syntax on
set number
set tabstop=4
set shiftwidth=4
set expandtab
set autoindent

" Recommended simple mappings
nnoremap <leader>w :w!<CR>
nnoremap <leader>q :q!<CR>

" Project-local settings
if filereadable('.vim_local')
  source .vim_local
endif
