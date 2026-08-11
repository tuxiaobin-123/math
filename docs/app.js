(() => {
  "use strict";
  const D = window.LENS_DATA;
  const KEY = "cumcm-lens-v5-state";
  const titles = {overview:"总览",diagnostic:"能力诊断",training:"训练任务",graph:"知识图谱",lab:"模型实验室",coach:"AI 教练",benchmark:"Benchmark",simulation:"48 小时模拟",team:"团队协作",portfolio:"作品集与内容",contribute:"开放贡献与 API"};
  const defaults = {
    view:"overview", taskFilter:"all", week:1, completed:{}, profile:null,
    simulation:{startedAt:null},
    teamTasks:[
      {id:"t1",title:"完成题面结构表",owner:"建模负责人",status:"todo"},
      {id:"t2",title:"跑通简单基线",owner:"编程负责人",status:"doing"},
      {id:"t3",title:"建立摘要数字核对表",owner:"论文负责人",status:"done"}
    ]
  };
  let state;
  try { state = {...defaults,...JSON.parse(localStorage.getItem(KEY) || "{}")}; } catch { state = {...defaults}; }
  state.completed ||= {}; state.teamTasks ||= defaults.teamTasks;

  const $ = (selector, root=document) => root.querySelector(selector);
  const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];
  const make = (tag, cls, text) => { const node=document.createElement(tag); if(cls) node.className=cls; if(text!==undefined) node.textContent=text; return node; };
  const save = () => {
    localStorage.setItem(KEY, JSON.stringify(state));
    const status = $("#saveStatus"); status.textContent="已自动保存"; status.style.opacity="1";
    setTimeout(() => status.style.opacity=".55",700);
  };
  const toast = (message) => { const node=$("#toast"); node.textContent=message; node.classList.add("show"); setTimeout(()=>node.classList.remove("show"),2200); };
  const download = (name, content, type="application/json") => {
    const url=URL.createObjectURL(new Blob([content],{type})); const a=make("a"); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),500);
  };
  const taskCount = D.weeks.reduce((n,w)=>n+w.tasks.length,0);
  const doneCount = () => Object.values(state.completed).filter(Boolean).length;
  const percent = () => Math.round(doneCount()/taskCount*100);

  function navigate(view) {
    if (!titles[view]) return;
    state.view=view; save();
    $$(".view").forEach(v=>v.classList.toggle("active",v.id===`view-${view}`));
    $$("#nav button").forEach(b=>b.classList.toggle("active",b.dataset.view===view));
    $("#viewTitle").textContent=titles[view];
    $(".sidebar").classList.remove("open"); window.scrollTo({top:0,behavior:"smooth"});
    if(view==="overview") renderOverview();
    if(view==="portfolio") renderPortfolio();
  }

  function renderOverview() {
    const p=percent(); $("#overallProgress").textContent=`${p}%`; $("#overallProgressBar").style.width=`${p}%`;
    const next=D.weeks.flatMap((week)=>week.tasks.map((task,i)=>({id:`w${week.week}-${i}`,week,task}))).find(item=>!state.completed[item.id]);
    $("#nextTask").textContent=next?`下一项：第 ${next.week.week} 周 · ${next.task[0]}`:"训练任务已全部完成，可进入独立复现";
    const stats=[
      ["真实赛题","3 道","数据 / 机理 / 优化"],
      ["训练任务",`${doneCount()} / ${taskCount}`,"每项含产出与评分"],
      ["自动审计","7 类","泄漏、残差、方程、约束等"],
      ["开放接口","5 个","诊断、教练、模型推荐"]
    ];
    const box=$("#overviewStats"); box.replaceChildren(); stats.forEach(([label,value,note])=>{const c=make("article","stat-card"); c.append(make("span","",label),make("strong","",value),make("small","",note)); box.append(c);});
    const versions=$("#versionMap"); versions.replaceChildren(); D.versions.forEach(v=>{const row=make("div","version-row"); row.append(make("strong","",v[0]),make("span","",`${v[1]} · ${v[2]}`),make("small","",v[3])); versions.append(row);});
    const cases=$("#caseCards"); cases.replaceChildren(); D.cases.forEach(c=>{const card=make("article","case-card"); const id=make("span","case-id",`${c.id} · ${c.evidence}`); const h=make("h3","",c.name); const ability=make("p","subtle",c.ability); const metric=make("span","metric",c.metric); const result=make("p","subtle",c.result); const boundary=make("div","boundary",c.boundary); card.append(id,h,ability,metric,result,boundary); cases.append(card);});
  }

  function renderDiagnostic() {
    const box=$("#diagnosticSliders"); box.replaceChildren();
    D.dimensions.forEach(d=>{const row=make("div","slider-row"); const label=make("label","",d.name); label.title=d.hint; const input=make("input"); input.type="range"; input.min=0; input.max=100; input.step=5; input.name=d.id; input.value=state.profile?.scores?.[d.id] ?? 50; const out=make("output","",input.value); input.addEventListener("input",()=>out.textContent=input.value); row.append(label,input,out); box.append(row);});
    if(state.profile) showDiagnosis(state.profile);
  }
  function diagnose(scores) {
    const tracks={
      "2023E":{name:"黄河水沙数据建模",w:{mathematics:.15,coding:.2,data:.35,writing:.15,mechanism:.15},first:"完成时间索引、缺失模式与时间外推切分审计"},
      "2016A":{name:"系泊系统机理建模",w:{mathematics:.3,coding:.15,data:.05,writing:.15,mechanism:.35},first:"画完整受力图并独立推导悬链线几何闭合方程"},
      "2024C":{name:"种植策略运筹优化",w:{mathematics:.25,coding:.3,data:.15,writing:.15,mechanism:.15},first:"把适种、连作和三年豆类规则写成可测试约束"}
    };
    const ranking=Object.entries(tracks).map(([id,t])=>({case:id,track:t.name,readiness:+Object.entries(t.w).reduce((s,[k,w])=>s+scores[k]*w,0).toFixed(1)})).sort((a,b)=>b.readiness-a.readiness);
    const weakest=Object.entries(scores).sort((a,b)=>a[1]-b[1]).slice(0,2);
    return {scores,ranking,recommended_case:ranking[0].case,weakest,next_action:tracks[ranking[0].case].first};
  }
  function showDiagnosis(result) {
    const box=$("#diagnosticResult"); box.replaceChildren(); box.append(make("span","eyebrow","TRAINING PRESCRIPTION"),make("div","result-score",result.recommended_case),make("h2","",result.ranking[0].track),make("p","",`第一项任务：${result.next_action}`));
    const ranks=make("div","rank-list"); result.ranking.forEach(r=>{const row=make("div","rank-item"); row.append(make("span","",`${r.case} · ${r.track}`),make("strong","",`${r.readiness}`)); ranks.append(row);}); box.append(ranks);
    const names=Object.fromEntries(D.dimensions.map(d=>[d.id,d.name])); box.append(make("p","fine-print",`优先补强：${result.weakest.map(([k,v])=>`${names[k]} ${v}`).join("、")}。证据：确定性加权训练量表，不是心理测量。`));
  }

  function renderTraining() {
    const rail=$("#weekRail"); rail.replaceChildren(); D.weeks.forEach(w=>{const b=make("button",`week-button ${state.week===w.week?"active":""}`); b.append(make("b","",`W${w.week}`),make("span","",w.title)); b.addEventListener("click",()=>{state.week=w.week;save();renderTraining();}); rail.append(b);});
    const list=$("#taskList"); list.replaceChildren(); const weeks=D.weeks.filter(w=>(state.taskFilter==="all"||w.case===state.taskFilter)&&(state.taskFilter!=="all"||w.week===state.week));
    weeks.forEach(w=>w.tasks.forEach((t,i)=>{const id=`w${w.week}-${i}`; const card=make("article",`task-card ${state.completed[id]?"done":""}`); const top=make("div","task-top"); const check=make("input","task-check"); check.type="checkbox"; check.checked=!!state.completed[id]; check.setAttribute("aria-label",`完成 ${t[0]}`); check.addEventListener("change",()=>{state.completed[id]=check.checked;save();renderTraining();renderOverview();}); const body=make("div"); body.append(make("span","eyebrow",`WEEK ${w.week} · ${w.case}`),make("h3","",t[0]),make("p","",t[1])); const meta=make("div","task-meta"); ["30 分钟诊断","3 小时基线","8 小时完整"].forEach(x=>meta.append(make("span","badge",x))); body.append(meta); const rubric=make("div","rubric"); t[2].split("；").forEach(x=>rubric.append(make("div","",x))); body.append(rubric); top.append(check,body); card.append(top); list.append(card);}));
  }

  function renderGraph(filter="all") {
    const svg=$("#knowledgeGraph"); svg.replaceChildren(); const NS="http://www.w3.org/2000/svg";
    const keep=new Set(); if(filter==="all") D.graph.nodes.forEach(n=>keep.add(n.id)); else {keep.add(filter); D.graph.edges.forEach(([a,b])=>{if(a===filter){keep.add(b);D.graph.edges.forEach(([c,d])=>{if(c===b)keep.add(d);});}});}
    const nodes=D.graph.nodes.filter(n=>keep.has(n.id)); const map=Object.fromEntries(nodes.map(n=>[n.id,n]));
    D.graph.edges.filter(([a,b])=>map[a]&&map[b]).forEach(([a,b])=>{const line=document.createElementNS(NS,"line"); line.setAttribute("x1",map[a].x);line.setAttribute("y1",map[a].y);line.setAttribute("x2",map[b].x);line.setAttribute("y2",map[b].y);line.setAttribute("class","graph-edge");svg.append(line);});
    nodes.forEach(n=>{const g=document.createElementNS(NS,"g");g.setAttribute("class",`graph-node ${n.type}`);g.setAttribute("tabindex","0");const circle=document.createElementNS(NS,"circle");circle.setAttribute("cx",n.x);circle.setAttribute("cy",n.y);circle.setAttribute("r",n.type==="case"?43:38);const text=document.createElementNS(NS,"text");text.setAttribute("x",n.x);text.setAttribute("y",n.y+4);text.textContent=n.label;g.append(circle,text);const show=()=>showGraphDetail(n);g.addEventListener("click",show);g.addEventListener("keydown",e=>{if(e.key==="Enter")show();});svg.append(g);});
  }
  function showGraphDetail(n){const box=$("#graphDetail");box.replaceChildren();box.append(make("span","eyebrow",`${n.type.toUpperCase()} · ${n.id}`),make("h2","",n.label),make("p","",n.detail),make("div","boundary",n.type==="case"?"一题可对应多种方法，图谱不是标准答案。":"采用前必须说明适用条件、失败条件和验证方法。"));}

  function labRecommendation(task,time,nonlinear,missing,samples) {
    const catalog={regression:["均值 / 线性基线","岭回归","梯度提升"],classification:["多数类 / Logistic 基线","随机森林","梯度提升"],forecast:["季节朴素","阻尼趋势","只含滞后特征的树模型"],optimization:["规则可行基线","线性 / 整数规划","鲁棒情景"],mechanism:["量纲 / 极限基线","控制方程","数值求解 + 残差审计"],evaluation:["透明加权基线","PCA / 熵权对照","排序稳定性"],simulation:["解析期望","固定种子 Monte Carlo","方差缩减"]};
    const risks=[]; if(time||task==="forecast")risks.push("必须时间外推或滚动验证；随机切分直接拒绝"); if(missing>40)risks.push("高缺失：先研究缺失机制，不要只换更复杂模型"); if(samples<100)risks.push("样本较小：限制自由度并报告区间"); if(nonlinear)risks.push("非线性增益必须相对简单基线证明");
    return {models:catalog[task],risks,stop:"没有改善样本外证据、约束质量或解释能力时，停止增加复杂度。"};
  }
  function showLab(r) {const box=$("#labResult");box.replaceChildren();box.append(make("span","eyebrow","COMPARISON PLAN"),make("h2","","候选模型顺序"));const seq=make("div","model-sequence");r.models.forEach((m,i)=>{const row=make("div","model-step");row.append(make("b","",String(i+1)),make("strong","",m));seq.append(row);});box.append(seq,make("h3","","强制验证"));const risks=make("ul","number-list");(r.risks.length?r.risks:["保留独立测试集；保存参数、种子、耗时和依赖版本"]).forEach(x=>risks.append(make("li","",x)));box.append(risks,make("div","boundary",r.stop),make("p","fine-print","证据 C：结构化推荐。模型选择仍取决于题目与数据。"));}

  function coach(draft,timeOrdered) {
    const low=draft.toLowerCase(); const f=[]; const add=(level,code,message,action)=>f.push({level,code,message,action});
    if(timeOrdered&&(draft.includes("随机划分")||low.includes("random split")))add("error","TIME_SPLIT","时间序列随机划分会泄漏未来结构。","改用时间外推或滚动起点验证。");
    if(!/(baseline|基线|朴素|线性)/i.test(draft))add("warning","NO_BASELINE","没有可解释的简单基线。","先建立最低比较线。");
    if(/最优|optimal|全局最优/i.test(draft)&&!/gap|证明|bound|界/i.test(draft))add("error","UNPROVEN_OPTIMAL","“最优”没有证明或求解器界。","报告状态与 gap，或改称候选解。");
    if(!/误差|残差|rmse|mae|敏感性|审计/i.test(draft))add("warning","NO_AUDIT","缺少误差、残差或约束审计。","至少补一个结果审计和一个结构审计。");
    if(/因果|导致|证明了/i.test(draft)&&!/对照|识别|实验|工具变量|断点/i.test(draft))add("warning","CAUSAL_OVERCLAIM","因果措辞缺少识别设计。","降级为相关结论，或补可信识别。");
    if(!/来源|附件|官方|sha|证据/i.test(draft))add("info","NO_SOURCE","没有说明题面、附件或参数来源。","增加来源 ID、版本和文件校验值。");
    if(!f.length)add("pass","BASIC_PASS","未触发基础规则风险。","继续人工核验公式、数据和边界。");
    return {score:Math.max(0,100-f.reduce((s,x)=>s+({error:24,warning:12,info:5,pass:0}[x.level]),0)),findings:f};
  }
  function showCoach(r){const box=$("#coachResult");box.replaceChildren();box.append(make("span","eyebrow","RULE REVIEW"),make("div","result-score",String(r.score)),make("h2","","可审计训练评分"));const list=make("div","finding-list");r.findings.forEach(x=>{const row=make("div",`finding ${x.level}`);const head=make("div","finding-head");head.append(make("strong","",x.message),make("code","",`${x.level.toUpperCase()} · ${x.code}`));row.append(head,make("p","subtle",`动作：${x.action}`),make("small","","证据 R：本地确定性规则"));list.append(row);});box.append(list,make("h3","","继续追问"));const qs=make("ul","number-list");["你的最简单基线是什么？","哪条结论最依赖额外假设？","删掉一个关键特征或约束会怎样？"].forEach(q=>qs.append(make("li","",q)));box.append(qs,make("p","fine-print","规则结果不是官方或专家评分，也不能证明模型正确。"));}

  function renderTables(){const runs=$("#verifiedRuns");runs.replaceChildren();D.verifiedRuns.forEach(r=>{const tr=make("tr");r.forEach(x=>tr.append(make("td","",x)));runs.append(tr);});const cards=$("#benchmarkCards");cards.replaceChildren();D.benchmark.forEach(b=>{const c=make("article","case-card");c.append(make("span","case-id",b.id),make("h3","",b.task),make("p","",b.split),make("div","boundary",b.metrics));cards.append(c);});const lead=$("#leaderboard");lead.replaceChildren();D.leaderboard.forEach(r=>{const tr=make("tr");r.forEach(x=>tr.append(make("td","",x)));lead.append(tr);});const badges=$("#reproBadges");badges.replaceChildren();[["S","source-checked"],["C","code-runs"],["R","result-reproduced"],["I","independent-review"]].forEach(([i,n])=>{const row=make("div","repro-badge");row.append(make("i","",i),make("span","",n));badges.append(row);});}

  let timer=null;
  function renderSimulation(){const line=$("#simulationTimeline");line.replaceChildren();const elapsed=state.simulation.startedAt?(Date.now()-state.simulation.startedAt)/3600000:0;D.simulation.forEach(s=>{const c=make("article",`timeline-item ${elapsed>=s.hour?"active":""}`);c.append(make("b","",`H+${s.hour}`),make("h3","",s.title),make("p","subtle",s.rule));line.append(c);});updateCountdown();}
  function updateCountdown(){const total=48*3600*1000;const elapsed=state.simulation.startedAt?Date.now()-state.simulation.startedAt:0;const left=Math.max(0,total-elapsed);const h=String(Math.floor(left/3600000)).padStart(2,"0");const m=String(Math.floor(left%3600000/60000)).padStart(2,"0");const s=String(Math.floor(left%60000/1000)).padStart(2,"0");$("#countdown").textContent=`${h}:${m}:${s}`;$("#simulationStatus").textContent=state.simulation.startedAt?(left?`已运行 ${(elapsed/3600000).toFixed(1)} 小时`:"模拟结束，立即复盘"):"尚未开始";}

  function renderTeam(){const roles=$("#roleCards");roles.replaceChildren();D.roles.forEach(r=>{const c=make("article","stat-card");c.append(make("span","",r.name),make("strong","",r.scope),make("small","",`常见风险：${r.risk}`));roles.append(c);});const board=$("#teamBoard");board.replaceChildren();[["todo","待处理"],["doing","进行中"],["done","已完成"]].forEach(([status,label])=>{const col=make("section","kanban-column");const tasks=state.teamTasks.filter(t=>t.status===status);const h=make("h3");h.append(make("span","",label),make("small","",String(tasks.length)));col.append(h);tasks.forEach(t=>{const card=make("article","kanban-task");card.append(make("strong","",t.title),make("p","fine-print",t.owner));const select=make("select","select");[["todo","待处理"],["doing","进行中"],["done","已完成"]].forEach(([v,n])=>{const o=make("option","",n);o.value=v;o.selected=v===t.status;select.append(o);});select.addEventListener("change",()=>{t.status=select.value;save();renderTeam();});card.append(select);col.append(card);});board.append(col);});}

  function portfolioData(){const completed=D.weeks.flatMap(w=>w.tasks.map((t,i)=>({id:`w${w.week}-${i}`,case:w.case,title:t[0]}))).filter(t=>state.completed[t.id]);return {generated_at:new Date().toISOString(),version:"5.0.0",profile:state.profile,progress:{completed:completed.length,total:taskCount,percent:percent()},completed_tasks:completed,boundary:"Personal training record; not an official competition credential."};}
  function renderPortfolio(){const data=portfolioData();const box=$("#portfolioPreview");box.replaceChildren();const hero=make("div","portfolio-hero");hero.append(make("span","eyebrow","MY CUMCM LENS"),make("h2","",state.profile?`当前主线：${state.profile.recommended_case}`:"尚未完成能力诊断"),make("p","",`已完成 ${data.progress.completed}/${data.progress.total} 项训练任务，完成度 ${data.progress.percent}%。`));box.append(hero);const grid=make("div","portfolio-grid");D.cases.forEach(c=>{const count=data.completed_tasks.filter(t=>t.case===c.id).length;const item=make("div","portfolio-item");item.append(make("strong","",`${c.id} · ${count}/12`),make("p","fine-print",c.ability));grid.append(item);});box.append(grid,make("div","boundary","此页面记录训练证据，不把完成任务等同于竞赛获奖或专业认证。"));}
  function portfolioHtml(){const d=portfolioData();const tasks=d.completed_tasks.map(t=>`<li>${t.case} · ${escapeHtml(t.title)}</li>`).join("");return `<!doctype html><meta charset="utf-8"><title>我的 CUMCM Lens 作品集</title><style>body{max-width:800px;margin:60px auto;font-family:system-ui;color:#17211b;line-height:1.7}h1{color:#176b4d}.box{padding:20px;background:#edf2ec;border-radius:14px}</style><h1>我的 CUMCM Lens 作品集</h1><div class="box"><b>版本 V5</b><p>完成 ${d.progress.completed}/${d.progress.total} 项，${d.progress.percent}%</p></div><h2>已完成训练</h2><ul>${tasks||"<li>尚无已完成任务</li>"}</ul><p>边界：个人训练记录，不是官方竞赛认证。</p>`;}
  function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}

  function generateContent(angle){const p=percent();const templates={mistake:`标题：AI 做数学建模最容易造假的 5 个地方\n\n开头：复杂模型不等于严谨。最危险的不是模型不会跑，而是随机切分时间序列、把可行解写成全局最优、手工修改论文数字。\n\n结构：\n1. 一个真实错误：24 天被误写成 24 个月\n2. 为什么测试没发现\n3. 修复：月频断言 + 回归测试\n4. 给观众的检查清单\n\n结尾：先证明数据和验证方式可靠，再谈模型。`,case:`标题：我把 2023E 黄河水沙题真正复现后，结果并不好看\n\n核心事实：含沙缺失率 87.13%，最佳时间外推 R² 只有 0.325。\n\n内容：数据怎么清洗 → 为什么不能随机切分 → 三模型怎么比 → 低精度还能保留哪些结论 → 哪些结论必须放弃。\n\n价值：真实建模不是把指标包装漂亮，而是知道什么不能说。`,method:`标题：看到优化题，先别上遗传算法\n\n结构：\n1. 先构造规则可行基线\n2. 把自然语言逐条写成约束\n3. 用 MILP 给出状态与 MIP gap\n4. 在求解器外再审计约束\n5. 无法证明时只写“候选解”\n\n结尾：算法名称不值钱，可信的约束翻译才值钱。`,journey:`标题：12 周数学建模训练，我完成了 ${p}%\n\n本周证据：完成任务 ${doneCount()} 项；每项都有输出物和评分标准。\n\n复盘三问：\n1. 哪个错误最晚才发现？\n2. 哪个复杂模型没有超过基线？\n3. 下周要删掉什么无效工作？\n\n结尾：焦虑靠堆资料解决不了，只有可验收的作品能解决。`};return templates[angle];}

  function validateManifest(m){const errors=[];["case","source_ids","seed","metrics","artifacts","limitations"].forEach(k=>{if(m[k]===undefined||m[k]===null||(Array.isArray(m[k])&&!m[k].length)||(typeof m[k]==="object"&&!Array.isArray(m[k])&&!Object.keys(m[k]).length))errors.push(`缺少或为空：${k}`);});if(["forecast","time_series"].includes(m.task)&&!m.time_split)errors.push("时序任务必须声明 time_split");(m.artifacts||[]).forEach((a,i)=>{if(!a.path)errors.push(`artifacts[${i}] 缺少 path`);});return errors;}

  function bind(){
    $$("#nav button").forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.view))); $$('[data-go]').forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.go)));
    $("#menuButton").addEventListener("click",()=>$(".sidebar").classList.toggle("open"));
    $("#diagnosticForm").addEventListener("submit",e=>{e.preventDefault();const scores={};D.dimensions.forEach(d=>scores[d.id]=+e.target.elements[d.id].value);state.profile=diagnose(scores);save();showDiagnosis(state.profile);renderOverview();toast("训练建议已生成");});
    $$("#taskFilters button").forEach(b=>b.addEventListener("click",()=>{state.taskFilter=b.dataset.filter;state.week=state.taskFilter==="all"?state.week:D.weeks.find(w=>w.case===state.taskFilter).week;save();$$("#taskFilters button").forEach(x=>x.classList.toggle("active",x===b));renderTraining();}));
    $("#graphFilter").addEventListener("change",e=>renderGraph(e.target.value));
    $("#labForm input[name=missing]").addEventListener("input",e=>e.target.nextElementSibling.textContent=`${e.target.value}%`);
    $("#labForm").addEventListener("submit",e=>{e.preventDefault();const f=e.target.elements;showLab(labRecommendation(f.task.value,f.timeOrdered.checked,f.nonlinear.checked,+f.missing.value,+f.samples.value));});
    $("#coachForm").addEventListener("submit",e=>{e.preventDefault();showCoach(coach(e.target.elements.draft.value,e.target.elements.timeOrdered.checked));});
    $("#startSimulation").addEventListener("click",()=>{if(!state.simulation.startedAt)state.simulation.startedAt=Date.now();save();renderSimulation();clearInterval(timer);timer=setInterval(updateCountdown,1000);toast("48 小时模拟已开始");});
    $("#resetSimulation").addEventListener("click",()=>{state.simulation.startedAt=null;save();clearInterval(timer);renderSimulation();});
    $("#addTeamTask").addEventListener("click",()=>{const title=prompt("任务名称");if(!title)return;const owner=prompt("负责人：建模负责人 / 编程负责人 / 论文负责人","建模负责人")||"待分配";state.teamTasks.push({id:`t${Date.now()}`,title,owner,status:"todo"});save();renderTeam();});
    $("#exportPortfolio").addEventListener("click",()=>download("CUMCM_Lens_个人作品集.html",portfolioHtml(),"text/html"));
    $("#exportProgress").addEventListener("click",()=>download("CUMCM_Lens_训练进度.json",JSON.stringify(portfolioData(),null,2)));
    $("#exportAll").addEventListener("click",()=>download("CUMCM_Lens_V5_全部状态.json",JSON.stringify(state,null,2)));
    $("#generateContent").addEventListener("click",()=>$("#contentDraft").textContent=generateContent($("#contentAngle").value));
    $("#manifestForm").addEventListener("submit",e=>{e.preventDefault();const box=$("#manifestResult");box.replaceChildren();try{const m=JSON.parse(e.target.elements.manifest.value);const errors=validateManifest(m);box.append(make("span","eyebrow","MANIFEST AUDIT"),make("div","result-score",errors.length?"拒绝":"通过"));const list=make("div","finding-list");(errors.length?errors:["必填字段与时序切分规则通过。文件存在性和 SHA-256 需在本地 CLI 中继续验证。"] ).forEach(x=>{const row=make("div",`finding ${errors.length?"error":"pass"}`);row.append(make("strong","",x));list.append(row);});box.append(list,make("p","fine-print","浏览器只校验结构；运行 cumcm-lens certify 才会核对真实文件和哈希。"));}catch(err){box.append(make("div","finding error",`JSON 无法解析：${err.message}`));}});
    $("#testApi").addEventListener("click",async()=>{const s=$("#apiStatus");s.textContent="正在连接…";try{const r=await fetch("http://127.0.0.1:8765/api/v1/health");const j=await r.json();s.textContent=`已连接：${j.status} · V${j.version} · ${j.mode}`;}catch{s.textContent="未连接。先在本地运行：cumcm-lens-api --port 8765";}});
  }

  function init(){
    renderOverview();renderDiagnostic();renderTraining();renderGraph();renderTables();renderSimulation();renderTeam();renderPortfolio();
    $("#manifestForm textarea").value=JSON.stringify(D.manifestExample,null,2); bind(); navigate(state.view||"overview");
    if(state.simulation.startedAt)timer=setInterval(updateCountdown,1000);
  }
  init();
})();
