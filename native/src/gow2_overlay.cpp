#include "gow2_overlay.h"
#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/logging.h>
#include <rex/system/function_dispatcher.h>
#include <imgui.h>
#include <Windows.h>
#include <atomic>
#include <chrono>
#include <cstring>
#include <vector>

REXCVAR_DEFINE_BOOL(gow2_show_fps, false, "Display", "Show FPS counter")
    .lifecycle(rex::cvar::Lifecycle::kHotReload);

namespace {
struct Translation { const char* key; const char* en; const char* es; const char* it; const char* ko; const char* zh; };
// UTF-8. Technical CVAR identifiers remain stable for logs and searches.
const Translation translations[] = {
 {"Settings", "Settings", "Configuración", "Impostazioni", "설정", "設定"},
 {"Thanks to %s", "Thanks to %s", "Gracias a %s", "Grazie a %s", "%s 님께 감사드립니다", "感謝 %s"},
 {"Show FPS counter", "Show FPS counter", "Mostrar contador de FPS", "Mostra contatore FPS", "FPS 표시", "顯示 FPS 計數器"},
 {"FPS help", "Game frame submissions per second (not monitor refresh rate).", "Fotogramas enviados por el juego por segundo (no los Hz del monitor).", "Fotogrammi inviati dal gioco al secondo (non gli Hz del monitor).", "게임이 초당 제출하는 프레임 수입니다 (모니터 주사율 아님).", "遊戲每秒提交的影格數（不是螢幕更新率）。"},
 {"Search", "Search", "Buscar", "Cerca", "검색", "搜尋"},
 {"Save to config", "Save to config", "Guardar configuración", "Salva configurazione", "설정 저장", "儲存設定"},
 {"Saved", "Saved", "Guardado", "Salvato", "저장됨", "已儲存"},
 {"Press any key...##v", "Press any key...##v", "Pulsa una tecla...##v", "Premi un tasto...##v", "키를 누르세요...##v", "請按任意鍵...##v"},
 {"Rebind##v", "Rebind##v", "Cambiar##v", "Cambia##v", "변경##v", "變更##v"},
 {"Reset##v", "Reset##v", "Restablecer##v", "Ripristina##v", "초기화##v", "重設##v"},
 {"Key '%s' is also bound to %d other action(s)", "Key '%s' is also bound to %d other action(s)", "La tecla '%s' también está asignada a otras %d acciones", "Il tasto '%s' è assegnato ad altre %d azioni", "'%s' 키가 다른 동작 %d개에도 지정되어 있습니다", "按鍵 '%s' 也指定給其他 %d 個動作"},
 {"Live - changes apply immediately", "Live - changes apply immediately", "Los cambios se aplican al instante", "Le modifiche si applicano subito", "변경 사항이 즉시 적용됩니다", "變更立即生效"},
 {"Requires restart to take effect", "Requires restart to take effect", "Requiere reiniciar el juego", "Richiede il riavvio del gioco", "게임을 다시 시작해야 합니다", "需要重新啟動遊戲"},
 {"Read-only - set at initialization only", "Read-only - set at initialization only", "Solo lectura: se configura antes de iniciar el juego", "Sola lettura: configurare prima di avviare il gioco", "읽기 전용: 게임 시작 전에 설정하세요", "唯讀：請在啟動遊戲前設定"},
 {"Close with F4", "Close with F4", "Cerrar con F4", "Chiudi con F4", "F4로 닫기", "按 F4 關閉"},
 {"Input", "Input", "Entrada", "Input", "입력", "輸入"},
 {"Keybinds", "Key bindings", "Asignación de teclas", "Assegnazione tasti", "키 지정", "按鍵配置"},
 {"Controller", "Controller", "Mando", "Controller", "컨트롤러", "控制器"},
 {"System", "System", "Sistema", "Sistema", "시스템", "系統"},
 {"Display", "Display", "Pantalla", "Schermo", "화면", "顯示"},
 {"GPU", "GPU", "GPU", "GPU", "GPU", "GPU"},
 {"Audio", "Audio", "Audio", "Audio", "오디오", "音訊"},
 {"Mods", "Mods", "Mods", "Mod", "모드", "模組"},
 {"Memory", "Memory", "Memoria", "Memoria", "메모리", "記憶體"},
 {"CPU", "CPU", "CPU", "CPU", "CPU", "CPU"},
 {"Runtime", "Runtime", "Ejecución", "Esecuzione", "런타임", "執行階段"},
 {"Logging", "Logging", "Registros", "Registri", "로그", "記錄"},
 {"Kernel", "Kernel", "Núcleo", "Kernel", "커널", "核心"},
 {"General", "General", "General", "Generale", "일반", "一般"},
 {"Paths", "Paths", "Rutas", "Percorsi", "경로", "路徑"},
 {"Video", "Video", "Vídeo", "Video", "비디오", "影片"},
 {"Graphics", "Graphics", "Gráficos", "Grafica", "그래픽", "圖形"},
 {"Debug", "Debug", "Depuración", "Debug", "디버그", "除錯"},
 {"Achievements", "Achievements", "Logros", "Obiettivi", "도전 과제", "成就"},
 {"Profiler", "Profiler", "Rendimiento", "Prestazioni", "성능", "效能"},
 {"UI", "Interface", "Interfaz", "Interfaccia", "인터페이스", "介面"},
 {"HID", "Input devices", "Dispositivos de entrada", "Dispositivi di input", "입력 장치", "輸入裝置"},
 {"XConfig", "Console settings", "Configuración de consola", "Impostazioni console", "콘솔 설정", "主機設定"},
 {"Clock", "Clock", "Reloj", "Orologio", "시계", "時脈"},
 {"Console", "Console", "Consola", "Console", "콘솔", "主控台"},
 {"Filesystem", "File system", "Archivos", "File", "파일 시스템", "檔案系統"},
 {"Log", "Logs", "Registros", "Registri", "로그", "記錄"},
 {"Perf", "Performance", "Rendimiento", "Prestazioni", "성능", "效能"},
 {"Presenter", "Presentation", "Presentación", "Presentazione", "화면 출력", "畫面輸出"},
 {"Window", "Window", "Ventana", "Finestra", "창", "視窗"},
 {"crt", "C runtime", "Biblioteca C", "Libreria C", "C 런타임", "C 執行階段"},
 {"mnk_mode", "Keyboard and mouse", "Teclado y ratón", "Tastiera e mouse", "키보드 및 마우스", "鍵盤與滑鼠"},
 {"mnk_mouse", "Mouse camera", "Cámara con ratón", "Telecamera con mouse", "마우스 카메라", "滑鼠控制鏡頭"},
 {"mnk_sensitivity", "Mouse sensitivity", "Sensibilidad del ratón", "Sensibilità del mouse", "마우스 감도", "滑鼠靈敏度"},
 {"gow2_mouse_aim_sensitivity", "Aim sensitivity", "Sensibilidad al apuntar", "Sensibilità della mira", "조준 감도", "瞄準靈敏度"},
 {"gow2_mouse_direct", "Direct mouse camera", "Ratón directo a la cámara", "Mouse diretto alla telecamera", "직접 마우스 카메라", "直接滑鼠鏡頭"},
 {"gow2_mouse_smoothing_ms", "Mouse smoothing (ms)", "Suavizado del ratón (ms)", "Smoothing del mouse (ms)", "마우스 보정 (ms)", "滑鼠平滑處理 (ms)"},
 {"gow2_mouse_deadzone", "Deadzone compensation", "Compensación de zona muerta", "Compensazione zona morta", "데드존 보정", "死區補償"},
 {"gow2_show_fps", "Show FPS counter", "Mostrar contador de FPS", "Mostra contatore FPS", "FPS 표시", "顯示 FPS 計數器"},
 {"gow2_mod_unlock_fps", "Unlock FPS (experimental)", "Desbloquear FPS (experimental)", "Sblocca FPS (sperimentale)", "FPS 제한 해제 (실험적)", "解除 FPS 限制（實驗性）"},
 {"gow2_mod_lighting", "Lighting correction", "Corrección de iluminación", "Correzione illuminazione", "조명 수정", "修正光照"},
 {"gow2_mod_no_ao", "Disable ambient occlusion", "Desactivar oclusión ambiental", "Disattiva occlusione ambientale", "앰비언트 오클루전 끄기", "停用環境光遮蔽"},
 {"gow2_mod_no_motion_blur", "Disable motion blur", "Desactivar desenfoque de movimiento", "Disattiva motion blur", "모션 블러 끄기", "停用動態模糊"},
 {"gow2_mod_no_lens_flares", "Disable lens flares", "Desactivar destellos de lentes", "Disattiva lens flare", "렌즈 플레어 끄기", "停用鏡頭光暈"},
 {"gow2_mod_texture_streaming", "Texture streaming improvement", "Mejora de carga de texturas", "Migliora caricamento texture", "텍스처 로딩 개선", "改善材質載入"},
 {"gow2_mod_no_dof_blur", "Reduce depth-of-field blur", "Reducir desenfoque de profundidad", "Riduci la sfocatura di profondità", "피사계 심도 흐림 감소", "減少景深模糊"},
 {"gow2_mod_no_bloom", "Disable bloom", "Desactivar bloom", "Disattiva bloom", "블룸 끄기", "停用泛光"},
 {"fullscreen", "Full screen", "Pantalla completa", "Schermo intero", "전체 화면", "全螢幕"},
 {"vsync", "Vertical sync", "Sincronización vertical", "Sincronizzazione verticale", "수직 동기화", "垂直同步"},
 {"user_language", "Game language", "Idioma del juego", "Lingua del gioco", "게임 언어", "遊戲語言"},
 {"user_country", "Console region", "Región de consola", "Regione console", "콘솔 지역", "主機地區"},
 {"draw_resolution_scale_x", "Horizontal render scale", "Escala horizontal de renderizado", "Scala rendering orizzontale", "가로 렌더링 배율", "水平算圖比例"},
 {"draw_resolution_scale_y", "Vertical render scale", "Escala vertical de renderizado", "Scala rendering verticale", "세로 렌더링 배율", "垂直算圖比例"},
 {"window_width", "Window width", "Ancho de ventana", "Larghezza finestra", "창 너비", "視窗寬度"},
 {"window_height", "Window height", "Alto de ventana", "Altezza finestra", "창 높이", "視窗高度"},
 {"video_mode_refresh_rate", "Refresh rate", "Frecuencia de actualización", "Frequenza aggiornamento", "주사율", "更新率"},
 {"bind_debug_overlay", "Debug overlay", "Panel de depuración", "Pannello debug", "디버그 패널", "除錯面板"},
 {"bind_console", "Console", "Consola", "Console", "콘솔", "主控台"},
 {"gow2_bind_settings", "Settings menu", "Menú de configuración", "Menu impostazioni", "설정 메뉴", "設定選單"},
 {"bind_achievements", "Achievements", "Logros", "Obiettivi", "도전 과제", "成就"},
 {"gow2_bind_mouse_capture", "Capture / release mouse", "Capturar / liberar ratón", "Cattura / rilascia mouse", "마우스 캡처 / 해제", "擷取／釋放滑鼠"},
 {"keybind_lstick_up", "Move forward", "Mover adelante", "Avanti", "앞으로", "向前移動"},
 {"keybind_lstick_down", "Move backward", "Mover atrás", "Indietro", "뒤로", "向後移動"},
 {"keybind_lstick_left", "Move left", "Mover a la izquierda", "Sinistra", "왼쪽으로", "向左移動"},
 {"keybind_lstick_right", "Move right", "Mover a la derecha", "Destra", "오른쪽으로", "向右移動"},
 {"keybind_a", "A: cover / run / confirm", "A: cobertura / correr / aceptar", "A: copertura / corsa / conferma", "A: 엄폐 / 달리기 / 확인", "A：掩護／奔跑／確認"},
 {"keybind_b", "B: melee / back", "B: cuerpo a cuerpo / volver", "B: corpo a corpo / indietro", "B: 근접 공격 / 뒤로", "B：近戰／返回"},
 {"keybind_x", "X: interact", "X: interactuar", "X: interagisci", "X: 상호 작용", "X：互動"},
 {"keybind_y", "Y: point of interest", "Y: punto de interés", "Y: punto di interesse", "Y: 관심 지점", "Y：關注目標"},
 {"keybind_left_trigger", "LT: aim", "LT: apuntar", "LT: mira", "LT: 조준", "LT：瞄準"},
 {"keybind_right_trigger", "RT: fire", "RT: disparar", "RT: spara", "RT: 발사", "RT：射擊"},
 {"keybind_left_shoulder", "LB: objectives", "LB: objetivos", "LB: obiettivi", "LB: 목표", "LB：目標"},
 {"keybind_right_shoulder", "RB: reload", "RB: recargar", "RB: ricarica", "RB: 재장전", "RB：裝填"},
 {"keybind_start", "Start: pause", "Start: pausa", "Start: pausa", "Start: 일시 정지", "Start：暫停"},
 {"keybind_back", "Back", "Back: volver", "Back: indietro", "Back: 뒤로", "Back：返回"},
 {"keybind_lstick_press", "Press left stick", "Pulsar stick izquierdo", "Premi stick sinistro", "왼쪽 스틱 누르기", "按下左搖桿"},
 {"keybind_rstick_press", "Press right stick", "Pulsar stick derecho", "Premi stick destro", "오른쪽 스틱 누르기", "按下右搖桿"},
 {"keybind_dpad_up", "D-pad up", "Cruceta arriba", "Croce su", "방향 패드 위", "方向鍵上"},
 {"keybind_dpad_down", "D-pad down", "Cruceta abajo", "Croce giù", "방향 패드 아래", "方向鍵下"},
 {"keybind_dpad_left", "D-pad left", "Cruceta izquierda", "Croce sinistra", "방향 패드 왼쪽", "方向鍵左"},
 {"keybind_dpad_right", "D-pad right", "Cruceta derecha", "Croce destra", "방향 패드 오른쪽", "方向鍵右"},
 {"keybind_rstick_up", "Camera up", "Cámara arriba", "Telecamera su", "카메라 위", "鏡頭向上"},
 {"keybind_rstick_down", "Camera down", "Cámara abajo", "Telecamera giù", "카메라 아래", "鏡頭向下"},
 {"keybind_rstick_left", "Camera left", "Cámara izquierda", "Telecamera sinistra", "카메라 왼쪽", "鏡頭向左"},
 {"keybind_rstick_right", "Camera right", "Cámara derecha", "Telecamera destra", "카메라 오른쪽", "鏡頭向右"},
};
std::atomic<uint64_t> submitted_frames{0};
}

