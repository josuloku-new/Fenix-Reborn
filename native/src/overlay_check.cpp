// Exercise the actual F4 widgets and rasterize ImGui draw data without a GPU
// or a running campaign. No user preferences or saves are touched.
#include "gow2_overlay.h"
#include "gow2_mods.h"
#include <rex/cvar.h>
#include <rex/ui/imgui_drawer.h>
#include <rex/ui/window.h>
#include <imgui.h>
#include <imgui_internal.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

class CheckContext : public rex::ui::WindowedAppContext {
  void NotifyUILoopOfPendingFunctions() override {}
  void PlatformQuitFromUIThread() override {}
};
void Require(bool ok, const char* message) {
  if (!ok) throw std::runtime_error(message);
}
void SaveRaster(const std::filesystem::path& path, ImDrawData* draw,
                const unsigned char* atlas, int aw, int ah) {
  constexpr int w=960, h=720;
  std::vector<uint32_t> pixels(w*h, 0xFF20242B);
  for (auto* list : draw->CmdLists) for (const auto& cmd : list->CmdBuffer) {
    if (cmd.UserCallback) continue;
    for (unsigned n=0; n+2<cmd.ElemCount; n+=3) {
      const auto& a=list->VtxBuffer[list->IdxBuffer[cmd.IdxOffset+n]+cmd.VtxOffset];
      const auto& b=list->VtxBuffer[list->IdxBuffer[cmd.IdxOffset+n+1]+cmd.VtxOffset];
      const auto& c=list->VtxBuffer[list->IdxBuffer[cmd.IdxOffset+n+2]+cmd.VtxOffset];
      const float area=(b.pos.x-a.pos.x)*(c.pos.y-a.pos.y)-(b.pos.y-a.pos.y)*(c.pos.x-a.pos.x);
      if (std::abs(area)<0.00001f) continue;
      int left=std::max({0,int(std::floor(std::min({a.pos.x,b.pos.x,c.pos.x}))),int(cmd.ClipRect.x)});
      int right=std::min({w,int(std::ceil(std::max({a.pos.x,b.pos.x,c.pos.x}))),int(cmd.ClipRect.z)});
      int top=std::max({0,int(std::floor(std::min({a.pos.y,b.pos.y,c.pos.y}))),int(cmd.ClipRect.y)});
      int bottom=std::min({h,int(std::ceil(std::max({a.pos.y,b.pos.y,c.pos.y}))),int(cmd.ClipRect.w)});
      for(int y=top;y<bottom;y++) for(int x=left;x<right;x++) {
        const float px=x+0.5f, py=y+0.5f;
        const float u=((b.pos.x-px)*(c.pos.y-py)-(b.pos.y-py)*(c.pos.x-px))/area;
        const float v=((c.pos.x-px)*(a.pos.y-py)-(c.pos.y-py)*(a.pos.x-px))/area;
        const float t=1-u-v;
        if(u<0 || v<0 || t<0) continue;
        int tx=std::clamp(int((u*a.uv.x+v*b.uv.x+t*c.uv.x)*aw),0,aw-1);
        int ty=std::clamp(int((u*a.uv.y+v*b.uv.y+t*c.uv.y)*ah),0,ah-1);
        const auto* tex=atlas+4*(ty*aw+tx);
        float color[4];
        for(int ch=0;ch<4;ch++) color[ch]=(u*((a.col>>(ch*8))&255)+v*((b.col>>(ch*8))&255)+t*((c.col>>(ch*8))&255))*tex[ch]/255.0f;
        const float alpha=color[3]/255.0f;
        uint32_t out=0xFF000000, old=pixels[y*w+x];
        for(int ch=0;ch<3;ch++) {
          int shift=(2-ch)*8; // BMP uses BGR; ImGui uses RGB.
          out |= uint32_t(color[ch]*alpha+((old>>shift)&255)*(1-alpha))<<shift;
        }
        pixels[y*w+x]=out;
      }
    }
  }
  std::ofstream file(path,std::ios::binary);
  auto put=[&](uint32_t v,int bytes){ for(int i=0;i<bytes;i++) file.put(char(v>>(8*i))); };
  file.write("BM",2); put(54+w*h*4,4);put(0,4);put(54,4);
  put(40,4);put(w,4);put(uint32_t(-h),4);put(1,2);put(32,2);put(0,4);
  put(w*h*4,4);put(0,4);put(0,4);put(0,4);put(0,4);
  file.write(reinterpret_cast<const char*>(pixels.data()),pixels.size()*4);
}

