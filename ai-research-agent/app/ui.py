from __future__ import annotations

import json
from pathlib import Path

from fastapi.responses import HTMLResponse


def render_ui() -> HTMLResponse:
    demo_qs = json.loads(Path("data/demo_questions.json").read_text(encoding="utf-8"))
    options = "".join([f'<option value="{q}">{q}</option>' for q in demo_qs])
    html = f"""
<!doctype html><html><head><meta charset='utf-8'><title>AI Research Agent Demo</title>
<style>body{{font-family:Arial;max-width:1100px;margin:20px auto;padding:0 16px}} textarea,input,select{{width:100%;margin:6px 0;padding:8px}} button{{padding:8px 14px}} #logs{{background:#111;color:#0f0;height:180px;overflow:auto;padding:8px;font-family:monospace}} table{{width:100%;border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:6px}}</style></head>
<body><h1>AI Research Agent (Demo)</h1>
<select id='demo'><option value=''>Demo questions</option>{options}</select>
<textarea id='question' rows='4' placeholder='Enter research question'></textarea>
<input id='region' placeholder='Region (optional)'><input id='time' placeholder='Time window (optional)'><input id='reading' placeholder='Reading level (optional)'>
<textarea id='urls' rows='3' placeholder='Optional URLs, one per line'></textarea>
<button onclick='run()'>Run</button> <span id='runid'></span>
<progress id='prog' max='100' value='0' style='width:100%'></progress>
<div id='logs'></div><div id='report'></div><h3>Evidence</h3><table id='evidence'></table><h3>Sources</h3><ul id='sources'></ul>
<input id='followup' placeholder='Ask follow-up'><button onclick='followup()'>Send follow-up</button>
<script>
let runId = null;
document.getElementById('demo').addEventListener('change',e=>{{if(e.target.value)document.getElementById('question').value=e.target.value}})
async function run(){{
 const body={{question:question.value,constraints:{{region:region.value,time_window:time.value,reading_level:reading.value}},urls:urls.value.split('\n').filter(Boolean)}};
 let r=await fetch('/api/research/run',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}}); let j=await r.json(); runId=j.run_id; runid.textContent=runId;
 await fetch(`/api/research/${{runId}}/start`,{{method:'POST'}}); poll();
}}
async function poll(){{
 let timer=setInterval(async()=>{{
  let s=await (await fetch(`/api/research/${{runId}}/status`)).json(); prog.value=s.progress; logs.textContent=s.logs.map(l=>`${{l.ts}} [${{l.level}}] ${{l.step}} ${{l.message}}`).join('\n');
  if(s.progress>=100){{clearInterval(timer); let out=await (await fetch(`/api/research/${{runId}}`)).json(); render(out); }}
 },1200);
}}
function render(out){{ report.innerHTML=out.report_md.replace(/\n/g,'<br>'); evidence.innerHTML='<tr><th>Claim</th><th>Sources</th><th>Confidence</th><th>Counterpoints</th></tr>'+out.evidence_table.sort((a,b)=>b.confidence-a.confidence).map(r=>`<tr><td>${{r.claim}}</td><td>${{r.source_tags.join(',')}}</td><td>${{r.confidence}}</td><td>${{r.counterpoints}}</td></tr>`).join(''); sources.innerHTML=out.sources.map(s=>`<li>[${{s.tag}}] ${{s.title||'Untitled'}} — <a href='${{s.url}}' target='_blank'>${{s.url}}</a> — ${{s.published_at||'unknown'}} — ${{s.fetched_at||'n/a'}}</li>`).join(''); }
async function followup(){{ if(!runId) return; await fetch(`/api/research/${{runId}}/followup`,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{question:document.getElementById('followup').value}})}}); poll(); }
</script></body></html>"""
    return HTMLResponse(html)
