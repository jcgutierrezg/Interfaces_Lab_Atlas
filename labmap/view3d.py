"""A 3D view of each room in the directory: rooms/<ROOM>-3d.html.

The .glb from `model` opens in Open3D Viewer or Blender, but the directory is what people have open: off a shared drive, often on
a machine that isn't theirs. So each room also gets a page that shows the same model in the browser. Drag to turn
it, right-drag (or Shift-drag, or two fingers) to move it, scroll or pinch to zoom, and click a thing to see what
it is and open its page. What the checks flag is coloured as in the report, and clear zones are painted in.

It is written against WebGL directly rather than a 3D library. A massing model of flat-shaded boxes needs a
camera, one shader and a way to tell what was clicked, and nothing more; a library would be the biggest file in
the site, and would have to be copied in, since the directory has to work with no internet. The geometry is
embedded in the page, because a browser won't let a page opened from a disk read the file next to it.
"""
from __future__ import annotations

import base64
import html
import json
import struct

LAYERS = ("floor", "walls", "things", "zones")


def _kind(name, rid):
    """(layer, object id) for a node of glb.scene: the room's floor and walls, a thing, or a thing's clear zone."""
    if name == f"{rid} floor":
        return "floor", None
    if name == f"{rid} walls":
        return "walls", None
    first = name.split(" ")[0]  # ids have no spaces
    return ("zones", first) if name.endswith(" clear zone") else ("things", first)


def _rgb(hex_colour):
    h = (hex_colour or "#b9bcc2").lstrip("#")
    return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4)) if len(h) == 6 else (185, 188, 194)


def _b64(fmt, values):
    return base64.b64encode(struct.pack(f"<{len(values)}{fmt}", *values)).decode("ascii")