int main(int argc,char** argv) {
  try {
    Require(!REXCVAR_GET(gow2_mod_no_dof_blur) && !REXCVAR_GET(gow2_mod_no_bloom),"New visual mods must default off");
    Require(std::string(gow2::ModAuthors("gow2_mod_no_dof_blur"))=="boma" &&
            std::string(gow2::ModAuthors("gow2_mod_no_bloom"))=="boma","Missing visual mod credits");
    const std::filesystem::path out=argc>1 ? argv[1] : ".";
    CheckContext context;
    auto window=rex::ui::Window::Create(context,"Overlay check",960,720);
    for(int language : {5,1,6,7,8}) {
      Require(rex::cvar::SetFlagByName("user_language",std::to_string(language)),"Cannot select language");
      rex::ui::ImGuiDrawer drawer(window.get(),64,gow2::ConfigureOverlayFonts);
      auto& io=drawer.GetIO();
      io.DisplaySize=ImVec2(960,720);io.DeltaTime=1.0f/60;
      unsigned char* atlas=nullptr;int aw=0,ah=0;
      io.Fonts->GetTexDataAsRGBA32(&atlas,&aw,&ah);
      io.Fonts->SetTexID(ImTextureID(1));
      auto* font=io.FontDefault->GetFontBaked(16.0f);
      Require(font && font->FindGlyphNoFallback(0x00F1) && font->FindGlyphNoFallback(0x00E9),"Missing accented glyphs");
      const char* p=gow2::Tr("Show FPS counter");
      while(*p) {unsigned code=0;int len=ImTextCharFromUtf8(&code,p,nullptr);Require(len>0,"Invalid UTF-8");p+=len;Require(font->FindGlyphNoFallback(code)!=nullptr,"Missing translated glyph");}
      gow2::FpsDialog fps(&drawer);
      {
        gow2::SettingsDialog settings(&drawer,out/"overlay_check.toml");
        auto frame=[&] {ImGui::NewFrame();fps.Draw();settings.Draw();ImGui::Render();};
        frame();frame();
        auto* f4=ImGui::FindWindowByName((std::string("Fenix Reborn · ")+gow2::Tr("Settings")+"###gow2_settings").c_str());
        Require(f4!=nullptr,"Settings window missing");
        rex::cvar::SetFlagByName("gow2_show_fps","false");
        // Click the actual checkbox at the start of the window's content.
        io.AddMousePosEvent(f4->Pos.x+15,f4->Pos.y+f4->TitleBarHeight+35);
        io.AddMouseButtonEvent(0,true);frame();io.AddMouseButtonEvent(0,false);frame();
        Require(REXCVAR_QUERY(bool,gow2_show_fps),"FPS checkbox did not enable counter");
        io.AddMousePosEvent(940,700);frame();
        SaveRaster(out/ ("f4_"+std::to_string(language)+".bmp"),ImGui::GetDrawData(),atlas,aw,ah);
        rex::cvar::SaveConfig(out/"overlay_check.toml");
        rex::cvar::SetFlagByName("gow2_show_fps","false");
        // A fresh process has default source priority. Inspect saved output
        // here; LoadConfig intentionally cannot override runtime-priority flags.
        std::ifstream saved(out/"overlay_check.toml");
        std::string text((std::istreambuf_iterator<char>(saved)),{});
        Require(text.find("gow2_show_fps = true")!=std::string::npos,"FPS option was not saved");
      }
      io.AddMousePosEvent(20,20);
      rex::cvar::SetFlagByName("gow2_show_fps","true");
      for(int i=0;i<3;i++) {ImGui::NewFrame();fps.Draw();ImGui::Render();}
      Require(!io.WantCaptureMouse && !io.WantCaptureKeyboard,"FPS HUD captures game input");
      std::cout<<"Language "<<language<<": glyphs, F4 checkbox, save and noninteractive FPS HUD OK\n";
    }
    std::filesystem::remove(out/"overlay_check.toml");
    return 0;
  } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
