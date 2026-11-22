"""캐릭터 비율 프록시 생성 스크립트 (Blender에서 실행)

기준 에셋 이미지에서 측정한 비율·색으로 단순 도형 프록시를 만든다.
- 정서연 163cm (C01, 머리 정수리 기준 / 번 제외), 머리 = 키의 약 21% (약 4.8등신)
- 걱정 인형 15cm (C03), 머리 = 키의 약 45%
- 인형 인간화 단계 STAGE 0~3 = 15 / 20 / 35 / 60cm (C04a 설정값), 비율은 인형 → 서연으로 보간
- 친구: 수빈 160 / 민준 174 / 지민 165cm (설정 문서에 키가 없어 가정값)
  지민은 C05_친구_C 수정본 도착 전 임시 (긴 웨이브 머리 기준)

결과: CHAR_PROXY 컬렉션 아래 CHR_<이름> 엠프티(원점 = 발바닥 중앙, -Y가 정면)
프리비즈 파일에서는 File > Link/Append 로 CHAR_PROXY 컬렉션을 가져와 사용.
"""
import bpy, math

scn = bpy.context.scene

def lin(c):
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

MATS = {}
def mat(name, srgb, rough=0.8):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = lin(srgb)
    b.inputs['Roughness'].default_value = rough
    m.diffuse_color = lin(srgb)
    MATS[name] = m
    return m

def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or scn.collection
    if c.name not in p.children:
        p.children.link(c)
    return c

def add(kind, col, par, name, loc, scale, m, rot=(0, 0, 0), **kw):
    if kind == 'sph':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=loc)
    elif kind == 'cyl':
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, location=loc, **kw)
    elif kind == 'cone':
        bpy.ops.mesh.primitive_cone_add(vertices=24, location=loc, **kw)
    else:
        bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.rotation_euler = rot
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    o.data.materials.append(m)
    if kind != 'cube':
        for poly in o.data.polygons:
            poly.use_smooth = True
    o.parent = par
    return o

def build(N, H, p, c, x, col, hair='bun', src=''):
    """N 이름, H 키(m), p 비율(키 대비), c 색(sRGB), x 배치 위치"""
    e = bpy.data.objects.new('CHR_' + N, None)
    col.objects.link(e)
    e.location = (x, 0, 0)
    e.empty_display_type = 'SINGLE_ARROW'
    e.empty_display_size = 0.15
    e['height_cm'] = round(H * 100, 1)
    e['source'] = src
    for k, v in p.items():
        e['p_' + k] = v
    M = lambda k: mat(f'M_{N}_{k}', c[k])

    hf = p['hf']
    zc = H * (1 - hf / 2)                       # 머리 중심
    add('sph', col, e, f'{N}_head', (0, 0, zc), (H * p['hw'] / 2, H * p['hd'] / 2, H * hf / 2), M('skin'))
    k = 1.12 if hair == 'curly' else 1.0
    add('sph', col, e, f'{N}_hair', (0, H * p['hd'] * 0.11, zc + H * hf * 0.15),
        (H * p['hw'] / 2 * 1.07 * k, H * p['hd'] / 2 * 1.07 * k, H * hf / 2 * (1.02 if hair == 'curly' else 0.95)), M('hair'))
    if hair == 'bun':
        add('sph', col, e, f'{N}_bun', (0, H * p['hd'] * 0.2, H * (1 + hf * 0.02)), (H * hf * 0.24,) * 3, M('hair'))
    if hair == 'bob':
        add('cyl', col, e, f'{N}_bob', (0, H * p['hd'] * 0.22, zc - H * hf * 0.2),
            (H * p['hw'] / 2 * 1.1, H * p['hd'] / 2 * 0.9, H * hf * 0.28), M('hair'))
    if hair == 'long':
        add('cube', col, e, f'{N}_longhair', (0, H * p['hd'] * 0.32, H * (1 - hf * 1.0)),
            (H * p['hw'] * 0.55, H * 0.035, H * hf * 1.0), M('hair'))

    zs = H * (1 - hf - p['neck'])              # 어깨 높이
    zh = H * p['hip']                          # 상의 밑단 높이
    add('cyl', col, e, f'{N}_neck', (0, 0, zs + H * p['neck'] / 2 + H * 0.01),
        (H * 0.035, H * 0.035, H * p['neck'] / 2 + H * 0.015), M('skin'))
    add('cone', col, e, f'{N}_torso', (0, 0, (zs + zh) / 2),
        (1, p['td'] / ((p['sh'] + p['hem']) / 2), 1), M('top'),
        depth=zs - zh, radius1=H * p['hem'] / 2, radius2=H * p['sh'] / 2)

    zst = H * p['shoe']
    ll = zh + H * 0.03 - zst
    for s in (-1, 1):
        side = 'L' if s < 0 else 'R'
        add('cyl', col, e, f'{N}_leg_{side}', (s * H * p['ls'], 0, zst + ll / 2),
            (H * p['lw'] / 2, H * p['lw'] / 2, ll / 2), M('pants'))
        add('cube', col, e, f'{N}_shoe_{side}', (s * H * p['ls'], -H * 0.02, zst / 2),
            (H * p['lw'] * 0.5, H * p['lw'] * 0.85, zst / 2), M('shoe'))
        ax = s * (H * p['sh'] / 2 + H * p['aw'] * 0.35)
        zw = H * p['wrist']
        al = zs - H * 0.02 - zw
        add('cyl', col, e, f'{N}_arm_{side}', (ax + s * H * 0.012, 0, zw + al / 2),
            (H * p['aw'] / 2, H * p['aw'] / 2, al / 2), M('top'), rot=(0, s * math.radians(-4), 0))
        add('sph', col, e, f'{N}_hand_{side}', (ax + s * H * 0.02, 0, zw - H * 0.03),
            (H * 0.028, H * 0.02, H * 0.04), M('skin'))
    return e