def room_data(lab, res, rid, href):
    """Everything the viewer needs for one room, as a JSON-able dict: vertex positions (metres, Y up, as in the
    .glb), a colour per vertex with the face's shade baked in, which object each vertex belongs to (0 for none,
    so clicking the floor selects nothing), and one index range per layer so walls and zones can be switched off.
    href(id) is the link to an object's page."""
    from . import glb
    from .layout import _flagged

    flagged = _flagged(lab, res)
    nodes, _ = glb.scene(lab, rid, res.geo, glb.WALL_H, flagged, person=lab.settings["person_height"])
    pos, col, pick = [], bytearray(), []
    faces = {k: [] for k in LAYERS}
    objects, number = [None], {}
    for name, (mesh, colour, *rest) in nodes.items():
        if not mesh:
            continue
        layer, i = _kind(name, rid)
        first = len(pos) // 3
        pos += mesh.pos
        base = _rgb(colour)
        for shade in mesh.col[0::4]:
            col += bytes(min(255, round(c * shade)) for c in base)
        n = 0
        if layer == "things":
            if i not in number:
                r = lab.placeables.get(i, {})
                msgs, bad = flagged.get(i, ([], False))
                xs, ys, zs = mesh.pos[0::3], mesh.pos[1::3], mesh.pos[2::3]
                number[i] = len(objects)
                objects.append({"id": i, "name": r.get("name") or "", "cat": r.get("category") or "",
                                "find": msgs, "bad": bad, "href": href(i),
                                "c": [round((min(v) + max(v)) / 2, 3) for v in (xs, ys, zs)],
                                "top": round(max(ys), 3),  # where the pin hangs from, and the ring spreads out
                                "r": round(max(max(xs) - min(xs), max(zs) - min(zs)) / 2, 3)})
            n = number[i]
        elif layer == "zones":
            n = number.get(i, 0)  # its owner's: a selected thing keeps its own clear zone when the rest fades
        pick += [n] * (len(mesh.pos) // 3)
        faces[layer] += [first + k for k in mesh.idx]
    index, ranges = [], {}
    for layer in LAYERS:
        ranges[layer] = [len(index), len(faces[layer])]
        index += faces[layer]
    xs, zs = pos[0::3], pos[2::3]
    return {"room": rid, "pos": _b64("f", pos), "col": base64.b64encode(bytes(col)).decode("ascii"),
            "pick": _b64("H", pick), "idx": _b64("I", index), "ranges": ranges, "objects": objects,
            "box": [round(min(xs), 3), round(min(zs), 3), round(max(xs), 3), round(max(zs), 3)] if xs else [0, 0, 1, 1]}


def page_body(lab, res, rid, href, room_href, glb_name):
    """The <main> of rooms/<ROOM>-3d.html."""
    data = json.dumps(room_data(lab, res, rid, href), separators=(",", ":"), ensure_ascii=False)
    room = lab.rooms[rid]
    esc = html.escape
    return (f"<h1>{esc(rid)} <span class='sub'>{esc(room.get('name') or '')} · in 3D</span></h1>"
            f"<p class='note'><a href='{esc(room_href)}'>← the plan</a> · "
            f"<a href='{esc(glb_name)}' download>download the model</a> for Open3D Viewer or Blender</p>"
            "<div class='v3d'><canvas id='v3d' aria-label='3D model of the room'></canvas>"
            "<div class='v3d-bar'><button data-layer='walls' class='on'>Walls</button>"
            "<button data-layer='zones' class='on'>Clear zones</button>"
            "<button data-layer='focus' class='on' title='When something is selected, show everything else as a "
            "faint ghost'>Fade the rest</button><button id='v3d-reset'>Reset view</button>"
            "<span class='v3d-help'>Drag to turn · right-drag or Shift-drag to move · scroll to zoom · "
            "click a thing</span></div><div id='v3d-info' hidden></div>"
            f"<p id='v3d-none' hidden>This browser can't show 3D. <a href='{esc(glb_name)}' download>Download the "
            "model</a> and open it in Open3D Viewer or Blender.</p></div>"
            "<p class='v3d-key'><i style='background:#c62828'></i>a problem <i style='background:#e08a00'></i>a warning "
            "<i style='background:#f2c200;opacity:.6'></i>space that has to stay clear · benches float over their leg "
            "room, so you can see what's under them</p>"
            f"<script>window.LAB3D={data};</script>")


CSS = """
.v3d { position: relative; margin: 8px 0; }
#v3d { display: block; width: 100%; height: 72vh; min-height: 360px; background: #eef1f4; border: 1px solid #d1d9e0;
       border-radius: 8px; touch-action: none; cursor: grab; }
#v3d:active { cursor: grabbing; }
.v3d-bar { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 8px; }
.v3d-bar button { font: inherit; font-size: 13px; padding: 3px 11px; border: 1px solid #d1d9e0; background: #fff;
                  border-radius: 999px; cursor: pointer; }
.v3d-bar button.on { background: #1f4e79; border-color: #1f4e79; color: #fff; }
.v3d-help { font-size: 12px; color: #59636e; margin-left: 4px; }
#v3d-info { position: absolute; top: 10px; right: 10px; max-width: min(340px, 70%); background: #fff;
            border: 1px solid #d1d9e0; border-radius: 8px; padding: 10px 12px; box-shadow: 0 2px 10px rgba(0,0,0,.12);
            font-size: 14px; }
#v3d-info .cat { color: #59636e; font-size: 12px; }
#v3d-info .x { position: absolute; top: 4px; right: 6px; border: 0; background: none; font-size: 18px; line-height: 1;
               color: #59636e; cursor: pointer; padding: 2px 4px; }
#v3d-info strong { color: #e11d48; }
#v3d-info ul { margin: 6px 0 0; padding-left: 18px; }
#v3d-info li.bad { color: #b42318; } #v3d-info li { color: #93370d; }
@media (max-width: 640px) {  /* on a phone the card would cover what was just tapped: put it under the model */
  #v3d-info { position: static; max-width: none; margin-top: 8px; box-shadow: none; }
  #v3d { height: 60vh; }
}
.v3d-key { font-size: 12px; color: #59636e; }
.v3d-key i { display: inline-block; width: 11px; height: 11px; border-radius: 2px; margin: 0 4px 0 10px;
             vertical-align: -1px; }
.v3d-key i:first-child { margin-left: 0; }
"""

JS = r"""
(function () {
  var D = window.LAB3D, cv = document.getElementById('v3d');
  if (!D || !cv) return;
  var gl = cv.getContext('webgl2', {antialias: true});
  if (!gl) { cv.hidden = true; document.getElementById('v3d-none').hidden = false; return; }

  function bytes(s) { var b = atob(s), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
  var pos = new Float32Array(bytes(D.pos).buffer), col = bytes(D.col),
      pick = new Uint16Array(bytes(D.pick).buffer), idx = new Uint32Array(bytes(D.idx).buffer);

  function shader(type, src) {
    var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  var prog = gl.createProgram();
  gl.attachShader(prog, shader(gl.VERTEX_SHADER, '#version 300 es\n' +
    'in vec3 aPos; in vec3 aCol; in float aPick; uniform mat4 uMVP; uniform vec3 uShift; uniform float uScale;\n' +
    'out vec3 vCol; out vec3 vPos; flat out float vPick;\n' +
    'void main() { vec3 p = aPos * uScale + uShift; vCol = aCol; vPos = p; vPick = aPick;\n' +
    '              gl_Position = uMVP * vec4(p, 1.0); }'));
  gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, '#version 300 es\nprecision highp float;\n' +
    'in vec3 vCol; in vec3 vPos; flat in float vPick;\n' +
    'uniform float uAlpha; uniform float uPicked; uniform int uMode; uniform int uFocus; uniform float uPulse;\n' +
    'out vec4 o;\n' +
    'void main() {\n' +
    '  if (uMode == 1) { o = vec4(mod(vPick, 256.0) / 255.0, floor(vPick / 256.0) / 255.0, 0.0, 1.0); return; }\n' +
    '  bool mine = uPicked > 0.5 && abs(vPick - uPicked) < 0.5;\n' +
    '  if (uFocus == 1 && !mine) discard;\n' +                    // the selected thing on its own...
    '  if (uFocus == 2 && mine) discard;\n' +                     // ...and everything else, as a ghost
    '  vec3 n = normalize(cross(dFdx(vPos), dFdy(vPos)));\n' +    // flat faces: the normal from the slope
    '  vec3 c = vCol * (0.8 + 0.2 * abs(dot(n, normalize(vec3(0.45, 0.8, 0.35)))));\n' +
    '  if (mine) c = mix(c, mix(vec3(1.0, 0.85, 0.3), vec3(1.0, 0.54, 0.24), uPulse), 0.6);\n' +  // the 2D flash
    '  if (uFocus == 2) { float g = dot(c, vec3(0.3, 0.59, 0.11)); c = mix(vec3(g), c, 0.3); }\n' +
    '  o = vec4(c, uAlpha);\n' +
    '}'));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  gl.useProgram(prog);
  var U = {};
  ['uMVP', 'uAlpha', 'uPicked', 'uMode', 'uFocus', 'uPulse', 'uShift', 'uScale'].forEach(function (n) {
    U[n] = gl.getUniformLocation(prog, n);
  });

  function attr(name, data, size, type, norm) {
    var b = gl.createBuffer(), loc = gl.getAttribLocation(prog, name);
    gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, type, norm, 0, 0);
  }
  var vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  attr('aPos', pos, 3, gl.FLOAT, false);
  attr('aCol', col, 3, gl.UNSIGNED_BYTE, true);
  attr('aPick', pick, 1, gl.UNSIGNED_SHORT, false);
  var ib = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);

  // --- the pin and the ring, as on the 2D map: a unit shape, moved and sized when drawn -------------------------------
  function shape(points, rgb) {
    var n = points.length / 3, cols = new Uint8Array(n * 3), none = new Uint16Array(n), v = gl.createVertexArray();
    for (var k = 0; k < n; k++) { var s = 0.72 + 0.28 * ((k / 3 | 0) % 3) / 2; cols.set([rgb[0] * s, rgb[1] * s, rgb[2] * s], k * 3); }
    gl.bindVertexArray(v);
    attr('aPos', new Float32Array(points), 3, gl.FLOAT, false);
    attr('aCol', cols, 3, gl.UNSIGNED_BYTE, true);
    attr('aPick', none, 1, gl.UNSIGNED_SHORT, false);
    return {vao: v, count: n};
  }
  var pinPts = [], w = 0.32, corner = [[-w, -w], [w, -w], [w, w], [-w, w]];
  for (var k = 0; k < 4; k++) {                    // a point pushed into the top of what it marks, four faces and a lid
    var a = corner[k], b = corner[(k + 1) % 4];
    pinPts.push(0, 0, 0, a[0], 1, a[1], b[0], 1, b[1]);
  }
  pinPts.push(-w, 1, -w, w, 1, -w, w, 1, w, -w, 1, -w, w, 1, w, -w, 1, w);
  var ringPts = [], seg = 48;
  for (var k = 0; k < seg; k++) {                 // a flat band round a unit circle
    var t0 = k / seg * 2 * Math.PI, t1 = (k + 1) / seg * 2 * Math.PI, i0 = 0.86, o0 = 1;
    var p = [Math.cos(t0), Math.sin(t0), Math.cos(t1), Math.sin(t1)];
    ringPts.push(p[0] * i0, 0, p[1] * i0, p[0] * o0, 0, p[1] * o0, p[2] * o0, 0, p[3] * o0,
                 p[0] * i0, 0, p[1] * i0, p[2] * o0, 0, p[3] * o0, p[2] * i0, 0, p[3] * i0);
  }
  var PIN = shape(pinPts, [225, 29, 72]), RING = shape(ringPts, [225, 29, 72]);

  // --- camera: turning round a point on the floor ---------------------------------------------------------------
  var box = D.box, cx = (box[0] + box[2]) / 2, cz = (box[1] + box[3]) / 2,
      span = Math.max(box[2] - box[0], box[3] - box[1], 1);
  var home = {theta: -0.65, phi: 0.72, dist: span * 1.25, t: [cx, 0.4, cz]};
  var cam = JSON.parse(JSON.stringify(home));
  function persp(fov, a, n, f) { var t = 1 / Math.tan(fov / 2); return [t / a, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) / (n - f), -1, 0, 0, 2 * f * n / (n - f), 0]; }
  function mul(a, b) { var o = new Array(16); for (var c = 0; c < 4; c++) for (var r = 0; r < 4; r++) { var s = 0; for (var k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; }
  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function norm(a) { var l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function eye() {
    return [cam.t[0] + cam.dist * Math.cos(cam.phi) * Math.sin(cam.theta), cam.t[1] + cam.dist * Math.sin(cam.phi),
            cam.t[2] + cam.dist * Math.cos(cam.phi) * Math.cos(cam.theta)];
  }
  function lookAt(e, t) {
    var z = norm(sub(e, t)), x = norm(cross([0, 1, 0], z)), y = cross(z, x);
    return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1];
  }

  // --- drawing ----------------------------------------------------------------------------------------------------
  var show = {walls: true, zones: true, focus: true}, picked = 0;
  var pickFb = null, pickTex = null, pickDepth = null, pw = 0, ph = 0, born = performance.now();
  function size() {
    var r = window.devicePixelRatio || 1, w = Math.round(cv.clientWidth * r), h = Math.round(cv.clientHeight * r);
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
  }
  function range(layer) { var r = D.ranges[layer]; if (r[1]) gl.drawElements(gl.TRIANGLES, r[1], gl.UNSIGNED_INT, r[0] * 4); }
  function set(focus, alpha) { gl.uniform1i(U.uFocus, focus); gl.uniform1f(U.uAlpha, alpha); }
  function place(x, y, z, s) { gl.uniform3f(U.uShift, x, y, z); gl.uniform1f(U.uScale, s); }
  function blend(on) {
    if (on) { gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false); }
    else { gl.disable(gl.BLEND); gl.depthMask(true); }
  }
  function draw(mode) {
    size();
    gl.viewport(0, 0, cv.width, cv.height);
    var mvp = mul(persp(0.8, cv.width / cv.height, cam.dist * 0.02, cam.dist * 8 + span * 4), lookAt(eye(), cam.t));
    var secs = (performance.now() - born) / 1000, o = D.objects[picked];
    gl.uniformMatrix4fv(U.uMVP, false, mvp);
    gl.uniform1i(U.uMode, mode); gl.uniform1f(U.uPicked, picked);
    gl.uniform1f(U.uPulse, 0.5 + 0.5 * Math.sin(secs * Math.PI / 0.45));   // flashing, as fast as the 2D mark
    gl.bindVertexArray(vao); place(0, 0, 0, 1); set(0, 1);
    gl.clearColor(mode ? 0 : 0.933, mode ? 0 : 0.945, mode ? 0 : 0.957, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST); blend(false);
    range('floor');
    if (mode === 1 || !o || !show.focus) {
      if (show.walls) range('walls');
      range('things');
      if (mode === 0 && show.zones) { blend(true); set(0, 0.45); range('zones'); blend(false); }
    } else {                                       // the selected thing solid, and everything else a faint ghost
      set(1, 1); range('things');
      blend(true);
      if (show.zones) { set(1, 0.5); range('zones'); }   // ...keeping its own clear zone
      set(2, 0.13); if (show.walls) range('walls'); range('things');
      blend(false); set(0, 1);
    }
    if (mode === 1 || !o) return;
    var ring = (secs % 1.4) / 1.4, r = Math.max(o.r, 0.15);
    blend(true); set(0, 0.9 * (1 - ring));         // a ring spreading out from its top, and fading
    gl.bindVertexArray(RING.vao); place(o.c[0], o.top + 0.005, o.c[2], r * (0.7 + 1.3 * ring));
    gl.drawArrays(gl.TRIANGLES, 0, RING.count);
    blend(false); set(0, 1); gl.disable(gl.DEPTH_TEST);   // and the pin, bobbing above it, in front of everything
    var tall = Math.max(0.28, Math.min(0.6, span * 0.05));
    gl.bindVertexArray(PIN.vao); place(o.c[0], o.top + 0.06 + tall * 0.25 * (0.5 + 0.5 * Math.sin(secs * Math.PI / 0.9)), o.c[2], tall);
    gl.drawArrays(gl.TRIANGLES, 0, PIN.count);
    gl.enable(gl.DEPTH_TEST); gl.bindVertexArray(vao); place(0, 0, 0, 1);
  }
  var queued = false, running = false;
  function loop() {                                // keeps going while something is selected: it moves
    if (!picked) { running = false; draw(0); return; }
    draw(0); requestAnimationFrame(loop);
  }
  function redraw() {
    if (running) return;
    if (picked) { running = true; requestAnimationFrame(loop); return; }
    if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; draw(0); }); }
  }

  function pickAt(px, py) {           // draw each thing in its own number, and read back the one under the pointer
    size();
    if (!pickFb || pw !== cv.width || ph !== cv.height) {
      pw = cv.width; ph = cv.height;
      pickFb = pickFb || gl.createFramebuffer(); pickTex = pickTex || gl.createTexture(); pickDepth = pickDepth || gl.createRenderbuffer();
      gl.bindTexture(gl.TEXTURE_2D, pickTex); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, pw, ph, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.bindRenderbuffer(gl.RENDERBUFFER, pickDepth); gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT24, pw, ph);
      gl.bindFramebuffer(gl.FRAMEBUFFER, pickFb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, pickTex, 0);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, pickDepth);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, pickFb);
    draw(1);
    var r = window.devicePixelRatio || 1, out = new Uint8Array(4);
    gl.readPixels(Math.round(px * r), Math.round(cv.height - py * r), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, out);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return out[0] + out[1] * 256;
  }

  // --- what was clicked -------------------------------------------------------------------------------------------
  var info = document.getElementById('v3d-info');
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]; }); }
  function select(n, fly) {
    picked = n;
    var o = D.objects[n];
    if (!o) {
      picked = 0; info.hidden = true;
      if (location.hash) history.replaceState(null, '', location.pathname + location.search);
      redraw(); return;
    }
    info.innerHTML = '<button class="x" aria-label="Clear the selection">×</button>' +
      '<strong>' + esc(o.id) + '</strong> ' + esc(o.name) + '<div class="cat">' + esc(o.cat) + '</div>' +
      (o.find.length ? '<ul>' + o.find.map(function (f) { return '<li class="' + (o.bad ? 'bad' : '') + '">' + esc(f) + '</li>'; }).join('') + '</ul>' : '') +
      '<p><a href="' + esc(o.href) + '">Open its page →</a></p>';
    info.hidden = false;
    info.querySelector('.x').addEventListener('click', function () { select(0); });
    if (fly) {                                     // from well above, so a column or a tall cupboard is less in the way
      cam.t = [o.c[0], Math.max(0.2, o.c[1]), o.c[2]]; cam.dist = Math.max(1.8, span * 0.5); cam.phi = Math.max(cam.phi, 1.05);
    }
    if (location.hash !== '#' + o.id) history.replaceState(null, '', '#' + o.id);
    redraw();
  }

  // --- turning, moving, zooming: mouse, pen and touch -------------------------------------------------------------
  var ptrs = {}, start = null, moved = 0;
  function pan(dx, dy) {
    var k = cam.dist / cv.clientHeight * 1.1, s = Math.sin(cam.theta), c = Math.cos(cam.theta);
    cam.t[0] += (-dx * c - dy * s) * k; cam.t[2] += (dx * s - dy * c) * k;
  }
  cv.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  cv.addEventListener('pointerdown', function (e) {
    cv.setPointerCapture(e.pointerId);
    ptrs[e.pointerId] = {x: e.clientX, y: e.clientY, pan: e.button === 2 || e.shiftKey};
    start = {x: e.clientX, y: e.clientY, t: Date.now()}; moved = 0;
  });
  cv.addEventListener('pointermove', function (e) {
    var p = ptrs[e.pointerId]; if (!p) return;
    var dx = e.clientX - p.x, dy = e.clientY - p.y, ids = Object.keys(ptrs);
    moved += Math.abs(dx) + Math.abs(dy);
    if (ids.length === 2) {                        // two fingers: pinch to zoom, and move together to pan
      var o = ptrs[ids[0] == e.pointerId ? ids[1] : ids[0]];
      var before = Math.hypot(p.x - o.x, p.y - o.y), after = Math.hypot(e.clientX - o.x, e.clientY - o.y);
      if (before > 0 && after > 0) cam.dist = Math.min(span * 6, Math.max(0.5, cam.dist * before / after));
      pan(dx / 2, dy / 2);
    } else if (p.pan) {
      pan(dx, dy);
    } else {
      cam.theta -= dx * 0.008; cam.phi = Math.min(1.5, Math.max(0.05, cam.phi + dy * 0.008));
    }
    p.x = e.clientX; p.y = e.clientY;
    redraw();
  });
  function up(e) {
    if (ptrs[e.pointerId] && moved < 6 && start && Date.now() - start.t < 600 && Object.keys(ptrs).length === 1) {
      var r = cv.getBoundingClientRect();
      select(pickAt(e.clientX - r.left, e.clientY - r.top), false);
    }
    delete ptrs[e.pointerId];
  }
  cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', function (e) { delete ptrs[e.pointerId]; });
  cv.addEventListener('wheel', function (e) {
    e.preventDefault(); cam.dist = Math.min(span * 6, Math.max(0.5, cam.dist * Math.exp(e.deltaY * 0.0012))); redraw();
  }, {passive: false});

  document.querySelectorAll('.v3d-bar button[data-layer]').forEach(function (b) {
    b.addEventListener('click', function () { show[b.dataset.layer] = !show[b.dataset.layer]; b.classList.toggle('on'); redraw(); });
  });
  document.getElementById('v3d-reset').addEventListener('click', function () { cam = JSON.parse(JSON.stringify(home)); select(0); });
  window.addEventListener('resize', redraw);

  var wanted = decodeURIComponent(location.hash.slice(1));
  var found = D.objects.findIndex(function (o) { return o && o.id === wanted; });
  if (found > 0) select(found, true); else redraw();
})();
"""
