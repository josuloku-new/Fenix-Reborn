# Gracias · v0.1

**By JoSuLoku @2026**

El modo Ratón directo a la cámara toma como referencia la disposición de la
cámara publicada por [Xenia Mousehook](https://github.com/Clippy95/xenia-canary-mousehook/blob/mousehook/src/xenia/hid/winkey/hookables/GearsOfWars.cc)
y la [cadena dinámica del jugador documentada por Clippy95](https://github.com/marinesciencedude/xenia-canary-mousehook/issues/35).
Gracias a **marinesciencedude y Clippy95**; estos créditos también aparecen en
Configuración → Controles. La integración nativa de entrada por fotograma y la
validación de punteros son de este proyecto. Aviso BSD en
licenses/Xenia-Mousehook-BSD.txt.

El icono del asistente, configurador y accesos es una ilustración propia de
engranaje y calavera, creada para el proyecto. Fuentes en launcher/assets/gow2.svg
y tools/build_icon.py; se distribuye bajo la licencia del proyecto.

Los agradecimientos se muestran dentro de Configuración → Mods, junto a cada casilla.

| Mejora | Agradecimiento visible |
|---|---|
| Desbloquear FPS | Gracias a illusion y boma |
| Corregir iluminación | Gracias a illusion y boma |
| Desactivar oclusión ambiental | Gracias a illusion |
| Desactivar desenfoque | Gracias a illusion |
| Desactivar destellos | Gracias a boma |
| Mejora de streaming | Gracias a boma |
| Reducir desenfoque de profundidad | Gracias a boma |
| Desactivar bloom | Gracias a boma |
| Pack HD 2× generado localmente | Gracias a Gildor, nihui / Kai Zhang (SRMD), Microsoft / DirectXTex, ReXGlue y FaliGame (referencia) |

Referencia: [parches originales de Xenia Canary](https://github.com/xenia-canary/game-patches/blob/main/patches/4D53082D%20-%20Gears%20of%20War%202.patch.toml).

Gracias a Tom Clay y al equipo de [ReXGlue](https://github.com/rexglue/rexglue-sdk), al proyecto [Xenia](https://github.com/xenia-project/xenia) y sus colaboradores. F4 es una adaptación de SettingsDialog de ReXGlue sobre Dear ImGui. El contador de FPS es propio, sobre VdSwap; no utiliza el parche Show FPS de Xenia.

Gracias a [XboxDev/extract-xiso](https://github.com/XboxDev/extract-xiso), [LLVM](https://github.com/llvm/llvm-project), [CMake](https://github.com/Kitware/CMake), [Ninja](https://github.com/ninja-build/ninja), Python, PyInstaller y 7-Zip. Sus componentes se descargan aparte y mantienen sus licencias.

Gracias a Martin Storsjö por [msvc-wine/vsdownload.py](https://github.com/mstorsjo/msvc-wine), utilizado para preparar cabeceras y bibliotecas de Windows sin instalar el IDE. Se conserva íntegro su aviso ISC en launcher/third_party/vsdownload.py. La base es el commit 514f8ea34842cd6d831804d0e9658d3a32870ae1; esta adaptación añade progreso de descarga y extracción de los archivos del SDK sin ejecutar sus instaladores, mediante sdk_files.py.

Gracias a los autores de Tcl/Tk por las ventanas nativas del asistente y el configurador. Se incluye su aviso en licenses/Tcl-Tk.txt. La interfaz no utiliza HTML ni un navegador.

El pack HD usa [UE Viewer de Gildor](https://github.com/gildor2/UEViewer) para
extraer imágenes de la copia local, [SRMD ncnn de nihui](https://github.com/nihui/srmd-ncnn-vulkan)
y el modelo [SRMD de Kai Zhang](https://github.com/cszn/SRMD) para ampliarlas,
y [DirectXTex de Microsoft](https://github.com/microsoft/DirectXTex) para crear
DDS BC1 con sus niveles de detalle. El diseño de reemplazos de
[Lost Odyssey HD Remaster de FaliGame](https://github.com/faligame/lost-odyssey-hd-remaster)
sirvió como referencia técnica; su aviso está en licenses/FaliGame-MIT.txt.
Los agradecimientos también figuran en la tarjeta del pack en Configuración → Mods.
Las texturas generadas pertenecen a la instalación privada y se excluyen del repositorio.

Avisos BSD de las partes adaptadas: licenses/ReXGlue-BSD-3-Clause.txt y native/src/LICENSE.rexglue. Los derechos del juego pertenecen a sus titulares; ninguna licencia del asistente otorga derechos sobre el juego.
