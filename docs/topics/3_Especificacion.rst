.. _especificacion:

=====================================
3 - Especificación de Variables eMAPS
=====================================

Para facilitar el procesamiento planteamos un protocolo de especificación para procesamiento de las variables de la metodología 
que consiste en definir un lenguaje de procesamiento que permita representar el valor en el que cada variable afecta el score de 
caminabilidad en el segmento de calle, permitiendo así abstraer del lenguaje de programación o software utilizado para el cálculo 
del score.

El lenguaje de procesamiento consiste en un archivo de texto plano separado por comas (CSV) que puede ser editado fácilmente en un 
software de hoja de cálculo como LibreOffice Calc, Microsoft Excel, Google Sheets, etc.

La estructura del archivo de texto es la siguiente.

TODO

Para la construcción de las condiciones y reglas de cada variable se han establecido reglas de sintaxis 
para cada tipo de pregunta, y otras de carácter general,  como se describe a continuación

Reglas de sintaxis generales:
-----------------------------

    • Todas las reglas se evalúan de izquierda a derecha,  
    • El valor se asigna al segmento una vez cumpla una condición,
    • Una vez se cumple una condición se ignoran las siguientes reglas
    • Si no cumple ninguna condición y no existe una regla para cualquier otro valor ``(*=N)`` se asignará el valor ``0``
    • Si una pregunta está presente en el protocolo de calificación y no en los datos de entrada se producirá un error de sintaxis.  

Comentarios:

   ``#``	Representa el inicio de una línea de comentario, no será interpretada en el análisis.

Regla cualquier otro valor.-  aplica la puntuación para cualquier valor que no ha cumplido las reglas 
previamente establecidas:

``*={PUNTUACION}``

ejemplo:


Reglas de puntuación:
---------------------

Las reglas de puntuación tienen el siguiente formato:

``{VALOR}:{PUNTUACION}:[{DESCRIPCION}]`` 

Donde ``{VALOR}`` representa el valor que puede tener la pregunta evaluada, 
``{PUNTUACION}`` representa el valor que se asignará si la respuesta de la pregunta evaluada es igual a 
``{VALOR}`` y ``{DESCRIPCION}`` es una descripción de la regla y es de carácter opcional

Una pregunta puede tener una o mas reglas de puntuación de acuerdo al tipo de pregunta 
y a los posibles valores de acuerdo a la configuración de la pregunta en el formulario de evaluación.

.. toctree::
   :caption: Contenido
   :glob:
