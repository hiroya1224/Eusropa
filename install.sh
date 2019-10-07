#!/bin/sh

### get jupyter data location ###
JUPYTER_LOC=`jupyter --paths | grep 'data' -A 1 | grep -oE '/.*'`

### copy kernel ###
mkdir -p "$JUPYTER_LOC/kernels/euslisp"
cp -r euslisp/ "$JUPYTER_LOC/kernels/euslisp/"

### create kernel.json ###
echo '{' > kernel.json
echo '  "display_name": "EusLisp",' >> kernel.json
echo '  "language": "euslisp",' >> kernel.json
echo '  "argv": [' >> kernel.json
echo '    "python",' >> kernel.json
echo '    "'$JUPYTER_LOC/kernels/euslisp/euslisp-kernel.py'"', >> kernel.json
echo '    "-f", "{connection_file}"' >> kernel.json
echo '  ]' >> kernel.json
echo '}' >> kernel.json
mv kernel.json "$JUPYTER_LOC/kernels/euslisp/kernel.json"

### finish ###
echo 'Installation Complete.'
