# Publicar las fuentes y el asistente

1. Ejecutar las pruebas y tools/check_repository.py. El icono propio se puede regenerar con python tools/build_icon.py, sin dependencias adicionales.
2. Construir Fenix-Reborn-Setup-0.1.exe con tools/build_launcher.py usando Python con Tcl/Tk, PyInstaller y la toolchain portable. --toolchain-workspace permite reutilizar herramientas de otro workspace. El paquete contiene la aplicación nativa Python/Tk, sus dos pequeños accesos EXE, fuentes de integración y avisos; no el ejecutable del juego ni código generado.
3. Publicar las fuentes en Git y adjuntar el EXE del asistente a una release. No añadir binarios al historial.
4. Probar el EXE en una carpeta vacía: preparar herramientas portables, seleccionar una ISO compatible y reconstruir localmente. Al terminar deben crearse Ejecutar Fenix Reborn.exe y Configurar Fenix Reborn.exe y cerrarse la preparación. El configurador ofrece Guardar y ejecutar y Guardar y salir. Comprobar el icono en ventanas y EXE y la casilla Liberar espacio al terminar, marcada por defecto: solo elimina archivos de preparación después de completar la compilación. Ninguno abre un navegador para mostrar su interfaz.

El EXE público contiene un arranque Win32 que prepara la aplicación en
.local/app/<huella> y establece la carpeta de trabajo y TEMP/TMP junto al EXE.
PyInstaller extrae sus archivos en .local/temp/app; los procesos externos usan
.local/temp/work. Cada apertura tiene recursos independientes. Probar desde
un directorio de trabajo distinto y con --handoff-self-test RUTA_JSON: el
informe debe confirmar independent_bundle, parent_bundle_removed y native_source.

Para reunir exactamente los archivos de publicación, ejecutar
**python tools/prepare_github.py** después de actualizar el EXE y el índice
de Git. Se crea **SUBIR A GITHUB** con:

- **REPOSITORIO/**: contenido que va en la raíz del repositorio, incluidos los archivos ocultos de configuración.
- **RELEASE/Fenix-Reborn-Setup-0.1.exe**: archivo que se adjunta a la release v0.1.
- **COMO_SUBIR.txt**: instrucciones de los dos destinos.

La copia del repositorio se audita completa y ejecuta sus pruebas sin necesitar
su propio directorio .git. La entrega queda excluida del repositorio original.

No publicar .local/, SDKs descargados, cabeceras/bibliotecas de Microsoft, ISO, XEX, compilaciones o guardados. El anterior gow2-runtime-0.1.zip fue retirado. No se ha creado un remoto ni publicado contenido desde esta sesión.
