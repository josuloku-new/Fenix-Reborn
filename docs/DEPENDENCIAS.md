# Dependencias de la versión 0.1

Cada herramienta tiene una función en la preparación desde una ISO. Esto no
significa que cada archivo de sus paquetes oficiales sea necesario. La selección
es para Windows x64 y compilación Release; no prepara un entorno de desarrollo Debug.

| Componente | Función |
|---|---|
| extract-xiso | Extraer la ISO seleccionada. |
| ReXGlue | Analizar el ejecutable, generar código y ejecutar el juego. |
| Clang, LLD, llvm-lib, llvm-rc, llvm-mt | Compilar, crear bibliotecas, enlazar y preparar recursos de Windows. |
| CMake y Ninja | Configurar y ejecutar la compilación. |
| Python portable | Ejecutar los pasos de preparación y los ajustes del código generado. El Python del EXE ejecuta la interfaz; este intérprete separado permite ejecutar scripts desde CMake. |
| Cabeceras y bibliotecas Microsoft | Compilar C++ y resolver las llamadas a Windows. No contiene compilador Microsoft ni IDE. |
| DLL de C++ para x64 | Cargar las herramientas y el juego sin una instalación global del redistribuible. |
| 7zr y 7-Zip | Abrir el paquete de LLVM y los CAB del SDK. 7zr solo prepara el extractor. |
| Tcl/Tk | Ventanas nativas de la aplicación, incluido dentro del EXE. No se descarga como dependencia durante la preparación. |
| Código fuente fijado de ReXGlue | Reconstruir el complemento D3D12 con el cargador nativo de texturas. |
| UE Viewer, SRMD ncnn y DirectXTex | Solo al preparar el pack HD opcional: extraer texturas, ampliar por IA y crear DDS comprimidos. Se descargan versiones verificadas por SHA-256. |

## Recortes verificados

- Windows SDK: se leen ocho MSI verificados para identificar los CAB necesarios;
  se descargan esos CAB y se extraen cabeceras comunes y las bibliotecas usadas
  por el enlace. Quedan fuera los paquetes de verificadores, certificación,
  herramientas ARM, IntelliSense, muestras y el instalador del SDK. Un CAB puede
  agrupar archivos adicionales que no se extraen.
- C++: se conserva el runtime Release DLL x64 y sus bibliotecas de importación.
  Se eliminan las bibliotecas estáticas, los símbolos y las variantes Debug.
- LLVM: se conserva clang-cl y las herramientas de enlace y recursos. Se elimina
  la copia duplicada clang.exe, los sanitizadores y las herramientas de pruebas.
- ReXGlue: se conserva Release y sus archivos CMake; se eliminan Debug y
  RelWithDebInfo. Se preservan las licencias y los archivos referenciados por
  los targets CMake del paquete.
- CMake: se conservan cmake.exe, cmcldeps.exe, módulos, plantillas y avisos.
  Se eliminan la interfaz gráfica, CPack, CTest y los manuales.

Con el manifiesto Microsoft 18.10.3 utilizado en la comprobación, la descarga del
Windows SDK pasa de **511,6 MiB a 78,1 MiB**, con **21 archivos en lugar de 229**.
La selección depende de los archivos del manifiesto; no es una estimación de
todas las descargas del asistente.

Las herramientas preparadas pasan aproximadamente de **1,94 GiB a 0,59 GiB** en
la copia de prueba. Estas cifras excluyen ISO, datos del juego, compilaciones y
caché de descargas. No se borran descargas previas automáticamente.

La selección se comprobó configurando y compilando el test nativo de F4 y
enlazando el juego completo con sus 234 objetos ya compilados. El analizador
ReXGlue se prueba también desde la carpeta reducida. Esto no sustituye una
reconstrucción completa y una prueba de campaña en cada equipo.

## Límites del empaquetado

LLVM, CMake y ReXGlue se descargan desde sus paquetes oficiales completos.
Aunque contienen archivos que después se descartan, el servidor no ofrece
necesariamente cada componente por separado. La reducción de espacio preparado
no equivale a una reducción idéntica de tráfico de red.

La política reproducible está en launcher/packages.py y
launcher/third_party/sdk_files.py. La migración de herramientas existentes se
ejecuta al pulsar **Preparar herramientas** y solo afecta a sus carpetas locales;
conserva licencias y los archivos seleccionados.
