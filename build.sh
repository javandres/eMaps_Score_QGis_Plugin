#!/bin/bash  
echo "Empaquetando archivo .zip" 
if [ ! -d ./dist ]; then
  mkdir -p ./dist;
fi
cd ..
zip -r ./eMaps_Score_QGis_Plugin/dist/emaps.zip ./eMaps_Score_QGis_Plugin -x '/*.git/*' -x '/*dist/*'
echo "Archivo generado en ./dist/emaps.zip" 