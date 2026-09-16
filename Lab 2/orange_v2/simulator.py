"""Loopback-only browser simulator serving the exact Pillow hardware frames."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import json
import time

from .render import render


PAGE = b'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Orange v2 local simulator</title>
<style>
body{background:#eeeae1;color:#25312f;font:16px system-ui;margin:40px auto;max-width:760px;padding:0 20px}
h1{font-size:25px} .device{display:flex;align-items:center;gap:20px;margin:30px 0}
img{width:min(65vw,480px);height:auto;image-rendering:pixelated;border:12px solid #202628;border-radius:8px}
.keys{display:flex;flex-direction:column;gap:28px}button{font:inherit;padding:16px 20px;border-radius:50%;
border:2px solid #596760;background:#faf9f4;touch-action:none;user-select:none}
button.down{background:#ffb85a}p{line-height:1.6}small{color:#53665e}
</style>
<h1>Orange v2 / local simulator</h1>
<div class="device"><div class="keys"><button id="A">A</button><button id="B">B</button></div>
<img id="screen" width="480" height="270" alt="Orange 240 by 135 screen"></div>
<p>Tap A to start washing; tap B to start drying. While running, hold the same button
for two real seconds to cancel. When ready, collect the clothes and tap the same button.</p>
<p>Hold your keyboard's A and B together to test a chord. Mouse/touch presses also work.
Release all buttons between actions. Idle long presses do nothing.</p>
<small id="status">Connecting...</small>
<p><small>The screen above is the actual renderer. This page does not access GPIO or a
laundry machine. Use one simulator tab. Ctrl+C in the terminal stops the server.</small></p>
<script>
const keys = new Set(), pointers = new Map(), pressTokens = new Map();
let queue = Promise.resolve(), stopped = false;
// Browser clicks may deliver down/up in one tick. Give a desktop tap a small
// stable interval so it can pass the same 30 ms debounce used by the hardware.
// Long holds keep their original duration; cancellation invalidates late releases.
function beginPress(token, down){const stamp={at:performance.now()};
  pressTokens.set(token,stamp);down();send();}
function endPress(token, up){const stamp=pressTokens.get(token);if(!stamp)return;
  setTimeout(()=>{if(pressTokens.get(token)!==stamp)return;
    pressTokens.delete(token);up();send();},Math.max(0,80-(performance.now()-stamp.at)));}
function pressed(){return [...new Set([...keys,...pointers.values()])].sort()}
function send(reset=false){const value=reset?[]:pressed();
  for(const id of ['A','B'])document.getElementById(id).classList.toggle('down',value.includes(id));
  queue=queue.then(()=>fetch(reset?'/reset':'/buttons',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(value)})).catch(()=>{});}
for(const id of ['A','B']){const b=document.getElementById(id);
  b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);
    beginPress('p'+e.pointerId,()=>pointers.set(e.pointerId,id))};
  b.onpointerup=e=>endPress('p'+e.pointerId,()=>pointers.delete(e.pointerId));
  b.onpointercancel=()=>reset(); b.oncontextmenu=e=>e.preventDefault();
  // Keyboard/assistive activation has no pointer edges; synthesize one short
  // debounced tap. Physical pointer holds keep their actual down/up timing.
  b.onclick=e=>{if(e.detail===0){keys.add(id);send();setTimeout(()=>{keys.delete(id);send()},100)}};}
window.onkeydown=e=>{const k=e.key.toUpperCase();if(['A','B'].includes(k)){
  e.preventDefault();if(!e.repeat)beginPress('k'+k,()=>keys.add(k))}};
window.onkeyup=e=>{const k=e.key.toUpperCase();if(keys.has(k)){
  e.preventDefault();endPress('k'+k,()=>keys.delete(k))}};
function reset(){pressTokens.clear();keys.clear();pointers.clear();send(true)}
window.onblur=reset;document.onvisibilitychange=()=>{if(document.hidden)reset()};
async function frame(){if(stopped)return;try{
  const response=await fetch('/frame',{cache:'no-store'});if(!response.ok)throw Error('frame');
  const url=URL.createObjectURL(await response.blob()), img=document.getElementById('screen');
  const old=img.src;img.src=url;if(old.startsWith('blob:'))URL.revokeObjectURL(old);
  document.getElementById('status').textContent='Connected / speed '+response.headers.get('X-Speed')+
    'x / holds and breathing use real seconds';
}catch(e){document.getElementById('status').textContent='Disconnected. Restart the server and reload.';
  stopped=true;}setTimeout(frame,80)}frame();
</script></html>'''


def run(timer, port=8765):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, body=b"", content_type="text/plain"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Speed", str(timer.config.speed))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.reply(200, PAGE, "text/html; charset=utf-8")
            elif self.path == "/frame":
                server.last_contact = time.monotonic()
                view = timer.step(server.last_contact, server.pressed)
                output = BytesIO()
                render(view).save(output, format="PNG")
                self.reply(200, output.getvalue(), "image/png")
            else:
                self.reply(404)

        def do_POST(self):
            if self.path not in ("/buttons", "/reset"):
                self.reply(404)
                return
            if self.headers.get("Content-Type") != "application/json":
                self.reply(415)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 64:
                    raise ValueError("Invalid length")
                values = json.loads(self.rfile.read(length))
                if not isinstance(values, list) or any(v not in ("A", "B") for v in values):
                    raise ValueError("Expected A and/or B")
            except (ValueError, TypeError):
                self.reply(400)
                return
            if self.path == "/reset":
                server.release_without_action()
            else:
                server.pressed = set(values)
            server.last_contact = time.monotonic()
            timer.step(server.last_contact, server.pressed)
            self.reply(204)

    class Server(HTTPServer):
        def get_request(self):
            sock, address = super().get_request()
            sock.settimeout(0.5)
            return sock, address

        def release_without_action(self):
            if timer.gesture:
                timer.gesture.invalid = True
            self.pressed = set()

    with Server(("127.0.0.1", port), Handler) as server:
        server.pressed = set()
        server.last_contact = time.monotonic()
        server.timeout = 0.005
        print(f"Open http://127.0.0.1:{server.server_port}/ (Ctrl+C to stop)", flush=True)
        print(f"Laundry time: {timer.config.speed:g}x; holds: 2 real seconds", flush=True)
        while True:
            now = time.monotonic()
            if now - server.last_contact > 1.0:
                server.release_without_action()
            timer.step(now, server.pressed)
            server.handle_request()
