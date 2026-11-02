import subprocess,re,glob,os,json,html,statistics,shutil,zipfile
ROOT='/mnt/data/rw_work'
files={
 'information-ideas':'/mnt/data/Information & Ideas Difficult Questions.pdf',
 'craft-structure':'/mnt/data/Craft & Structure Difficult Questions.pdf',
 'expression-ideas':'/mnt/data/Expression of Ideas Difficult Questions.pdf',
 'expression-ideas-psat':'/mnt/data/Expression of Ideas Difficult Questions 2.pdf',
 'standard-conventions':'/mnt/data/Standard English Conventions Difficult Questions.pdf',
}
names={'information-ideas':'Information and Ideas','craft-structure':'Craft and Structure','expression-ideas':'Expression of Ideas','standard-conventions':'Standard English Conventions'}

def clean(s):
    s=s.replace('\x0c',' ').replace('\u00a0',' ')
    s=re.sub(r'[ \t]+',' ',s)
    s=re.sub(r' *\n *','\n',s)
    s=re.sub(r'\n{3,}','\n\n',s)
    return s.strip()

def parse_file(path, domain, psat=False):
    t=subprocess.check_output(['pdftotext','-layout',path,'-'],text=True,errors='replace')
    blocks=[b for b in re.split(r'(?=Question ID:)',t) if 'Question ID:' in b]
    out=[]
    for idx,b in enumerate(blocks):
        mq=re.search(r'(?m)^[ \t]*Question[ \t]*$',b); ma=re.search(r'(?m)^[ \t]*Answer[ \t]*$',b); qpos=mq.start() if mq else -1; apos=ma.start() if ma else -1; cpos=b.find('Correct Answer:'); rpos=b.find('Rationale',cpos if cpos>=0 else 0)
        if min(qpos,apos,cpos,rpos)<0 or not(qpos<apos<cpos<rpos):
            continue
        qtxt=clean(b[mq.end():apos])
        atxt=b[ma.end():cpos]
        corrm=re.search(r'Correct Answer:\s*([A-D])\b',b[cpos:cpos+100])
        if not corrm: continue
        correct=corrm.group(1)
        rat=clean(b[rpos+len('Rationale'):])
        # Strip page furniture accidentally included after rationale (normally block ends at next question)
        rat=re.sub(r'\n?\s*<PARSED TEXT FOR PAGE:.*$','',rat,flags=re.S)
        # parse answer options with line-start markers; retain wrapped continuation lines
        lines=atxt.splitlines(); opts=[]; cur=None
        for line in lines:
            m=re.match(r'^\s{0,24}([A-D])\.\s*(.*\S)?\s*$',line)
            if m:
                if cur: opts.append(cur)
                cur={'letter':m.group(1),'text':(m.group(2) or '').strip()}
            elif cur and line.strip():
                cur['text'] += ' ' + line.strip()
        if cur: opts.append(cur)
        # Keep only a complete four-choice question, skip parse failures instead of fabricating options.
        opts=[{'letter':o['letter'],'text':clean(o['text'])} for o in opts if o['text']]
        if len(opts)!=4 or [o['letter'] for o in opts] != ['A','B','C','D']:
            # fallback: regex captures options even when layout wraps labels
            matches=list(re.finditer(r'(?m)^\s*([A-D])\.\s+',atxt))
            if len(matches)>=4:
                opts=[]
                for j,m in enumerate(matches[:4]):
                    end=matches[j+1].start() if j+1<4 else len(atxt)
                    opts.append({'letter':m.group(1),'text':clean(atxt[m.end():end])})
        if len(opts)!=4: continue
        # Get skill from metadata table row where possible
        pre=b[:qpos]
        skill='Reading and Writing'
        for ln in pre.splitlines():
            if 'Reading and Writing' in ln and ('Difficulty' in ln or 'Hard' in ln):
                # remove standard table labels / Assessment Test Domain Skill Difficulty
                ln=re.sub(r'Assessment|Test|Domain|Skill|Difficulty|SAT|PSAT/NMSQT and PSAT|Reading and Writing|Hard',' ',ln)
                skill=clean(ln) or 'Reading and Writing'; skill=re.sub(r'(?i)'+re.escape({'information-ideas':'Information and Ideas','craft-structure':'Craft and Structure','expression-ideas':'Expression of Ideas','standard-conventions':'Standard English Conventions'}[domain]),' ',skill); skill=re.sub(r'\s+',' ',skill).strip() or 'Reading and Writing'
        # Question metadata should never reach student display; source IDs kept only for internal uniqueness.
        idm=re.search(r'Question ID:\s*([0-9a-f]+)',b)
        out.append({'id':(idm.group(1) if idm else f'{domain}-{idx}')+('-psat' if psat else ''), 'domain':domain,'skill':skill,'question':qtxt,'options':opts,'answer':correct,'rationale':rat,'source':'PSAT' if psat else 'SAT','source_order':idx})
    return out

