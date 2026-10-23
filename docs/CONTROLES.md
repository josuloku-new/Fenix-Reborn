# Configuración · v0.1

**By JoSuLoku @2026**

Abre Configurar Fenix Reborn.exe para acceder directamente a Controles, Imagen y Mods. El selector de idioma aparece sobre los ajustes y solo ofrece idiomas presentes en la ISO. Guardar y salir conserva los cambios; Guardar y ejecutar los guarda e inicia el juego. La ejecución se habilita cuando la compilación termina correctamente. El configurador puede abrirse de nuevo en cualquier momento.

Imagen incluye perfiles gráficos, resolución de vídeo (480p, 540p, 720p,
900p, **1080p**, 1440p y 4K), escala de renderizado 1×–6×, VSync,
suavizado FXAA, filtrado anisotrópico y contador de FPS. «Usar ajustes de
rendimiento» recupera 720p y escala 1×. Los perfiles conservan controles,
idioma, mods y la elección de mostrar FPS. El juego mantiene la pantalla
completa; el modo de vídeo que se comunica al juego y su resolución interna
pueden ser distintos. La escala aumenta los render targets que genera el
juego. Los ajustes anteriores conservan su escala y modo base 720p.

El perfil **8K experimental** solicita una escala 6× sobre la base 1280×720:
7680×4320 de supermuestreo en los render targets que sigan esa base. Tiene
una carga elevada y la escala efectiva depende de la GPU y del motor. El modo
de vídeo que recibe el juego se conserva en 720p: sus dimensiones están
limitadas a 4095 píxeles por eje; introducir 7680×4320 ahí no produciría 8K.

La frecuencia comunicada al juego se puede elegir entre 30 y **240 Hz**.
Se conserva al cambiar de perfil gráfico. Es independiente de los FPS reales
y del refresco físico del monitor, que se configura en Windows. El parche
de FPS sigue siendo experimental y está orientado a 60 FPS; seleccionar
240 Hz no convierte ese parche en soporte garantizado de 240 FPS.

WASD para moverse y navegar; ratón para cámara; clic derecho para apuntar; clic izquierdo para disparar. Espacio acepta, corre y usa cobertura; V o Retroceso vuelve o ataca cuerpo a cuerpo; E interactúa; Q muestra interés; R recarga; Tab muestra objetivos; Enter pausa.

F1 libera/captura el ratón. F4 abre los ajustes de ReXGlue adaptados al idioma seleccionado y permite activar Mostrar contador de FPS. Guardar configuración conserva esa casilla. Los identificadores avanzados conservan sus nombres técnicos. El contador mide presentaciones VdSwap, no los Hz del monitor.

En Controles puedes ajustar **Sensibilidad cámara** y **Sensibilidad mira**
por separado. La segunda se utiliza al mantener la acción Apuntar (clic derecho
por defecto), también si reasignas esa acción a otra tecla. Valores iniciales:
cámara 1, mira 0,65 y suavizado desactivado.
La casilla **Suavizado (ms)** permite activarlo o desactivarlo. Al marcarla se
habilita su intensidad; al desmarcarla el juego recibe 0 ms y el configurador
recuerda el valor elegido para la próxima vez. La intensidad inicial al
activarlo es 2 ms. Los ajustes anteriores conservan su estado: 0 ms pasa a
desactivado y un valor mayor que 0 permanece activado.
**Ratón directo a la cámara** está activado por defecto: el desplazamiento se
consume una vez en el tick de entrada del juego y modifica la rotación del
controlador del jugador. No pasa por el stick, su zona muerta ni el promedio
del hilo de mandos. Con cámara 1, 2048 unidades de movimiento relativo producen
180° de giro; el recorrido físico depende de los DPI del ratón. Se conservan
las fracciones, el giro horizontal no tiene un límite de velocidad de stick y
el giro vertical respeta los límites de cámara del juego. El suavizado 0 evita
añadir movimiento después de detener el ratón.

Desmarca Ratón directo a la cámara para volver al stick emulado, como opción
de compatibilidad en escenas o controles especiales. La zona muerta solo se
utiliza en ese modo. El modo mando conserva su recorrido original.
Gracias a marinesciencedude y Clippy95 por la referencia Mousehook; la cadena
del jugador se resuelve de nuevo en cada tick, sin una dirección fija de heap.

Los ajustes iniciales se guardan en .local/settings.json y los de F4 en .local/runtime/bin/gow2.toml. Los datos y guardados permanecen fuera de Git.
