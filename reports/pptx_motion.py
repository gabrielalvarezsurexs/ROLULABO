"""Transiciones y animaciones para la presentación, escritas directo en el XML de PowerPoint.

python-pptx no expone transiciones ni animaciones, así que aquí se inyectan los
elementos <p:transition> y <p:timing> que PowerPoint y Google Slides entienden.

Reglas de animación por diapositiva
    El encabezado (etiqueta y título) y el pie quedan fijos.
    El resto se agrupa por tarjeta, cada elemento dentro de una tarjeta entra con ella.
    Los grupos entran solos en orden de lectura al abrir la diapositiva, sin clics.
    Las gráficas entran con barrido de abajo hacia arriba, lo demás con desvanecido.
"""
from lxml import etree
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn

EMU = 914400
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _in(v):
    return (v or 0) / EMU


def _box(sh):
    return _in(sh.left), _in(sh.top), _in(sh.width), _in(sh.height)


def _is_card(sh):
    if sh.shape_type != MSO_SHAPE_TYPE.AUTO_SHAPE:
        return False
    _, _, w, h = _box(sh)
    return w >= 1.2 and h >= 0.9


def _groups(slide, skip_top=1.95, skip_bottom=6.85, max_groups=9):
    shapes = []
    for sh in slide.shapes:
        x, y, w, h = _box(sh)
        if y < skip_top and h < 1.5:
            continue
        if y >= skip_bottom:
            continue
        shapes.append(sh)
    cards = [s for s in shapes if _is_card(s)]

    def container(sh):
        x, y, w, h = _box(sh)
        cx, cy = x + w / 2, y + h / 2
        best = None
        for c in cards:
            if c is sh:
                continue
            X, Y, W, H = _box(c)
            if X <= cx <= X + W and Y <= cy <= Y + H and W * H > w * h:
                if best is None or W * H < _box(best)[2] * _box(best)[3]:
                    best = c
        return best

    groups = {}
    for sh in shapes:
        anchor = container(sh) or sh
        groups.setdefault(anchor.shape_id, {"anchor": anchor, "members": []})["members"].append(sh)
    ordered = sorted(groups.values(), key=lambda g: (round(_box(g["anchor"])[1] / 0.35), _box(g["anchor"])[0]))
    # Si hay demasiados grupos se juntan de dos en dos para no alargar la entrada.
    while len(ordered) > max_groups:
        merged = []
        for i in range(0, len(ordered), 2):
            pair = ordered[i:i + 2]
            merged.append({"anchor": pair[0]["anchor"], "members": [m for g in pair for m in g["members"]]})
        ordered = merged
    return [g["members"] for g in ordered]


def _el(tag, **attrs):
    e = etree.Element(qn(tag))
    for k, v in attrs.items():
        e.set(k, str(v))
    return e


def _sub(parent, tag, **attrs):
    e = _el(tag, **attrs)
    parent.append(e)
    return e


class _Ids:
    def __init__(self):
        self.n = 2

    def next(self):
        self.n += 1
        return self.n


def _effect(ids, spid, delay, kind):
    par = _el("p:par")
    ctn = _sub(par, "p:cTn", id=ids.next(), fill="hold")
    st = _sub(ctn, "p:stCondLst")
    _sub(st, "p:cond", delay=delay)
    kids = _sub(ctn, "p:childTnLst")
    inner = _sub(kids, "p:par")
    if kind == "wipe":
        preset, subtype, flt, dur = 22, 4, "wipe(up)", 700
    else:
        preset, subtype, flt, dur = 10, 0, "fade", 450
    ectn = _sub(inner, "p:cTn", id=ids.next(), presetID=preset, presetClass="entr", presetSubtype=subtype,
                fill="hold", grpId=0, nodeType="withEffect")
    est = _sub(ectn, "p:stCondLst")
    _sub(est, "p:cond", delay=0)
    ekids = _sub(ectn, "p:childTnLst")
    st_set = _sub(ekids, "p:set")
    b = _sub(st_set, "p:cBhvr")
    t = _sub(b, "p:cTn", id=ids.next(), dur=1, fill="hold")
    tst = _sub(t, "p:stCondLst")
    _sub(tst, "p:cond", delay=0)
    tg = _sub(b, "p:tgtEl")
    _sub(tg, "p:spTgt", spid=spid)
    an = _sub(b, "p:attrNameLst")
    _sub(an, "p:attrName").text = "style.visibility"
    to = _sub(st_set, "p:to")
    _sub(to, "p:strVal", val="visible")
    ae = _sub(ekids, "p:animEffect", transition="in", filter=flt)
    b2 = _sub(ae, "p:cBhvr")
    _sub(b2, "p:cTn", id=ids.next(), dur=dur)
    tg2 = _sub(b2, "p:tgtEl")
    _sub(tg2, "p:spTgt", spid=spid)
    return par