banks={k:[] for k in names}
banks['information-ideas']=parse_file(files['information-ideas'],'information-ideas')
banks['craft-structure']=parse_file(files['craft-structure'],'craft-structure')
banks['expression-ideas']=parse_file(files['expression-ideas'],'expression-ideas')+parse_file(files['expression-ideas-psat'],'expression-ideas',True)
banks['standard-conventions']=parse_file(files['standard-conventions'],'standard-conventions')
for k,v in banks.items():
    print(k, len(v), 'sample skill', v[0]['skill'] if v else None, 'question',v[0]['question'][:80] if v else None, 'opts',len(v[0]['options']) if v else 0,'rat',len(v[0]['rationale']) if v else 0)
    if not v: raise RuntimeError('No questions parsed: '+k)
# Assign tiers using relative complexity across each domain. Length, reasoning/rhetorical indicators, choice length and rationale complexity are proxies.
# PSAT receives a small downward adjustment when comparing otherwise similar Expression of Ideas questions.
for k,arr in banks.items():
    for q in arr:
        text=q['question']; opts=' '.join(o['text'] for o in q['options']); rat=q['rationale']
        score=0
        score += min(len(text),1800)/1800*2.0
        score += min(len(opts),1800)/1800*1.3
        score += min(len(rat),3000)/3000*1.0
        score += 0.12*len(re.findall(r'\b(although|whereas|however|nevertheless|in contrast|most strongly|best explains|infer|implies|suggests|relationship|undermine|qualify|synthesize|counterargument|nuance|implication|assumption|conclusion)\b',text+' '+rat,re.I))
        # Longer stems with tables, paired texts, and complex grammar often demand more operations.
        score += 0.22*len(re.findall(r'\b(Text 1|Text 2|Table|graph|data|experiment|study|researchers|theory|hypothesis|rhetorical|conventions|transition|modifier|semicolon|colon|punctuation)\b',text,re.I))
        if q['source']=='PSAT': score -= 0.35
        q['_complexity']=score
    arr.sort(key=lambda q:q['_complexity'])
    n=len(arr)
    # Balanced relative tiers with slight overlap by rank only; preserve exact question content.
    for i,q in enumerate(arr):
        pct=(i+0.5)/n
        if pct<1/3: q['level']=1; q['difficulty']='Hard'
        elif pct<2/3: q['level']=2; q['difficulty']='Very Hard'
        else: q['level']=3; q['difficulty']='Expert'
        q['subdomain']=q['skill']
        del q['_complexity']
    # Shuffle bank order deterministic by source/domain/ID, so students aren't presented easiest to hardest.
    arr.sort(key=lambda q: (q['source'], q['source_order'], q['id']))