# ---------------- 비율 (키 대비) ----------------
# hf 머리높이, hw/hd 머리 폭/깊이, neck 목, hip 상의 밑단, sh/hem 어깨/밑단 폭, td 몸통 깊이,
# lw 다리 폭, ls 다리 중심 간격(반), aw 팔 폭, wrist 손목 높이, shoe 신발 높이
P_SEO = dict(hf=.21, hw=.23, hd=.23, neck=.02, hip=.42, sh=.27, hem=.30, td=.16,
             lw=.11, ls=.062, aw=.075, wrist=.43, shoe=.035)
P_DOLL = dict(hf=.45, hw=.47, hd=.43, neck=.0, hip=.25, sh=.34, hem=.38, td=.24,
              lw=.16, ls=.09, aw=.12, wrist=.27, shoe=.05)

def mix(a, b, t):
    return {k: round(a[k] + (b[k] - a[k]) * t, 4) for k in a}

# ---------------- 색 (sRGB, 시트에서 샘플 후 보정) ----------------
C_SEO = dict(skin=(.92, .75, .65), hair=(.16, .09, .07), top=(.44, .40, .28),
             pants=(.27, .25, .25), shoe=(.80, .77, .72))
C_DOLL = dict(skin=(.93, .85, .76), hair=(.18, .10, .08), top=(.44, .40, .28),
              pants=(.27, .25, .25), shoe=(.95, .95, .93))
C_SUBIN = dict(skin=(.93, .74, .63), hair=(.06, .06, .07), top=(.70, .60, .50),
               pants=(.20, .20, .20), shoe=(.90, .89, .86))
C_MINJUN = dict(skin=(.92, .72, .60), hair=(.05, .05, .05), top=(.15, .12, .12),
                pants=(.30, .28, .28), shoe=(.80, .78, .74))
C_JIMIN = dict(skin=(.95, .76, .65), hair=(.03, .03, .03), top=(.42, .27, .18),
               pants=(.12, .10, .09), shoe=(.30, .22, .17))

# ---------------- 생성 ----------------
old = bpy.data.collections.get('CHAR_PROXY')
if old:
    for o in list(old.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for ch in list(old.children_recursive):
        bpy.data.collections.remove(ch)
    bpy.data.collections.remove(old)

root = coll('CHAR_PROXY')
c_main = coll('CHAR_SEOYEON', root)
c_doll = coll('CHAR_DOLL_STAGES', root)
c_fr = coll('CHAR_FRIENDS', root)

build('SEOYEON', 1.63, P_SEO, C_SEO, 0.0, c_main, 'bun', 'C01_주인공_턴어라운드.png')

# 친구 (같은 퍼펫 비율 체계, 체형만 조정)
P_SUBIN = dict(P_SEO, hf=.205, sh=.25, hem=.25, td=.14, lw=.09, ls=.055, aw=.06, hip=.44)
P_MINJUN = dict(P_SEO, hf=.19, hw=.20, hd=.21, sh=.29, hem=.29, td=.16, lw=.11, ls=.065, aw=.07, hip=.44)
P_JIMIN = dict(P_SEO, hf=.20, sh=.25, hem=.25, td=.14, lw=.085, ls=.055, aw=.06, hip=.45)
build('SUBIN', 1.60, P_SUBIN, C_SUBIN, 1.0, c_fr, 'bob', 'C05_친구_A_턴어라운드.png')
build('MINJUN', 1.74, P_MINJUN, C_MINJUN, 1.8, c_fr, 'curly', 'C05_친구_B_턴어라운드.png')
build('JIMIN', 1.65, P_JIMIN, C_JIMIN, 2.6, c_fr, 'long', 'C05_친구_C (임시, 수정본 대기)')

# 걱정 인형 단계: 키는 설정 cm, 비율은 인형→서연 보간 (C04a 외형 기준)
stages = [('DOLL_S0', .15, 0.0), ('DOLL_S1', .20, 0.25), ('DOLL_S2', .35, 0.6), ('DOLL_S3', .60, 0.9)]
x = -1.4
for n, h, t in stages:
    skin = tuple(C_DOLL['skin'][i] + (C_SEO['skin'][i] - C_DOLL['skin'][i]) * t for i in range(3))
    c = dict(C_DOLL, skin=skin, shoe=C_DOLL['shoe'] if t < .5 else C_SEO['shoe'])
    build(n, h, mix(P_DOLL, P_SEO, t), c, x, c_doll, 'bun', 'C03 / C04a / C04a2')
    x += max(h * 0.9, 0.25)
    x = round(x, 3)

print('built', [o.name for o in root.all_objects if o.type == 'EMPTY'])
