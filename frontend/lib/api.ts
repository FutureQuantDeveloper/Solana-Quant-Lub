import {get, set, values} from "idb-keyval";
import type {Config, Dataset, Strategy, Run, Result} from "./types";
export const browserMode = process.env.NEXT_PUBLIC_EXECUTION_MODE === "browser";
const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
function uid(){const bytes=new Uint8Array(16);crypto.getRandomValues(bytes);return Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("");}
let worker: Worker | undefined;
let boot: Promise<{dataset:Dataset;config:Config}> | undefined;
const callbacks = new Map<string, {resolve:(v:unknown)=>void;reject:(e:Error)=>void;progress?:(n:number)=>void}>();
function compute<T>(action:string, payload?:unknown, progress?:(n:number)=>void):Promise<T> {
  if (!worker) {
    worker = new Worker("/research-worker.js");
    worker.onmessage = ({data}) => {
      const task = callbacks.get(data.id);
      if (!task) return;
      if (typeof data.progress === "number") {task.progress?.(data.progress); return;}
      callbacks.delete(data.id);
      if (data.error) task.reject(new Error(data.error)); else task.resolve(data.value);
    };
    worker.onerror = () => {for (const cb of callbacks.values()) cb.reject(new Error("Research worker failed. Reload the app and try again.")); callbacks.clear(); worker?.terminate(); worker=undefined; boot=undefined;};
  }
  return new Promise<T>((resolve,reject) => {
    const id=uid();
    callbacks.set(id,{resolve:resolve as (v:unknown)=>void,reject,progress});
    worker!.postMessage({id,action,payload});
  });
}
async function request<T>(path:string, body?:unknown, method?:string):Promise<T> {
  let response: Response;
  try {response=await fetch(base+path,{method:method || (body === undefined?"GET":"POST"),headers:{"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body)});}
  catch {throw new Error("Cannot reach the research API. Start FastAPI and verify NEXT_PUBLIC_API_URL. No data has been substituted.");}
  if(!response.ok){const data=await response.json().catch(()=>({detail:response.statusText}));throw new Error(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail));}
  return response.json();
}
async function initialize(){
  if(!boot) boot=compute<{dataset:Dataset;config:Config}>("initialize").catch(error=>{boot=undefined;throw error;});
  const initialized=await boot;
  if(!await get("strategy:strategy-demo")) await set("strategy:strategy-demo",{id:"strategy-demo",dataset_id:initialized.dataset.id,name:initialized.config.name,config:initialized.config,created_at:new Date().toISOString()});
  return initialized;
}
export async function listDatasets():Promise<Dataset[]>{return browserMode?[(await initialize()).dataset]:request("/api/datasets");}
export async function listStrategies():Promise<Strategy[]>{
  if(!browserMode)return request("/api/strategies");
  await initialize();
  return (await values<Strategy|Run>()).filter((x):x is Strategy=>"name" in x && "config" in x).sort((a,b)=>b.created_at.localeCompare(a.created_at));
}
export async function saveStrategy(dataset_id:string,config:Config,id?:string):Promise<Strategy>{
  if(!browserMode) return request(id?`/api/strategies/${id}`:"/api/strategies",{dataset_id,config},id?"PUT":"POST");
  config=await compute<Config>("validate",config);
  const row={id:id || "strategy_"+uid(),dataset_id,name:config.name,config,created_at:new Date().toISOString()};
  await set("strategy:"+row.id,row);return row;
}
export async function listRuns():Promise<Run[]>{
  if(!browserMode)return request("/api/backtests");
  return (await values<Strategy|Run>()).filter((x):x is Run=>"status" in x).sort((a,b)=>b.created_at.localeCompare(a.created_at)).map(r=>({...r,result:undefined,summary:r.result?{dataset_kind:r.result.dataset_kind,fingerprint:r.result.fingerprint,in_sample:r.result.in_sample.metrics,out_of_sample:r.result.out_of_sample.metrics}:undefined}));
}
export async function getRun(id:string):Promise<Run>{
  if(!browserMode)return request(`/api/backtests/${id}`);
  const run=await get<Run>("run:"+id);if(!run)throw new Error("This run was not found in this browser workspace.");return run;
}
export async function runStrategy(strategy:Strategy,progress:(n:number)=>void):Promise<Run>{
  if(!browserMode){
    const job=await request<Run>("/api/backtests",{strategy_id:strategy.id});
    for(;;){await new Promise(r=>setTimeout(r,500));const current=await getRun(job.id);progress(current.progress);if(current.status==="completed")return current;if(current.status==="failed")throw new Error(current.error||"Backtest failed");}
  }
  const row:Run={id:"run_"+uid(),strategy_id:strategy.id,dataset_id:strategy.dataset_id,status:"running",progress:0,config:strategy.config,error:null,created_at:new Date().toISOString()};
  await set("run:"+row.id,row);
  try{row.result=await compute<Result>("run",strategy.config,progress);row.status="completed";row.progress=100;await set("run:"+row.id,row);return row;}
  catch(e){row.status="failed";row.error=e instanceof Error?e.message:String(e);await set("run:"+row.id,row);throw e;}
}
export async function generateReport(run:Run):Promise<string>{
  if(browserMode)return compute<string>("report",run.result);
  const response=await fetch(`${base}/api/backtests/${run.id}/report`,{method:"POST"});if(!response.ok)throw new Error("Report generation failed");return response.text();
}
export async function exportDataset(id:string){return browserMode?compute("export_dataset"):request(`/api/datasets/${id}/export`);}
export const ingestWallets = (body:unknown) => request<{id:string}>("/api/ingestions/wallets",body);
export const getIngestion = (id:string) => request<{id:string;status:string;progress:number;error?:string;result?:Record<string,unknown>}>(`/api/ingestions/${id}`);
export function download(name:string,data:unknown,mime="application/json"){
  const url=URL.createObjectURL(new Blob([typeof data==="string"?data:JSON.stringify(data,null,2)],{type:mime}));
  const a=document.createElement("a");a.href=url;a.download=name;a.style.display="none";
  document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
}
