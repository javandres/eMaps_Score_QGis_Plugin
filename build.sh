#!/bin/bash  
echo "Empaquetando archivo .zip" 
if [ ! -d ./dist ]; then
  mkdir -p ./dist;
fi
zip -r dist/emaps.zip . -x '/*.git/*' -x '/*dist/*'
echo "Archivo generado en ./dist/emaps.zip" 