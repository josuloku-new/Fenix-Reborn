"""Build our original cog/skull artwork; requires only Python's standard library."""
import math
from pathlib import Path
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]

def artwork():
    shapes=[]
    def polygon(points,color):shapes.append(('polygon',points,color))
    def ellipse(box,color):shapes.append(('ellipse',box,color))
    gear=[]
    for tooth in range(12):
        for offset,radius in ((-.46,99),(-.30,120),(.30,120),(.46,99)):
            angle=(tooth+offset)*math.tau/12-math.pi/2
            gear.append((128+radius*math.cos(angle),128+radius*math.sin(angle)))
    polygon(gear,'#aa2337');ellipse((26,26,230,230),'#d23848')
    ellipse((42,42,214,214),'#11151d');ellipse((49,49,207,207),'#20212a')
    ellipse((77,61,179,158),'#f0e7d6')
    polygon([(78,110),(178,110),(178,143),(164,154),(158,180),(98,180),(92,154),(78,143)],'#f0e7d6')
    polygon([(87,115),(119,124),(114,140),(90,136)],'#11151d')
    polygon([(169,115),(137,124),(142,140),(166,136)],'#11151d')
    polygon([(128,137),(117,154),(128,150),(139,154)],'#11151d')
    polygon([(99,159),(157,159),(154,166),(102,166)],'#11151d')
    for x in (110,122,134,146):polygon([(x,161),(x+3,161),(x+3,180),(x,180)],'#11151d')
    for x in (119,131):polygon([(x,78),(x+6,78),(x+6,103),(x,103)],'#aa2337')
    return shapes

def png(size,pixels):
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data))
    scan=b''.join(b'\0'+pixels[y*size*4:(y+1)*size*4] for y in range(size))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan,9))+chunk(b'IEND',b'')

def render(size,shapes):
    scale=3;width=size*scale;pixels=bytearray(width*width*4)
    for kind,geometry,color in shapes:
        rgba=bytes.fromhex(color[1:])+b'\xff'
        if kind=='ellipse':
            x0,y0,x1,y1=geometry;cx=(x0+x1)/2;cy=(y0+y1)/2;rx=(x1-x0)/2;ry=(y1-y0)/2
            contains=lambda x,y:((x-cx)/rx)**2+((y-cy)/ry)**2<=1
        else:
            xs,ys=zip(*geometry);x0=min(xs);x1=max(xs);y0=min(ys);y1=max(ys)
            edges=list(zip(geometry,geometry[1:]+geometry[:1]))
            def contains(x,y):
                inside=False
                for (ax,ay),(bx,by) in edges:
                    if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
                return inside
        for py in range(max(0,int(y0*width/256)),min(width,math.ceil(y1*width/256))):
            y=(py+.5)*256/width
            for px in range(max(0,int(x0*width/256)),min(width,math.ceil(x1*width/256))):
                if contains((px+.5)*256/width,y):
                    offset=(py*width+px)*4;pixels[offset:offset+4]=rgba
    result=bytearray()
    for y in range(size):
        for x in range(size):
            samples=[(yy*width+xx)*4 for yy in range(y*scale,(y+1)*scale) for xx in range(x*scale,(x+1)*scale)]
            alpha=sum(pixels[p+3] for p in samples)
            result.extend(round(sum(pixels[p+c]*pixels[p+3] for p in samples)/alpha) if alpha else 0 for c in range(3))
            result.append(round(alpha/(scale*scale)))
    return bytes(result)

def main():
    shapes=artwork();assets=ROOT/'launcher/assets';assets.mkdir(parents=True,exist_ok=True)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">',
         '<!-- Original artwork by JoSuLoku @2026. Project license; no game assets. -->']
    for kind,geometry,color in shapes:
        if kind=='ellipse':
            x0,y0,x1,y1=geometry;svg.append(f'<ellipse cx="{(x0+x1)/2:g}" cy="{(y0+y1)/2:g}" rx="{(x1-x0)/2:g}" ry="{(y1-y0)/2:g}" fill="{color}"/>')
        else:svg.append('<polygon points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in geometry)+f'" fill="{color}"/>')
    (assets/'gow2.svg').write_text('\n'.join(svg+['</svg>'])+'\n','utf-8')
    sizes=(16,24,32,48,64,128,256);images=[]
    for size in sizes:
        pixels=render(size,shapes)
        if size<=48:
            bgra=b''.join(bytes((pixels[p+2],pixels[p+1],pixels[p],pixels[p+3])) for y in reversed(range(size)) for p in range(y*size*4,(y+1)*size*4,4))
            mask=b'\0'*(((size+31)//32)*4*size)
            images.append(struct.pack('<IiiHHIIiiII',40,size,size*2,1,32,0,len(bgra),0,0,0,0)+bgra+mask)
        else:images.append(png(size,pixels))
    offset=6+16*len(images);directory=[]
    for size,data in zip(sizes,images):
        directory.append(struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(data),offset));offset+=len(data)
    (assets/'gow2.ico').write_bytes(struct.pack('<HHH',0,1,len(images))+b''.join(directory)+b''.join(images))
    print('Original icon built:',assets/'gow2.ico')

if __name__=='__main__':main()
