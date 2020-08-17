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

.. tabularcolumns:: |p{1cm}|p{7cm}|

.. csv-table:: Estructura
   :file: _files/emaps.csv
   :header-rows: 1
   :class: longtable
   :widths: 1 1 1 1 1 1 1

Para la construcción de las condiciones y reglas de cada variable se han establecido reglas de sintaxis 
para cada tipo de pregunta, y otras de carácter general,  como se describe a continuación

*NOTA: el protocolo evaluará todas las preguntas especificacas en el archivo CSV, se recomienda que en la especificación de variables
consten todas las preguntas del formulario de levantamiento de información par facilitar modificaciones  o variaciones en la 
asignación de puntajes, para las preguntas que se desea excluir en el cálucolo utilizar la opción "required=FALSE" .*


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


Reglas de puntajes:
---------------------

Las reglas para asignación de puntajes tienen el siguiente formato:

``{VALOR}:{PUNTUACION}:[{DESCRIPCION}]`` 

Donde ``{VALOR}`` representa el valor que puede tener la pregunta evaluada, 
``{PUNTUACION}`` representa el valor que se asignará si la respuesta de la pregunta evaluada es igual a 
``{VALOR}`` y ``{DESCRIPCION}`` es una descripción de la regla y es de carácter opcional

Una pregunta puede tener una o mas reglas de puntuación de acuerdo al tipo de pregunta 
y a los posibles valores de acuerdo a la configuración de la pregunta en el formulario de evaluación.


Pregunta de tipo Bool
---------------------
Representa a preguntas de tipo verdadero/falso ejemplo:

``{TRUE | FALSE} = {PUNTUACION} {:[COMENTARIO]}``

ejemplo:

=============        =============================
variable             Q_008a
=============        =============================
desc                 Semáforo vehicular - inicial 
alias                seg_semaforo_vehicular_ini
level                segment 
section              building
scale                intersections
subscale             intersections_positive
aggregate      
aggregate_ref        Q_008
**type**             **bool**
required             TRUE
sum_type             positive
**option_1**         **True=1:Verdadero**
**option_2**         **False=0:Falso**
=============        =============================

Para la variable de ejemplo ``Q_008a`` se evaluará cada encuesta asignando el puntaje ``1`` cuando la respuesta es Verdadero y ``0`` cuando la respuesta es Falso

Pregunta de tipo Numérico:
--------------------------
Evalúa una expresión numérica mediante reglas de comparación utilizando los operadores (<, >, <=, >=):

En éste tipo de preguntas opcionalmente puede utilizar paréntesis para agrupar las condiciones y facilitar la lectura de la expresión

La condición para tipo numérico tiene la siguiente sintaxis:

``[(] {>|<|>=|<}={VALOR}, {>|<|>=|<=}={VALOR}, …   [)] = {PUNTUACIÓN} [:{COMENTARIO}]``

=============        =============================
variable             Q_008
=============        =============================
desc                 Semáforo - inicial 
alias                seg_semaforo_ini
level                segment 
section              building
scale                intersections
subscale             intersections_positive
aggregate            TRUE
aggregate_ref        
**type**             **numeric**
required             TRUE
sum_type             positive
**option_1**         **(>=1, <=6)=1**
**option_2**         **(>=7)=2**
**option_3**         ***=0**
=============        =============================

Para la variable de ejemplo ``Q_008`` se evaluará cada encuesta asignando el puntaje ``1`` si la respuesta a la pregunta en la encuesta es ``>=1 y <=6``,  obtendrá un valor de 2 cuando la respuesta cumple ``>=7`` y se asignará ``0`` en cualquier otro caso.

Pregunta de tipo Texto:
-----------------------
Evalúa una expresión de cadena de texto, su seintaxis es:

``{VALOR}={PUNTUACION} [:{DESCRIPCION}]``

Ejemplo:

=============        ==================================
variable             Q_023
=============        ==================================
desc                 Construcciones bien mantenidas
alias                build_maintenance
level                parcel 
section              building
scale                building_positive
subscale             building_maintenance
aggregate            
aggregate_ref        Q_023_SEG
**type**             **option**
required             TRUE
sum_type             positive
**option_1**         **A=1:Bueno (76-100%)**
**option_2**         **B=0:Regular (51-75%)**
**option_3**         **C=0:Malo**
**option_4**         **D=0:Precario**
**option_5**         **E=0:N/S o N/A**
=============        ==================================

Para la variable de ejemplo ``Q_023`` se evaluará cada encuesta asignando el puntaje: ``1`` si la respuesta es ``A``, 0 si las respuestas son ``B`` o ``C`` o ``D`` o ``E`` 

*NOTA: en éste caso se podría haber utilizado la regla "cualquier otro valor" para indicar las opciones que asignan ``0`` al puntaje, 
sin embargo para mejor legibilidad se recomienda que consten todas las opciones de respuesta del formulario de levantamiento.*

Pregunta de tipo Fórmula
------------------------

Evalúa una pregunta aplicando una fórmula sobre el valor de la respuesta en el formulario.

la fórmula puede contener operadores matemáticos:

