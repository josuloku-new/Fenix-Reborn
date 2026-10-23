# Mods nativos compatibles · v0.1

**By JoSuLoku @2026**

El configurador ofrece mejoras integradas en la recompilación. Su aplicación
se realiza sobre el C++ generado localmente, con validación del SHA-256 del XEX
y de los puntos de código esperados. El pack HD usa el complemento gráfico
nativo y archivos DDS locales. La ISO no se modifica.

## Integrados

| Mejora | Aplicación nativa | Agradecimiento visible |
|---|---|---|
| Desbloquear FPS | Cambios del limitador y del intervalo de presentación del propio juego. Experimental; no garantiza 60 FPS sostenidos. | Gracias a illusion y boma |
| Corregir iluminación | Cambio de la configuración MSAA del juego para reducir errores de iluminación. | Gracias a illusion y boma |
| Desactivar oclusión ambiental | Cambio del parámetro de AO en el código recompilado. | Gracias a illusion |
| Desactivar desenfoque | Desactivación del motion blur del juego. | Gracias a illusion |
| Desactivar destellos | Desactivación de lens flares del juego. | Gracias a boma |
| Carga de texturas | Mayor presupuesto de texturas y ajuste del streaming. Consume más memoria. | Gracias a boma |
| Reducir desenfoque de profundidad | Adaptación de la variante A del parche gaussiano; conserva el resto del posprocesado. | Gracias a boma |
| Desactivar bloom | Desactivación del resplandor en los tres puntos de selección del juego. | Gracias a boma |
| Pack HD 2× | Reemplazo por contenido de texturas BC1 ampliadas localmente con SRMD. Catálogo inicial: personajes, armas, objetos y comienzo del hospital. | Gracias a Gildor, nihui / Kai Zhang, Microsoft / DirectXTex, ReXGlue y FaliGame (referencia) |

Iluminación y desactivación de AO están activadas por defecto. Las demás
casillas están desactivadas inicialmente. El desbloqueo de FPS conserva el
refresco y VSync elegidos en Imagen; los vídeos conservan sus fotogramas originales.
Los agradecimientos aparecen junto a cada casilla de Configuración → Mods.

La [referencia de estos cambios y sus autores](https://github.com/xenia-canary/game-patches/blob/main/patches/4D53082D%20-%20Gears%20of%20War%202.patch.toml)
procede del catálogo de parches de Xenia. Aquí se han traducido a cambios de
C++: no se instala ni se ejecuta Xenia y no se carga su motor de parches TOML.
El ratón directo y el contador de FPS también están integrados en el ejecutable.
Los créditos de Mousehook reconocen la referencia utilizada para la cámara.

## Configuración y comprobación

Abre **Configurar Fenix Reborn.exe → Mods**, marca las mejoras deseadas y usa
**Guardar y ejecutar**. **Guardar y salir** las conserva para el siguiente
inicio. Los mods requieren reiniciar el juego. Las dos opciones visuales
nuevas están apagadas por defecto y se pueden seleccionar por separado. Se
muestran como experimentales: se ha comprobado su ejecución nativa, pero
la primera prueba en campaña no ha confirmado una diferencia visual perceptible.

La adaptación de profundidad de campo reproduce dos instrucciones fsubs
de la variante A; no aplica la variante que anula toda la cadena DoF. La de
bloom sustituye tres lecturas por el valor cero. Se mantienen las ramas
originales cuando las casillas están desactivadas.

tools/check_native_mods.py compila los cinco bloques C++ generados y compara
su comportamiento activado con los opcodes de referencia. También comprueba
las cuatro combinaciones de las dos casillas y que, al desactivarlas, se
conserven las lecturas, las llamadas y el registro LR originales. El resultado
visual depende de la escena y debe valorarse en partida. El registro de inicio
indica las casillas recibidas y registra una sola vez cada punto visual que
llega a ejecutarse; esto comprueba la aplicación del código, no una mejora
visible ni de rendimiento.

## Multijugador

No hay un mod multijugador validado para esta recompilación. Su incorporación
requiere desarrollar y probar funciones del propio runtime y del juego. Las
soluciones que precisan ejecutar otro emulador quedan fuera del catálogo.

No se distribuyen mods de otras versiones del juego, imágenes de texturas, doblajes ni DLC.

El [pack HD](TEXTURAS_HD.md) se prepara desde Configuración → Mods. El
cargador identifica los bloques BC1 originales, crea recursos de mayor
resolución y vuelve a la textura original si falta un archivo o resulta
incompatible. Los archivos del pack permanecen en `.local/mods/textures-hd/`.