# Create per-domain standalone pages using a shared engine. Questions are HTML text; escaping preserves source content safely.
engine=r'''<script>
const BANK=__BANK__;
const DOMAIN_NAME=__DOMAIN__;
const TOTAL=30, MAX_SCORE=89, LEVEL_POINTS={1:1,2:2,3:3}, LEVEL_NAMES={1:'Hard',2:'Very Hard',3:'Expert'};
const $=id=>document.getElementById(id);
let used=new Set(),testQuestions=[],current=0,selected=null,answers=[];
function escapeHtml(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function randomItem(a){return a[Math.floor(Math.random()*a.length)]}
function chooseQuestion(level){let c=BANK.filter(q=>q.level===level&&!used.has(q.id));if(!c.length){for(let d=1;d<=2&&!c.length;d++){for(const l of [level-d,level+d].filter(x=>x>=1&&x<=3)){c=BANK.filter(q=>q.level===l&&!used.has(q.id));if(c.length)break}}}if(!c.length)return null;const q=randomItem(c);used.add(q.id);return q}
function renderQuestion(){selected=null;const q=testQuestions[current];$('question-counter').textContent=`Question ${current+1} of ${TOTAL}`;$('difficulty-pill').textContent=`${LEVEL_NAMES[q.level]} · ${LEVEL_POINTS[q.level]} point${q.level===1?'':'s'}`;$('subdomain-label').textContent='';$('progress-fill').style.width=`${current/TOTAL*100}%`;
$('question-content').innerHTML=`<div class="question-text">${escapeHtml(q.question).replace(/\n/g,'<br>')}</div>`;
const area=$('answer-area');area.innerHTML='';const wrap=document.createElement('div');wrap.className='choices';q.options.forEach(o=>{const b=document.createElement('button');b.type='button';b.className='choice';b.innerHTML=`<span class="letter">${o.letter}</span><span>${escapeHtml(o.text)}</span>`;b.onclick=()=>{selected=o.letter;wrap.querySelectorAll('.choice').forEach(x=>x.classList.remove('selected'));b.classList.add('selected');$('next-btn').disabled=false;$('answer-hint').textContent='Answer selected.'};wrap.appendChild(b)});area.appendChild(wrap);$('next-btn').textContent=current===TOTAL-1?'Finish test':'Submit answer';$('next-btn').disabled=true;$('answer-hint').textContent='Select one answer to continue.'}
function submitAnswer(){const q=testQuestions[current];if(selected===null)return;const correct=String(selected).toUpperCase()===String(q.answer).toUpperCase();answers.push({question:q,response:selected,correct,points:correct?LEVEL_POINTS[q.level]:0});if(current===TOTAL-1){showResults();return}const level=correct?Math.min(3,q.level+1):Math.max(1,q.level-1);const next=chooseQuestion(level);if(!next){showResults();return}testQuestions.push(next);current++;renderQuestion();window.scrollTo({top:0,behavior:'smooth'})}
function table(headers,rows){return `<table><thead><tr>${headers.map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`}
function showResults(){ $('test-screen').classList.add('hidden');$('results').classList.remove('hidden');$('progress-fill').style.width='100%';const raw=answers.reduce((s,a)=>s+a.points,0),totalPoints=Math.min(MAX_SCORE,raw),correctCount=answers.filter(a=>a.correct).length;const pct=(100*totalPoints/MAX_SCORE).toFixed(1);$('overall-stats').innerHTML=`<div class="stat"><span class="muted">Total points</span><strong>${totalPoints} / ${MAX_SCORE}</strong></div><div class="stat"><span class="muted">Available points earned</span><strong>${pct}%</strong></div><div class="stat"><span class="muted">Questions correct</span><strong>${correctCount} / ${answers.length}</strong></div><div class="stat"><span class="muted">Questions completed</span><strong>${answers.length} / ${TOTAL}</strong></div>`;
$('difficulty-table').innerHTML=table(['Difficulty','Attempted','Correct','Accuracy','Points earned'],[1,2,3].map(l=>{const a=answers.filter(x=>x.question.level===l),c=a.filter(x=>x.correct).length;return [LEVEL_NAMES[l],a.length,c,a.length?(100*c/a.length).toFixed(1)+'%':'—',a.reduce((s,x)=>s+x.points,0)]}));
const subs=[...new Set(BANK.map(q=>q.subdomain))];const perf=subs.map(s=>{const a=answers.filter(x=>x.question.subdomain===s);return {s,n:a.length,c:a.filter(x=>x.correct).length,p:a.length?a.filter(x=>x.correct).length/a.length:1}}).filter(x=>x.n).sort((a,b)=>a.p-b.p);let rec=[];if(perf.length&&perf[0].p<.8)rec.push(`Prioritize review of ${perf[0].s}, your lowest-accuracy skill in this test.`);if(correctCount/answers.length>=.8)rec.push('You showed strong overall accuracy. Review any missed questions and continue practicing more challenging applications.');if(!rec.length)rec.push('Review missed questions and their explanations, focusing on the skills where you lost points.');$('recommendations').innerHTML='<ul>'+rec.map(x=>`<li>${escapeHtml(x)}</li>`).join('')+'</ul>';
$('review-list').innerHTML=answers.map((a,i)=>`<article class="review"><h3>Question ${i+1} of ${TOTAL} · ${LEVEL_NAMES[a.question.level]}</h3><div class="review-question">${escapeHtml(a.question.question).replace(/\n/g,'<br>')}<div class="review-options">${a.question.options.map(o=>`<div class="review-option ${o.letter===a.question.answer?'correct-option':''}"><b>${o.letter}.</b> ${escapeHtml(o.text)}${o.letter===a.question.answer?' <strong>(Correct answer)</strong>':''}</div>`).join('')}</div></div><p><strong>Your answer:</strong> ${a.response} &nbsp; <span class="${a.correct?'correct':'incorrect'}">${a.correct?'Correct':'Incorrect'}</span></p><p><strong>Points earned:</strong> ${a.points} / ${LEVEL_POINTS[a.question.level]}</p><h4>Answer explanation</h4><div class="explanation">${escapeHtml(a.question.rationale).replace(/\n/g,'<br>')}</div></article>`).join('');window.scrollTo({top:0,behavior:'smooth'})}
function startTest(){try{if(BANK.length<TOTAL)throw new Error(`Only ${BANK.length} questions loaded; at least ${TOTAL} are required.`);used=new Set();testQuestions=[];answers=[];current=0;const first=chooseQuestion(2);if(!first)throw new Error('No Very Hard questions were available.');testQuestions.push(first);$('intro').classList.add('hidden');$('results').classList.add('hidden');$('test-screen').classList.remove('hidden');renderQuestion();window.scrollTo({top:0,behavior:'smooth'})}catch(e){$('start-error').textContent='The test could not start: '+e.message;$('start-error').classList.remove('hidden')}}
$('start-btn').addEventListener('click',startTest);$('next-btn').addEventListener('click',submitAnswer);$('print-btn').addEventListener('click',()=>window.print());$('retake-btn').addEventListener('click',()=>{$('results').classList.add('hidden');$('test-screen').classList.add('hidden');$('intro').classList.remove('hidden');window.scrollTo({top:0,behavior:'smooth'})});
$('main-menu-btn').addEventListener('click',e=>{e.preventDefault();if(confirm('Are you sure you want to return to the main page? Your current test progress will be lost.'))window.location.href='../index.html'});
$('header-main-menu-btn').addEventListener('click',e=>{e.preventDefault();if(confirm('Are you sure you want to return to the main page? Your current test progress will be lost.'))window.location.href='../index.html'});
</script>'''
css=r'''<style>
:root{--navy:#173052;--blue:#176ca9;--ink:#24364b;--line:#d5dfeb;--muted:#64748b;--pale:#edf6ff;--green:#167344;--red:#a12222}*{box-sizing:border-box}body{margin:0;background:#f4f7fa;color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}.shell{max-width:1000px;margin:0 auto;padding:24px 18px 60px}.site-header{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:14px}.brand{color:var(--navy);font-weight:800;letter-spacing:.04em;font-size:.85rem;text-transform:uppercase}.hero{background:white;border:1px solid var(--line);border-radius:18px;padding:clamp(22px,4vw,42px);margin-top:12px;box-shadow:0 8px 26px #132b4a0b}.hero h1{font-size:clamp(1.8rem,4vw,2.7rem);line-height:1.15;margin:8px 0 14px;color:var(--navy)}h2,h3,h4{color:var(--navy)}.lead{font-size:1.08rem;color:#435166;max-width:760px}.btn{border:0;border-radius:10px;background:var(--blue);color:#fff;font-weight:700;font-size:1rem;padding:13px 20px;cursor:pointer}.btn.secondary{background:white;color:var(--navy);border:1px solid var(--line)}.btn:disabled{opacity:.5;cursor:not-allowed}.main-menu-link{text-decoration:none;margin:0;padding:10px 14px;white-space:nowrap}.pill{display:inline-block;background:#e4eef8;color:#164f82;padding:5px 10px;border-radius:999px;font-size:.88rem;font-weight:700}.topline{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:12px}.progress{height:8px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin:12px 0 24px}.progress span{display:block;height:100%;background:var(--blue);width:0;transition:width .2s}.qcard{background:white;border:1px solid var(--line);border-radius:16px;padding:clamp(16px,3vw,30px);box-shadow:0 8px 26px #132b4a0a}.question-text,.review-question{font-size:1.04rem;line-height:1.75;overflow-wrap:anywhere}.question-text{white-space:normal}.choices{display:grid;grid-template-columns:1fr;gap:10px;margin-top:20px}.choice{display:flex;align-items:flex-start;gap:10px;background:#fff;border:2px solid var(--line);border-radius:10px;padding:13px;text-align:left;cursor:pointer;font-size:1rem;line-height:1.5;color:var(--ink)}.choice:hover{border-color:#8ab9e1}.choice.selected{border-color:var(--blue);background:#edf6ff}.choice .letter{display:inline-flex;flex:0 0 30px;align-items:center;justify-content:center;width:30px;height:30px;border-radius:50%;background:#edf1f5;font-weight:800}.qfoot{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-top:24px}.note,.tagline{font-size:.9rem;color:var(--muted)}.error-box{margin-top:14px;padding:12px 14px;background:#fff1f0;border:1px solid #f2b8b5;border-radius:10px;color:#8b1d18}.hidden{display:none!important}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}.stat{background:white;border:1px solid var(--line);border-radius:12px;padding:16px}.stat strong{font-size:1.55rem;color:var(--navy);display:block}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;background:white;margin:12px 0 22px}th,td{padding:10px 12px;border:1px solid var(--line);text-align:left}th{background:var(--pale);color:var(--navy)}.review{background:white;border:1px solid var(--line);border-radius:12px;padding:18px;margin:14px 0;break-inside:avoid;overflow-wrap:anywhere}.review h3{margin-top:0}.review-options{margin:12px 0}.review-option{margin:6px 0;padding:8px 10px;border-radius:8px}.correct-option{background:#edf8f0;border:1px solid #b7e0c2}.correct{color:var(--green);font-weight:800}.incorrect{color:var(--red);font-weight:800}.explanation{white-space:normal;line-height:1.7;overflow-wrap:anywhere;max-width:100%}.print-header{display:none}.no-print{margin:22px 0;display:flex;gap:10px;flex-wrap:wrap}@media(max-width:600px){.shell{padding:14px 10px 36px}.qfoot .btn{width:100%}.choice{font-size:.98rem}}@media print{body{background:white;font-size:11pt}.shell{max-width:none;padding:0}.brand,.no-print,#intro,#test-screen,.site-header{display:none!important}#results{display:block!important}.hero{box-shadow:none;border:0;padding:0}.review{box-shadow:none;border:1px solid #bbb;break-inside:auto}.explanation{overflow:visible;max-height:none}table{font-size:10pt}h1{font-size:24pt}h2,h3{break-after:avoid}.print-header{display:block!important}}
</style>'''
for key,arr in banks.items():
    os.makedirs(os.path.join(ROOT,key),exist_ok=True)
    # Remove source-order internal field and source label stays only internal, not shown.
    for q in arr: q.pop('source_order',None)
    bankjson=json.dumps(arr,ensure_ascii=False,separators=(',',':'))
    name=names[key]
    htmlpage='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>SAT Practice Lab — '''+html.escape(name)+'''</title>'''+css+'''</head><body><main class="shell"><div class="site-header"><div class="brand">SAT Practice Lab · Reading &amp; Writing</div><a class="btn secondary main-menu-link" id="header-main-menu-btn" href="../index.html">← Return to Main Screen</a></div><section id="intro" class="hero"><span class="pill">Adaptive Reading &amp; Writing Practice</span><h1>'''+html.escape(name)+'''</h1><p class="lead">A 30-question adaptive practice test. Questions become more or less challenging based on your answers.</p><p class="note">Hard questions are worth 1 point, Very Hard questions 2 points, and Expert questions 3 points. The maximum score is 89 points.</p><p class="note">Question bank: '''+str(len(arr))+''' questions.</p><button id="start-btn" class="btn" type="button">Start Test</button><div id="start-error" class="error-box hidden" role="alert"></div></section><section id="test-screen" class="hidden"><div class="topline"><span id="question-counter" class="pill">Question 1 of 30</span><span id="difficulty-pill" class="pill">Very Hard · 2 points</span><span id="subdomain-label" class="tagline"></span></div><div class="progress"><span id="progress-fill"></span></div><div class="qcard"><div id="question-content"></div><div id="answer-area"></div><div class="qfoot"><span id="answer-hint" class="note">Choose an answer to continue.</span><button id="next-btn" class="btn" disabled>Submit answer</button></div></div></section><section id="results" class="hidden"><div class="hero"><div class="print-header"><div class="brand">SAT Practice Lab · Reading &amp; Writing</div></div><div class="pill">Assessment complete</div><h1>Your '''+html.escape(name)+''' Results</h1><p class="lead">Review your score, performance by difficulty, and explanations for every question. Your score is a practice measure, not an official SAT score prediction.</p><div id="overall-stats" class="stats"></div><h2>Performance by difficulty</h2><div id="difficulty-table" class="table-wrap"></div><h2>Recommended review priorities</h2><div id="recommendations"></div><div class="no-print"><button id="print-btn" class="btn">Print / Save report as PDF</button><button id="retake-btn" class="btn secondary">Take another test</button><button id="main-menu-btn" class="btn secondary" type="button">Return to Main Screen</button></div></div><div class="hero"><h2>Answer explanations — Questions 1–30</h2><p class="note">Questions and explanations appear in the exact order you answered them, numbered 1 through 30. Explanations are not grouped by subdomain.</p><div id="review-list"></div></div></section></main>'''+engine.replace('__BANK__',bankjson).replace('__DOMAIN__',json.dumps(name,ensure_ascii=False))+'''</body></html>'''
    open(os.path.join(ROOT,key,'index.html'),'w',encoding='utf-8').write(htmlpage)
    print('wrote',key,len(htmlpage), 'levels', {i:sum(q['level']==i for q in arr) for i in (1,2,3)})
