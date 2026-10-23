# Pack HD 2× · Fenix Reborn 0.1

**By JoSuLoku @2026 · 14 de octubre de 2026**

El configurador integra la generación local de un pack y un cargador de DDS
en el complemento nativo DirectX 12. Se amplían las imágenes de la copia del
usuario mediante SRMD; no se descarga un pack con arte del juego.

## Uso

1. Abre **Configurar Fenix Reborn.exe → Mods**.
2. Pulsa **Preparar pack HD (2×)**. La ventana muestra la textura actual y
   el progreso. Las descargas se verifican por SHA-256.
3. Al terminar se activa **Pack HD 2×**. Usa **Guardar y ejecutar**.
4. Desmarca la casilla para volver a los originales en el siguiente arranque.

**Eliminar los archivos de preparación al terminar** está marcada por
defecto. Conserva el pack y elimina las herramientas opcionales, sus descargas
y las imágenes intermedias. El juego, ajustes y partidas se conservan.
Toda la preparación se realiza dentro de `.local/`, junto a los EXE.

La instalación local usada en la implementación tiene **127 texturas** y
ocupa aproximadamente **221 MiB**. Incluye texturas de Marcus y Dom para
cinemáticas y gameplay, armas, objetos, fachadas, paredes, suelos y elementos
de la zona inicial del hospital. El catálogo usa `GearGame.xxx`,
`SP_Hospital_01.xxx`, `SP_Hospital_01_S.xxx` y `SP_Hospital_01_Backdrop.xxx`.
No cubre toda la campaña. Los vídeos prerenderizados conservan su imagen.

## Qué cambia

Las texturas de color BC1 opacas seleccionadas se amplían a 2× por eje,
con un máximo de 4096 × 4096. Se generan todos sus niveles de detalle y se
comprimen de nuevo en BC1. Se excluyen normales, máscaras, mapas especulares,
emisión, transparencias, agua y efectos identificables por su nombre.
SRMD amplía y restaura la imagen original; no equivale a texturas oficiales
redibujadas ni garantiza recuperar el detalle que nunca existió en la ISO.
El cargador aplica un ajuste de un nivel de detalle a los materiales que usan
el reemplazo 2×. Así, el muestreo automático puede usar los nuevos píxeles en
vez de seleccionar el nivel reducido, que se parece al original. Las texturas
sin reemplazo conservan el muestreo normal.

El cargador reconoce el contenido BC1 original después de corregir su
disposición en memoria y orden de bytes. Evita depender de direcciones que
cambian entre escenas o partidas. Si el juego reutiliza una textura para otro
contenido, se actualizan sus vistas. Las vistas anteriores y sus recursos
permanecen válidos para los comandos GPU ya enviados.

Los DDS inválidos, ausentes o que exceden el presupuesto conservan el
original. El límite de recursos de reemplazo más sus buffers de subida es
512 MiB por sesión. Los mapas originales y archivos de la ISO no se editan.
El pack necesita reiniciar el juego después de activarlo o desactivarlo.

## Validación y límites

La sustitución DDS a mayor resolución se comprobó visualmente con una imagen
sintética sobre personajes y escenarios. La implementación definitiva se ha
compilado y la identidad BC1 se ha contrastado con un DDS real de Marcus en
las ocho combinaciones de disposición lineal/tiled y orden de bytes. Los DDS
generados incluyen sus niveles de detalle completos. La diferencia visual y
el rendimiento del pack real dependen de la escena, distancia y resolución;
no se presenta como una remasterización completa.
En particular, a 720p y a cierta distancia puede seguir siendo difícil
percibir cambios: el reescalado parte del arte original y no inventa una
textura nueva. El registro del juego enumera cada reemplazo aplicado.

El juego usa ReXGlue y DirectX 12. La generación opcional usa Vulkan mediante
el controlador gráfico para ejecutar SRMD. No instala ni ejecuta Xenia.

## Créditos y publicación

Gracias a [Gildor / UE Viewer](https://github.com/gildor2/UEViewer),
[nihui / SRMD ncnn](https://github.com/nihui/srmd-ncnn-vulkan),
[Kai Zhang / SRMD](https://github.com/cszn/SRMD),
[Microsoft / DirectXTex](https://github.com/microsoft/DirectXTex),
[ReXGlue](https://github.com/rexglue/rexglue-sdk) y
[FaliGame](https://github.com/faligame/lost-odyssey-hd-remaster) por la
referencia de diseño. Estos agradecimientos aparecen en la tarjeta de Mods.

El repositorio contiene el generador, los enganches del complemento y sus
metadatos. `.local/mods/textures-hd/` contiene los DDS y `pack.json` de cada
instalación; está excluida de GitHub. Las herramientas se descargan de sus
proyectos originales, sin incluir sus binarios ni datos del juego en las fuentes.
