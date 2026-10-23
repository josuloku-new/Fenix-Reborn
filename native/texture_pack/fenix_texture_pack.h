// Fenix Reborn texture replacements. By JoSuLoku @2026.
// Native D3D12 resources; originals are identified by canonical BC1 content.
#pragma once
#include <algorithm>
#include <array>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <vector>
#include <rex/graphics/d3d12/command_processor.h>
#include <rex/graphics/pipeline/texture/util.h>
#include <rex/logging.h>
#include <rex/ui/d3d12/d3d12_util.h>

namespace rex::graphics::d3d12::fenix {
struct Image {
  Microsoft::WRL::ComPtr<ID3D12Resource> texture, upload;
  uint32_t mips = 0;
};

// Safe guest reads are checked before access. Hashing canonical blocks avoids
// addresses, tiling padding and byte order becoming part of a pack identity.
inline bool Readable(const uint8_t* data, size_t size) {
  auto end = data + size;
  while (data < end) {
    MEMORY_BASIC_INFORMATION region{};
    if (!VirtualQuery(data, &region, sizeof(region)) || region.State != MEM_COMMIT ||
        (region.Protect & (PAGE_GUARD | PAGE_NOACCESS)) ||
        (region.Protect & 0xff) == PAGE_EXECUTE) return false;
    auto next = static_cast<const uint8_t*>(region.BaseAddress) + region.RegionSize;
    if (next <= data) return false;
    data = next;
  }
  return true;
}
inline bool CopyGuest(uint8_t* destination, const uint8_t* source, size_t size) {
  __try { std::memcpy(destination, source, size); return true; }
  __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}
inline uint64_t HashBC1(uint32_t width, uint32_t height, bool tiled, uint32_t endian,
                       const texture_util::TextureGuestLayout& layout,
                       const uint8_t* source) {
  const uint32_t size = layout.base.level_data_extent_bytes;
  if (!source || !size || size > 8 * 1024 * 1024 || !Readable(source, size)) return 0;
  std::vector<uint8_t> bytes(size);
  if (!CopyGuest(bytes.data(), source, size)) return 0;
  const uint32_t columns = (width + 3) / 4, rows = (height + 3) / 4;
  const uint32_t pitch = std::max(layout.base.row_pitch_bytes / 8, columns);
  uint64_t hash = UINT64_C(14695981039346656037);
  for (uint32_t y = 0; y < rows; ++y) {
    for (uint32_t x = 0; x < columns; ++x) {
      const size_t offset = tiled ? size_t(texture_util::GetTiledOffset2D(x, y, pitch, 3))
                                  : (size_t(y) * pitch + x) * 8;
      if (offset + 8 > bytes.size()) return 0;
      uint8_t block[8];
      for (uint32_t b = 0; b < 8; ++b) {
        // Xenos Endian: none=0, 8in16=1, 8in32=2, 16in32=3.
        const uint32_t swap = endian == 1 ? 1 : endian == 2 ? 3 : endian == 3 ? 2 : 0;
        block[b] = bytes[offset + (b ^ swap)];
      }
      uint64_t word = 0;
      std::memcpy(&word, block, 8);
      hash = (hash ^ word) * UINT64_C(1099511628211);
    }
  }
  return hash;
}

class Pack {
 public:
  static Pack& Get() { static Pack instance; return instance; }
  bool enabled() const { return !root_.empty(); }
  Image* Find(uint64_t hash, uint32_t width, uint32_t height,
              D3D12CommandProcessor& processor) {
    if (!hash || !enabled()) return nullptr;
    char name[96];
    snprintf(name, sizeof(name), "%016llx_%ux%u.dds",
             static_cast<unsigned long long>(hash), width, height);
    const std::string key(name);
    auto found = images_.find(key);
    if (found != images_.end()) return found->second.get();
    if (!files_.contains(key)) return nullptr;
    // A failed file is attempted once and leaves the original visible.
    auto [slot, inserted] = images_.emplace(key, nullptr);
    slot->second = Load(root_ / key, processor);
    if (slot->second) REXGPU_INFO("Fenix HD: replaced {}", key);
    else REXGPU_WARN("Fenix HD: using original for {}", key);
    return slot->second.get();
  }
 private:
  Pack() {
    const wchar_t* path = _wgetenv(L"FENIX_TEXTURE_PACK");
    if (!path || !*path) return;
    std::filesystem::path requested(path);
    if (!requested.is_absolute()) return;
    std::error_code error;
    if (!std::filesystem::is_directory(requested, error)) return;
    root_ = requested;
    for (auto entry = std::filesystem::directory_iterator(root_, error);
         !error && entry != std::filesystem::directory_iterator(); entry.increment(error)) {
      if (entry->is_regular_file(error) && entry->path().extension() == L".dds")
        files_.insert(entry->path().filename().string());
    }
    REXGPU_INFO("Fenix HD: {} replacements indexed", files_.size());
  }
  std::unique_ptr<Image> Load(const std::filesystem::path& path,
                            D3D12CommandProcessor& processor) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) return nullptr;
    const auto length = stream.tellg();
    if (length < 128 || length > 16 * 1024 * 1024) return nullptr;
    std::vector<uint8_t> bytes(static_cast<size_t>(length));
    stream.seekg(0);
    if (!stream.read(reinterpret_cast<char*>(bytes.data()), length)) return nullptr;
    auto read32 = [&](size_t offset) { uint32_t v; std::memcpy(&v, bytes.data()+offset,4); return v; };
    if (read32(0)!=0x20534444 || read32(4)!=124 || read32(76)!=32 || read32(84)!=0x31545844)
      return nullptr;
    const uint32_t height=read32(12), width=read32(16), mips=read32(28);
    if (!width || !height || width>4096 || height>4096 || !mips || mips>13 ||
        (read32(112) & 0x0020FE00)) return nullptr;  // No cube/volume DDS.
    uint32_t complete=1;
    for (uint32_t edge=std::max(width,height); edge>1; edge>>=1) ++complete;
    if (mips!=complete) return nullptr;
    size_t payload=0;
    for(uint32_t level=0;level<mips;++level)
      payload+=size_t((std::max(width>>level,1u)+3)/4)*((std::max(height>>level,1u)+3)/4)*8;
    if(payload+128!=bytes.size()) return nullptr;
    auto image=std::make_unique<Image>();
    auto* device=processor.GetD3D12Provider().GetDevice();
    D3D12_RESOURCE_DESC desc{};
    desc.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;desc.Width=width;desc.Height=height;
    desc.DepthOrArraySize=1;desc.MipLevels=uint16_t(mips);desc.Format=DXGI_FORMAT_BC1_UNORM;
    desc.SampleDesc.Count=1;desc.Layout=D3D12_TEXTURE_LAYOUT_UNKNOWN;
    std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(mips);
    std::vector<UINT> rows(mips);std::vector<UINT64> row_sizes(mips);UINT64 upload_size=0;
    device->GetCopyableFootprints(&desc,0,mips,0,footprints.data(),rows.data(),row_sizes.data(),&upload_size);
    // Retain resources for the session so old submitted descriptors stay valid.
    // The budget counts both the default resource and its upload allocation.
    if(memory_bytes_+upload_size*2>512*1024*1024) return nullptr;
    if(FAILED(device->CreateCommittedResource(&ui::d3d12::util::kHeapPropertiesDefault,
        processor.GetD3D12Provider().GetHeapFlagCreateNotZeroed(),&desc,
        D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&image->texture))))return nullptr;
    D3D12_RESOURCE_DESC upload{};upload.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;
    upload.Width=upload_size;upload.Height=1;upload.DepthOrArraySize=1;upload.MipLevels=1;
    upload.SampleDesc.Count=1;upload.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    if(FAILED(device->CreateCommittedResource(&ui::d3d12::util::kHeapPropertiesUpload,
        D3D12_HEAP_FLAG_NONE,&upload,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,
        IID_PPV_ARGS(&image->upload))))return nullptr;
    void* mapped=nullptr;D3D12_RANGE no_read{0,0};
    if(FAILED(image->upload->Map(0,&no_read,&mapped)))return nullptr;
    std::memset(mapped,0,size_t(upload_size));size_t cursor=128;
    for(uint32_t level=0;level<mips;++level){
      const size_t row_bytes=size_t((std::max(width>>level,1u)+3)/4)*8;
      for(uint32_t row=0;row<rows[level];++row){
        std::memcpy(static_cast<uint8_t*>(mapped)+footprints[level].Offset+
          size_t(row)*footprints[level].Footprint.RowPitch,bytes.data()+cursor,row_bytes);
        cursor+=row_bytes;
      }
    }
    D3D12_RANGE written{0,size_t(upload_size)};image->upload->Unmap(0,&written);
    auto& commands=processor.GetDeferredCommandList();
    for(uint32_t level=0;level<mips;++level){
      D3D12_TEXTURE_COPY_LOCATION source{},destination{};
      source.pResource=image->upload.Get();source.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
      source.PlacedFootprint=footprints[level];destination.pResource=image->texture.Get();
      destination.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;destination.SubresourceIndex=level;
      commands.D3DCopyTextureRegion(&destination,0,0,0,&source,nullptr);
    }
    processor.PushTransitionBarrier(image->texture.Get(),D3D12_RESOURCE_STATE_COPY_DEST,
      D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE|D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    processor.SubmitBarriers();image->mips=mips;memory_bytes_+=upload_size*2;
    return image;
  }
  std::filesystem::path root_;
  std::set<std::string> files_;
  std::map<std::string,std::unique_ptr<Image>> images_;
  uint64_t memory_bytes_=0;
};
}  // namespace rex::graphics::d3d12::fenix