========    ================  ======================
Operador    Descripción       Ejemplo
========    ================  ======================
"+"         Suma              3+2 ``# r es 5``
"-"         Resta             4-7 ``# r es -3``
"-"         Negación          -7 ``# r es -7``
"*"         Multiplicación    2*6 ``# r es 12``
"**"        Exponente         2*\*6 ``# r es 64``
"/"         División          3.5/2 ``# r es 1.75``
"//"        División Entera   3.5//2 ``# r es 1.0``
"%"         Módulo            7%2 ``# r es 1``
========    ================  ======================

y las siguientes variables:

================  =============================================
Variable          Descripción
================  =============================================
[value]           Expresa el valor que se está evaluando
[segment_length]  Expresa la longitud del segmento de calle que se está evaluando
[segment_slope]   Expresa la pendiente del segmento que se está evaluando
================  =============================================

Ejemplo:

=============        ==================================
variable             Q_040_l
=============        ==================================
desc                 Luminarias - Lado izquierdo
alias                seg_acera_luminarias_izq
level                segment 
section              streetscape
scale                streetscape_positive
subscale             lighting
aggregate            
aggregate_ref        Q_040
**type**             **formula**
required             TRUE
sum_type             positive
**option_1**         **([value]/[segment_length])*100**
=============        ==================================


Pregunta de tipo Slope (Pendiente)
----------------------------------
Aplica reglas de valor numérico sobre el valor de porcentaje de la pendiente del segmento de calle evaluado, ejemplo:

=============        ==================================
variable             Q_SLOPE
=============        ==================================
desc                 Pendiente
alias                seg_pendiente
level                segment 
section              streetscape
scale                streetscape_negative
subscale             slope
aggregate            
aggregate_ref        
**type**             **slope**
required             TRUE
sum_type             negative
**option_1**         **(>=0, <=0.05)=0**
**option_2**         **(>0.05, <=0.1)=-1**
**option_3**         **(>0.1, <=0.15)=-2**
**option_4**         **(>0.15)=-3**
**option_5**         ***=0**
=============        ==================================

Para la variable de ejemplo ``Q_SLOPE`` se evaluará el porcentaje de pendiente del segmento de calle y asignará el valor de acuerdo
a la evaluación de las reglas, en el ejemplo asignando un valor negativo para pendientes mayores a ``0.05``

Preguntas Agregadas
-------------------
Aplica a todas las preguntas cuyo parámetros ``aggregate`` sea ``TRUE`` y realiza el procesamiento de la siguiente manera:

* Realiza el cálculo para todas las preguntas que tiene relación de agregación,  ésta relación de agregación se establece en el parámetro ``aggregate_ref`` de la pregunta, y deberá contener el código de la pregunta a la que se agregará el resultado.

* Obtiene el valor agregado de las preguntas hijas, aplicando las siguientes condiciones que puede establecer el parámetro “type” de la pregunta:   

   * "sum" aplica como resultado la suma de las preguntas hijas evaluadas
   * "max" aplica como resultado el valor máximo de las preguntas hijas evaluadas
   * "min" aplica como resultado el valor mínimo de las preguntas hijas evaluadas
   * "count" aplica como resultado el valor del número de preguntas hijas evaluadas
   * "avg" aplica como resultado el valor promedio de las preguntas hijas evaluadas
   * "Numeric" aplica las reglas de tipo “numérico” a la suma de las preguntas hijas evaluadas
   * "Formula" aplica las reglas de tipo formula a la suma de las preguntas hijas evaluadas

Ejemplo:

Pregunta de agregación:

=============        ==================================
variable             Q_037
=============        ==================================
desc                 Basureros Públicos en Acera
alias                seg_acera_basureros
level                segment 
section              streetscape
scale                streetscape_positive
subscale             trash_cans
**aggregate**        **TRUE**
aggregate_ref        
**type**             **numeric**
required             TRUE
sum_type             positive
**option_1**         **(>0)=1**
**option_2**         ***=0**
=============        ==================================

Preguntas agregadas o hijas:

=================    =============================================
variable             Q_037_l
=================    =============================================
desc                 Basureros Públicos en Acera - Lado izquierdo
alias                seg_acera_basureros_izq
level                segment 
section              streetscape
scale                streetscape_positive
subscale             trash_cans
**aggregate**        
**aggregate_ref**    **Q_037**
**type**             **numeric**
required             TRUE
sum_type             positive
**option_1**         **(>0)=1**
**option_2**         ***=0**
=================    =============================================

=================    ==========================================
variable             Q_037_r
=================    ==========================================
desc                 Basureros Públicos en Acera - Lado derecho
alias                seg_acera_basureros_der
level                segment 
section              streetscape
scale                streetscape_positive
subscale             trash_cans
**aggregate**        
**aggregate_ref**    **Q_037**
**type**             **numeric**
required             TRUE
sum_type             positive
**option_1**         **(>0)=1**
**option_2**         ***=0**
=================    ==========================================

En el ejemplo con la propiedad ``aggregate = TRUE`` definimos la pregunta de agregación ``Q_037`` y mediante la propiedad ``aggregate_ref`` 
relacionamos las preguntas ``Q_037_l`` y ``Q_037_r``.

Interpretamos el resultado de la suma de puntajes de las preguntas hijas mediante evlauación tipo "Numeric", 
es decir,  si en el segmento de calle hay al menos un elemento "Basurero público en acera" el segmento de calle obtiene 
un puntaje de ``1`` caso contrario ``0``.

*NOTA: Para casos que se requiera, se pueden anidar las agregaciones en varios niveles* 


.. toctree::
   :caption: Contenido
   :glob:
