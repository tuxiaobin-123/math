#!/usr/bin/env node
import { JSDOM, VirtualConsole } from "jsdom";
import { createServer } from "node:http";
import { createReadStream, statSync } from "node:fs";
import { dirname, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

let server;
let url = process.env.CUMCM_LENS_SITE_URL;
if (!url) {
  const root = join(dirname(fileURLToPath(import.meta.url)), "..", "docs");
  const types = {".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json; charset=utf-8",".pdf":"application/pdf"};
  server = createServer((request, response) => {
    const relative = decodeURIComponent(new URL(request.url, "http://local").pathname).replace(/^\/+/, "") || "index.html";
    const path = normalize(join(root, relative));
    if (!path.startsWith(root)) { response.writeHead(403).end(); return; }
    try {
      const stat = statSync(path);
      response.writeHead(200, {"content-type": types[extname(path)] || "application/octet-stream", "content-length": stat.size});
      createReadStream(path).pipe(response);
    } catch { response.writeHead(404).end(); }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  url = `http://127.0.0.1:${server.address().port}/`;
}
const errors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on("error", (...args) => errors.push(args.join(" ")));
virtualConsole.on("jsdomError", (error) => errors.push(error.message));

const dom = await JSDOM.fromURL(url, {
  resources: "usable",
  runScripts: "dangerously",
  pretendToBeVisual: true,
  virtualConsole,
  beforeParse(window) {
    window.scrollTo = () => {};
  },
});

await new Promise((resolve) => dom.window.addEventListener("load", () => setTimeout(resolve, 300)));
const { document, Event } = dom.window;
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
  process.stdout.write(`PASS ${message}\n`);
};
const click = (selector) => {
  const node = document.querySelector(selector);
  assert(node, `element exists: ${selector}`);
  node.click();
};

assert(document.title === "CUMCM Lens V5", "page title");
assert(document.body.innerText?.trim().length > 500 || document.body.textContent.trim().length > 500, "page has meaningful content");
assert(document.querySelectorAll("#nav button").length === 11, "all navigation modules render");
assert(document.querySelectorAll("#overviewStats .stat-card").length === 4, "overview statistics render");
assert(document.querySelectorAll("#caseCards .case-card").length === 3, "three case cards render");

click('#nav button[data-view="diagnostic"]');
assert(document.querySelectorAll("#diagnosticSliders input[type=range]").length === 5, "five diagnostic dimensions render");
document.querySelector('#diagnosticForm input[name="data"]').value = "90";
document.querySelector("#diagnosticForm").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
assert(document.querySelector("#diagnosticResult").textContent.includes("2023E"), "diagnostic produces a recommendation");

click('#nav button[data-view="training"]');
const firstTask = document.querySelector("#taskList .task-check");
assert(firstTask, "training task checkbox renders");
firstTask.click();
assert(Object.keys(JSON.parse(dom.window.localStorage.getItem("cumcm-lens-v5-state"))).length > 0, "training progress persists locally");

click('#nav button[data-view="coach"]');
document.querySelector('#coachForm textarea[name="draft"]').value = "我们随机划分时间序列，用遗传算法得到全局最优解";
document.querySelector("#coachForm").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
assert(document.querySelector("#coachResult").textContent.includes("TIME_SPLIT"), "coach catches time leakage");
assert(document.querySelector("#coachResult").textContent.includes("UNPROVEN_OPTIMAL"), "coach catches unproven optimality");

click('#nav button[data-view="graph"]');
assert(document.querySelectorAll("#knowledgeGraph .graph-node").length >= 14, "knowledge graph nodes render");
click('#nav button[data-view="benchmark"]');
assert(document.querySelectorAll("#benchmarkCards .case-card").length === 3, "benchmark cards render");
click('#nav button[data-view="team"]');
assert(document.querySelectorAll("#teamBoard .kanban-column").length === 3, "team board columns render");
click('#nav button[data-view="portfolio"]');
assert(document.querySelector("#portfolioPreview").textContent.includes("已完成"), "portfolio updates from progress");

const manual = await fetch(new URL("downloads/CUMCM_Lens_V5_严谨训练手册.pdf", url));
assert(manual.ok && Number(manual.headers.get("content-length")) > 100000, "manual download is reachable");
const openapi = await fetch(new URL("openapi.json", url));
assert(openapi.ok && (await openapi.json()).info.version === "5.0.0", "OpenAPI document is reachable");
assert(errors.length === 0, `no console or resource errors (${errors.join(" | ")})`);
dom.window.close();
if (server) await new Promise((resolve) => server.close(resolve));
process.stdout.write("SITE_VERIFICATION_PASSED\n");
