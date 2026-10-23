[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/josuloku)

# Fenix Reborn 0.1

Por JoSuLoku, 2026.

Fenix Reborn es un proyecto independiente que recompila Gears of War 2 (Xbox 360) para Windows x64. Usa ReXGlue y renderiza con DirectX 12. Incluye un asistente que prepara todo desde tu propia ISO, ajustes de imagen, teclado y ratón, mando, selector de idioma y algunos mods.

No lleva el juego dentro: ni ISO, ni XEX, ni ejecutable recompilado, ni texturas. El código del juego se genera en tu equipo a partir de tu copia. No tiene ninguna relación oficial con los titulares del juego.

No necesita Xenia ni ningún otro emulador.

## Requisitos

- Windows 10 u 11 de 64 bits y una GPU compatible con DirectX 12.
- Unos 30 GB libres (datos, herramientas y compilación).
- Una ISO de Gears of War 2 cuyo ejecutable retail tenga este SHA-256: `c110e168abd4518c510f8358723343e129aed17eea73fe12010b8a0cd0a73bb8`. Otras revisiones no están soportadas.

## Cómo se usa

Descarga `Fenix-Reborn-Setup-0.1.exe` desde la sección Releases y ábrelo con doble clic. Es una aplicación nativa de Windows con Python y Tcl/Tk incluidos, así que no necesitas instalar Python ni abrir un navegador. Puedes copiarlo a una carpeta vacía: todo lo que genere se guarda en `.local/`, junto al EXE.

El asistente tiene cuatro pasos:

1. Bienvenida.
2. Herramientas: aceptas sus condiciones y descarga Clang/LLD, CMake/Ninja, ReXGlue, el extractor de ISO y las cabeceras y bibliotecas de Windows y C++. No instala Visual Studio ni MSBuild.
3. Tu ISO: la seleccionas, se extrae y se verifica. La ISO original no se toca.
4. Preparar juego: genera el C++ y lo compila en tu equipo. La primera vez tarda varios minutos.

En ese último paso viene marcada la casilla **Liberar espacio al terminar**. Si la dejas, al acabar borra las descargas, las herramientas y la compilación temporal, y conserva la ISO, el juego preparado, los ajustes, las cachés y tus partidas. Desmárcala si quieres poder reconstruir más adelante sin volver a descargar. Los registros quedan en `.local/logs`.

Cuando termina bien se crean otros dos accesos junto al asistente (deben quedarse en esa carpeta):

- **Ejecutar Fenix Reborn.exe** arranca el juego con tus ajustes.
- **Configurar Fenix Reborn.exe** abre el configurador, con las opciones *Guardar y salir* y *Guardar y ejecutar*. Mientras se compila, *Guardar y ejecutar* está desactivado y se activa solo cuando el juego está listo.

Si algo se interrumpe, vuelve a abrir el asistente y retoma la preparación donde se quedó.

## Qué incluye

**Controles.** Teclado y ratón, mando y ratón directo a la cámara. En el juego, F1 libera el ratón y F4 abre los ajustes y el contador de FPS. Detalles en [docs/CONTROLES.md](docs/CONTROLES.md).

**Imagen.** Resoluciones hasta 1080p, escala de renderizado independiente, perfiles gráficos, VSync, FXAA, filtrado de texturas y contador de FPS. Hay un perfil experimental de 8K con supermuestreo 6x desde 720p. Puedes indicar al juego hasta 240 Hz, pero eso no garantiza 240 FPS ni cambia los Hz de tu monitor. Lo normal sigue siendo 720p, escala 1x y 60 Hz.

**Mods.** Mejoras que se aplican sobre el C++ generado, comprobando antes el SHA-256 del XEX y las instrucciones esperadas: desbloqueo de FPS, corrección de iluminación, desactivar oclusión ambiental, desenfoque, destellos o bloom, y mejoras de streaming. Están explicados en [docs/MODS.md](docs/MODS.md). El desbloqueo de FPS es experimental y no asegura 60 FPS estables.

**Pack HD 2x.** Opcional. Extrae las texturas de color de tu copia local, las amplía con SRMD y crea DDS con todos sus niveles de detalle. De momento cubre personajes, armas, objetos y la zona inicial del hospital, no toda la campaña. Para generarlo hace falta Vulkan en el controlador de la GPU; el juego sigue usando DirectX 12. Más información y límites en [docs/TEXTURAS_HD.md](docs/TEXTURAS_HD.md).

## Estado

La campaña funciona, pero el proyecto es experimental. La estabilidad, la fidelidad visual y que la reconstrucción funcione en otros equipos todavía no están garantizadas. Si te encuentras un fallo, cuéntalo en Issues con el registro de `.local/logs`.

## Para desarrolladores

```
python launcher/app.py                       # ejecutar el asistente desde las fuentes
python -m unittest discover -s tests -v      # pruebas (no necesitan una ISO)
python tools/check_repository.py             # auditoría de lo que se publica
python tools/build_launcher.py --work RUTA   # construir el EXE del asistente
```

Para construir el EXE necesitas PyInstaller en un entorno con Tcl/Tk y las herramientas portables ya preparadas. Si están en otro workspace, añade `--toolchain-workspace RUTA`. Los pasos de publicación están en [docs/RELEASE.md](docs/RELEASE.md).

Estructura del repositorio:

- `launcher/`: asistente y configurador en Python. `launcher/native/` tiene el código de los dos accesos y `launcher/third_party/` el descargador de bibliotecas de Microsoft.
- `native/`: integración en C++ y manifiestos. No contiene código generado del juego.
- `tools/`: auditoría y construcción del EXE.
- `tests/`: pruebas.
- `docs/` y `licenses/`: documentación y avisos de licencia.

`.local/` guarda lo privado y generado en cada instalación y no forma parte del repositorio. Tampoco se incluyen compilaciones, ISO, XEX, guardados ni binarios de terceros. El EXE del asistente se publica como archivo adjunto de cada release, no en el historial de Git.

## Legal y créditos

Las partes derivadas de otros proyectos mantienen sus avisos originales (BSD, MIT, ISC y otros); están en [licenses/](licenses/) y en [CREDITOS.md](CREDITOS.md). Los derechos del juego pertenecen a sus titulares y ninguna licencia de este proyecto da derechos sobre él. Lo que se distribuye y lo que no, en [docs/LEGAL.md](docs/LEGAL.md). Qué hace cada herramienta que se descarga, en [docs/DEPENDENCIAS.md](docs/DEPENDENCIAS.md).

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/josuloku)
