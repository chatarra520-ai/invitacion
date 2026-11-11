"""Convierte un PNG (ideal: fondo transparente) en tarjeta.glb con movimiento flotante.
Uso: python hacer_tarjeta.py ilustracion.png
"""
import sys, math, struct, io
import numpy as np
from PIL import Image as PILImage
from pygltflib import *

src = sys.argv[1] if len(sys.argv) > 1 else "ilustracion.png"
img = PILImage.open(src).convert("RGBA")
img.thumbnail((1024, 1024))
w, h = img.size
H = 0.30                      # alto de la tarjeta en metros
W = H * w / h
y0 = 0.06                     # altura del borde inferior sobre la superficie

verts = np.array([[-W/2, y0, 0], [W/2, y0, 0], [W/2, y0+H, 0], [-W/2, y0+H, 0]], dtype=np.float32)
uvs = np.array([[0, 1], [1, 1], [1, 0], [0, 0]], dtype=np.float32)
norms = np.array([[0, 0, 1]] * 4, dtype=np.float32)
idx = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint16)

# animación: sube/baja 2 cm y se balancea +-6 grados, ciclo de 4 s
N = 33
t = np.linspace(0, 4, N, dtype=np.float32)
ph = 2 * math.pi * t / 4
trans = np.array([[0, 0.02 * math.sin(p), 0] for p in ph], dtype=np.float32)
rot = np.array([[0, math.sin(math.radians(6) * math.sin(p) / 2), 0, math.cos(math.radians(6) * math.sin(p) / 2)] for p in ph], dtype=np.float32)

buf = io.BytesIO()
views, accs = [], []
def add(data, target=None):
    b = data.tobytes()
    off = buf.tell(); buf.write(b)
    while buf.tell() % 4: buf.write(b"\0")
    views.append(BufferView(buffer=0, byteOffset=off, byteLength=len(b), target=target))
    return len(views) - 1

png = io.BytesIO(); img.save(png, "PNG"); pngb = png.getvalue()

vi = add(verts, ARRAY_BUFFER); ui = add(uvs, ARRAY_BUFFER); ni = add(norms, ARRAY_BUFFER)
ii = add(idx, ELEMENT_ARRAY_BUFFER); ti = add(t); tri = add(trans); roi = add(rot)
off = buf.tell(); buf.write(pngb)
while buf.tell() % 4: buf.write(b"\0")
views.append(BufferView(buffer=0, byteOffset=off, byteLength=len(pngb)))
imgview = len(views) - 1

accs = [
 Accessor(bufferView=vi, componentType=FLOAT, count=4, type=VEC3, min=verts.min(0).tolist(), max=verts.max(0).tolist()),
 Accessor(bufferView=ui, componentType=FLOAT, count=4, type=VEC2),
 Accessor(bufferView=ni, componentType=FLOAT, count=4, type=VEC3),
 Accessor(bufferView=ii, componentType=UNSIGNED_SHORT, count=6, type=SCALAR),
 Accessor(bufferView=ti, componentType=FLOAT, count=N, type=SCALAR, min=[float(t.min())], max=[float(t.max())]),
 Accessor(bufferView=tri, componentType=FLOAT, count=N, type=VEC3),
 Accessor(bufferView=roi, componentType=FLOAT, count=N, type=VEC4),
]
g = GLTF2(
 scene=0, scenes=[Scene(nodes=[0])], nodes=[Node(mesh=0, name="tarjeta")],
 meshes=[Mesh(primitives=[Primitive(attributes=Attributes(POSITION=0, TEXCOORD_0=1, NORMAL=2), indices=3, material=0)])],
 materials=[Material(name="ilustracion", alphaMode="BLEND", doubleSided=True,
   pbrMetallicRoughness=PbrMetallicRoughness(baseColorTexture=TextureInfo(index=0), metallicFactor=0, roughnessFactor=1))],
 textures=[Texture(source=0, sampler=0)], images=[Image(bufferView=imgview, mimeType="image/png")],
 samplers=[Sampler(magFilter=LINEAR, minFilter=LINEAR_MIPMAP_LINEAR)],
 bufferViews=views, accessors=accs,
 animations=[Animation(name="flotar",
   samplers=[AnimationSampler(input=4, output=5, interpolation="LINEAR"), AnimationSampler(input=4, output=6, interpolation="LINEAR")],
   channels=[AnimationChannel(sampler=0, target=AnimationChannelTarget(node=0, path="translation")),
             AnimationChannel(sampler=1, target=AnimationChannelTarget(node=0, path="rotation"))])],
 buffers=[Buffer(byteLength=buf.tell())],
)
g.set_binary_blob(buf.getvalue())
g.save_binary("tarjeta.glb")
print("OK: tarjeta.glb creado", W, H)
