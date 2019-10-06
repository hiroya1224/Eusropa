# Eusropa
A EusLisp kernel for Jupyter

- Locate the `euslisp` directory under `~/.local/share/jupyter/kernels/`.
- Create `~/.local/share/jupyter/kernels/euslisp/kernel.json` and write as below:
>{  
>    "display_name": "EusLisp",  
>    "language": "euslisp",  
>    "argv": [  
>	"python",  
>	"[/path/to/user_home]/.local/share/jupyter/kernels/euslisp/euslisp-kernel.py",  
>	"-f", "{connection_file}"  
>    ]  
>}  

You need to change `[/path/to/user_home]` to fit your environment (e.g., `..."/home/hiroya/.local/..."` ).
