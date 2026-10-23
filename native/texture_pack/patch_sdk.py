"""Apply the small native texture-pack hooks to pinned ReXGlue 0.10.0 source."""
from pathlib import Path
import argparse

def patch(root):
    def edit(relative, replacements):
        path=root/relative
        text=path.read_text('utf-8')
        if 'FENIX_TEXTURE_PACK_HOOKS' in text:return
        for before,after in replacements:
            if text.count(before)!=1:raise ValueError('SDK source does not match: '+relative+' / '+before[:70])
            text=text.replace(before,after,1)
        path.write_text('// FENIX_TEXTURE_PACK_HOOKS\n'+text,'utf-8')
    edit('include/rex/graphics/d3d12/shared_memory.h',[(
        'ID3D12Resource* GetBuffer() const { return buffer_; }',
        'memory::Memory& FenixGuestMemory() const { return memory(); }\n  ID3D12Resource* GetBuffer() const { return buffer_; }')])
    edit('include/rex/graphics/d3d12/texture_cache.h',[
        ('class D3D12CommandProcessor;', 'class D3D12CommandProcessor;\nnamespace fenix { struct Image; }'),
        ('uint8_t swizzled_signs;', 'uint8_t swizzled_signs;\n    uint32_t fenix_generation;'),
        ('uint32_t dimension : 2;', 'uint32_t dimension : 2;\n        uint32_t fenix_revision : 17;'),
        ('ID3D12Resource* resource() const { return resource_.Get(); }\n\n    D3D12_RESOURCE_STATES SetResourceState',
         'fenix::Image* fenix_image = nullptr;\n    uint32_t fenix_revision = 0;\n    ID3D12Resource* resource() const { return resource_.Get(); }\n\n    D3D12_RESOURCE_STATES SetResourceState'),
        ('std::vector<SRVDescriptorCachePage> srv_descriptor_cache_;',
         'uint32_t fenix_generation_ = 0;\n  uint32_t fenix_bindings_generation_ = 0;\n  std::vector<SRVDescriptorCachePage> srv_descriptor_cache_;')])
    edit('src/graphics/d3d12/texture_cache.cpp',[
        ('#include <rex/graphics/d3d12/texture_cache.h>', '#include <rex/graphics/d3d12/texture_cache.h>\n#include "fenix_texture_pack.h"'),
        ('TextureCache::RequestTextures(used_texture_mask);', '''TextureCache::RequestTextures(used_texture_mask);
  if (fenix_bindings_generation_ != fenix_generation_) {
    UpdateTextureBindingsImpl(UINT32_MAX);
    fenix_bindings_generation_ = fenix_generation_;
  }'''),
        ('const TextureSRVKey& key = keys[i];', 'const TextureSRVKey& key = keys[i];\n    if (key.fenix_generation != fenix_generation_) return false;'),
        ('TextureSRVKey& key = keys[i];\n    const TextureBinding*', 'TextureSRVKey& key = keys[i];\n    key.fenix_generation = fenix_generation_;\n    const TextureBinding*'),
        ('TextureKey texture_key = d3d12_texture.key();\n\n  DeferredCommandList&', '''TextureKey texture_key = d3d12_texture.key();
  if (load_base && fenix::Pack::Get().enabled() &&
      texture_key.format == xenos::TextureFormat::k_DXT1 && !texture_key.scaled_resolve &&
      texture_key.dimension == xenos::DataDimension::k2DOrStacked &&
      texture_key.GetDepthOrArraySize() == 1 && texture_key.GetWidth() >= 256 &&
      texture_key.GetHeight() >= 256 &&
      uint64_t(texture_key.base_page << 12) + d3d12_texture.GetGuestBaseSize() <= 0x20000000ull) {
    const auto* source = static_cast<D3D12SharedMemory&>(shared_memory()).FenixGuestMemory()
                             .TranslatePhysical<const uint8_t*>(texture_key.base_page << 12);
    const uint64_t hash = fenix::HashBC1(texture_key.GetWidth(), texture_key.GetHeight(),
        texture_key.tiled, uint32_t(texture_key.endianness), d3d12_texture.guest_layout(), source);
    fenix::Image* image = fenix::Pack::Get().Find(hash, texture_key.GetWidth(),
                                               texture_key.GetHeight(), command_processor_);
    if (d3d12_texture.fenix_image != image && d3d12_texture.fenix_revision < 131070) {
      d3d12_texture.fenix_image = image;
      ++d3d12_texture.fenix_revision;
      ++fenix_generation_;
    }
    if (std::getenv("FENIX_TEXTURE_AUDIT")) {
      REXGPU_INFO("Fenix HD source: {:016x}_{}x{} page={}", hash,
                  texture_key.GetWidth(), texture_key.GetHeight(), uint32_t(texture_key.base_page));
    }
  }

  DeferredCommandList&'''),
        ('descriptor_key.dimension = uint32_t(dimension);', 'descriptor_key.dimension = uint32_t(dimension);\n  descriptor_key.fenix_revision = texture.fenix_revision;'),
        ('ID3D12Resource* resource_for_view = texture.resource();', '''ID3D12Resource* resource_for_view = texture.resource();
  if (texture.fenix_image && !is_signed) {
    resource_for_view = texture.fenix_image->texture.Get();
    mip_levels = texture.fenix_image->mips;
  }''')])

    # A 2x replacement normally gets sampled one mip lower than the original.
    # Carry an HD bit in the sampler cache key so only replaced resources get
    # the compensating bias, including shaders that reuse sampler descriptors.
    upgrades = [
        ('include/rex/graphics/d3d12/texture_cache.h', [
            ('uint32_t mip_base_map : 1;            // 22',
             'uint32_t mip_base_map : 1;            // 22\n      uint32_t fenix_hd : 1;                // 23'),
        ]),
        ('src/graphics/d3d12/texture_cache.cpp', [
            ('  parameters.mip_base_map = mip_base_map;\n\n  return parameters;', '''  parameters.mip_base_map = mip_base_map;
  const TextureBinding* fenix_binding = GetValidTextureBinding(binding.fetch_constant);
  parameters.fenix_hd = fenix_binding && fenix_binding->texture &&
      static_cast<const D3D12Texture*>(fenix_binding->texture)->fenix_image ? 1 : 0;

  return parameters;'''),
            ('  desc.MipLODBias = 0.0f;',
             '  desc.MipLODBias = parameters.fenix_hd ? -1.0f : 0.0f;'),
            ('  desc.MinLOD = float(parameters.mip_min_level);',
             '  desc.MinLOD = std::max(0.0f, float(parameters.mip_min_level) -\n                         float(parameters.fenix_hd));'),
        ]),
    ]
    for relative, replacements in upgrades:
        path=root/relative
        text=path.read_text('utf-8')
        for before, after in replacements:
            if after in text:continue
            if text.count(before)!=1:raise ValueError('SDK sampler source does not match: '+relative+' / '+before[:70])
            text=text.replace(before,after,1)
        path.write_text(text,'utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('sdk',type=Path)
    patch(parser.parse_args().sdk)