def animate(slide, step_ms=230):
    groups = _groups(slide)
    if not groups:
        return 0
    ids = _Ids()
    timing = _el("p:timing")
    tn = _sub(timing, "p:tnLst")
    root_par = _sub(tn, "p:par")
    root = _sub(root_par, "p:cTn", id=1, dur="indefinite", restart="never", nodeType="tmRoot")
    rk = _sub(root, "p:childTnLst")
    seq = _sub(rk, "p:seq", concurrent=1, nextAc="seek")
    main = _sub(seq, "p:cTn", id=2, dur="indefinite", nodeType="mainSeq")
    mk = _sub(main, "p:childTnLst")
    click = _sub(mk, "p:par")
    cctn = _sub(click, "p:cTn", id=ids.next(), fill="hold")
    cst = _sub(cctn, "p:stCondLst")
    _sub(cst, "p:cond", delay="indefinite")
    auto = _sub(cst, "p:cond", evt="onBegin", delay=0)
    _sub(auto, "p:tn", val=2)
    ck = _sub(cctn, "p:childTnLst")
    animated = []
    for g, members in enumerate(groups):
        for sh in members:
            kind = "wipe" if sh.shape_type == MSO_SHAPE_TYPE.CHART or getattr(sh, "has_chart", False) else "fade"
            ck.append(_effect(ids, sh.shape_id, g * step_ms, kind))
            animated.append(sh)
    prev = _sub(seq, "p:prevCondLst")
    pc = _sub(prev, "p:cond", evt="onPrev", delay=0)
    _sub(_sub(pc, "p:tgtEl"), "p:sldTgt")
    nxt = _sub(seq, "p:nextCondLst")
    nc = _sub(nxt, "p:cond", evt="onNext", delay=0)
    _sub(_sub(nc, "p:tgtEl"), "p:sldTgt")
    bld = _sub(timing, "p:bldLst")
    for sh in animated:
        if sh.shape_type in (MSO_SHAPE_TYPE.AUTO_SHAPE, MSO_SHAPE_TYPE.TEXT_BOX) and sh.has_text_frame:
            _sub(bld, "p:bldP", spid=sh.shape_id, grpId=0, animBg=1)
    if len(bld) == 0:
        timing.remove(bld)
    _place(slide, timing)
    return len(groups)


def transition(slide, kind="fade"):
    tr = _el("p:transition", spd="med")
    if kind == "fade_black":
        _sub(tr, "p:fade", thruBlk=1)
    elif kind == "push":
        _sub(tr, "p:push", dir="u")
    elif kind == "wipe":
        _sub(tr, "p:wipe", dir="r")
    else:
        _sub(tr, "p:fade")
    _place(slide, tr)


def _place(slide, el):
    """Respeta el orden del esquema. cSld, clrMapOvr, transition, timing, extLst."""
    sld = slide._element
    tag = el.tag
    for old in sld.findall(tag):
        sld.remove(old)
    order = [qn("p:cSld"), qn("p:clrMapOvr"), qn("p:transition"), qn("p:timing"), qn("p:extLst")]
    pos = order.index(tag)
    idx = 0
    for i, child in enumerate(list(sld)):
        if child.tag in order and order.index(child.tag) < pos:
            idx = i + 1
    sld.insert(idx, el)