namespace gow2 {
int OverlayLanguage() { return REXCVAR_QUERY(int32_t, user_language); }
const char* Tr(const char* key) {
  const int language = OverlayLanguage();
  for (const auto& row : translations) if (std::strcmp(row.key, key) == 0) {
    switch (language) {
      case 5: return row.es;
      case 6: return row.it;
      case 7: return row.ko;
      case 8: return row.zh;
      default: return row.en;
    }
  }
  return key;
}
const char* SettingLabel(const std::string& name) { return Tr(name.c_str()); }
const char* ModAuthors(const std::string& name) {
  if (name == "gow2_mod_unlock_fps" || name == "gow2_mod_lighting") return "illusion, boma";
  if (name == "gow2_mod_no_ao" || name == "gow2_mod_no_motion_blur") return "illusion";
  if (name == "gow2_mod_no_lens_flares" || name == "gow2_mod_texture_streaming" ||
      name == "gow2_mod_no_dof_blur" || name == "gow2_mod_no_bloom") return "boma";
  return nullptr;
}

void ConfigureOverlayFonts(ImFontAtlas* atlas) {
  // The old tiny bitmap font has incomplete accented glyphs. Use Windows fonts
  // and bake only the selected UI's characters, keeping the atlas small.
  atlas->Clear();
  static ImVector<ImWchar> ranges;
  ranges.clear();
  ImFontGlyphRangesBuilder builder;
  builder.AddRanges(atlas->GetGlyphRangesDefault());
  for (const auto& row : translations) builder.AddText(Tr(row.key));
  builder.BuildRanges(&ranges);
  wchar_t windows_dir[MAX_PATH] = {};
  GetWindowsDirectoryW(windows_dir, MAX_PATH);
  const auto font_dir = std::filesystem::path(windows_dir) / L"Fonts";
  const int language = OverlayLanguage();
  auto file = font_dir / (language == 7 ? L"malgun.ttf" : language == 8 ? L"msjh.ttc" : L"segoeui.ttf");
  auto* font = atlas->AddFontFromFileTTF(file.string().c_str(), 16.0f, nullptr, ranges.Data);
  if (!font) {
    REXLOG_WARN("GoW2 overlay font missing: {}", file.string());
    font = atlas->AddFontDefault();
  }
  ImGui::GetIO().FontDefault = font;
}

rex::ui::FrameStats ReadFrameStats() {
  // Read only on the UI thread. The guest hook only increments an atomic.
  using Clock = std::chrono::steady_clock;
  static auto start = Clock::now();
  static uint64_t previous = 0;
  static rex::ui::FrameStats stats;
  const auto now = Clock::now();
  const double seconds = std::chrono::duration<double>(now - start).count();
  if (seconds >= 0.5) {
    const uint64_t count = submitted_frames.load(std::memory_order_relaxed);
    stats.fps = (count - previous) / seconds;
    stats.frame_time_ms = stats.fps > 0 ? 1000.0 / stats.fps : 0;
    stats.frame_count = count;
    static bool logged_first_sample = false;
    if (count > previous && !logged_first_sample) {
      REXLOG_INFO("GoW2 FPS counter: first guest sample {:.1f} FPS, {} submitted frames", stats.fps, count);
      logged_first_sample = true;
    }
    previous = count;
    start = now;
  }
  return stats;
}

void FpsDialog::OnDraw(ImGuiIO&) {
  const auto stats = ReadFrameStats();
  if (!REXCVAR_GET(gow2_show_fps)) return;
  ImGui::SetNextWindowPos(ImVec2(12, 12), ImGuiCond_Always);
  ImGui::SetNextWindowBgAlpha(0.65f);
  if (ImGui::Begin("##gow2_fps", nullptr,
      ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoInputs | ImGuiWindowFlags_NoNav |
      ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::Text("%.1f FPS", stats.fps);
  }
  ImGui::End();
}
}

// Count guest swaps, not ImGui redraws or the desktop refresh rate. Preserve
// every original SDK argument and register, just like the input import guards.
extern "C" REX_FUNC(__imp__VdSwap) {
  static PPCFunc* original = reinterpret_cast<PPCFunc*>(
      GetProcAddress(GetModuleHandleW(L"rexruntime.dll"), "__imp__VdSwap"));
  if (!original) REX_FATAL("Missing SDK VdSwap export");
  original(ctx, base);
  submitted_frames.fetch_add(1, std::memory_order_relaxed);
}
void gow2::InstallFrameCounter(rex::runtime::FunctionDispatcher* dispatcher) {
  if (!dispatcher->SetFunction(0x82F4DA1C, __imp__VdSwap))
    REX_FATAL("Unable to install GoW2 frame counter");
  REXLOG_INFO("GoW2 overlay: language={}, guest VdSwap FPS counter installed", OverlayLanguage());
}
