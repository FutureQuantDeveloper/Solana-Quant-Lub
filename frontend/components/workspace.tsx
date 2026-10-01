"use client";
import {createContext,useCallback,useContext,useEffect,useState,ReactNode} from "react";
import Link from "next/link";
import {usePathname} from "next/navigation";
import {Activity,LayoutDashboard,FlaskConical,ChartNoAxesCombined,FileText,Database,ChevronRight,LoaderCircle,TriangleAlert,PanelLeftClose,PanelLeftOpen} from "lucide-react";
import * as api from "@/lib/api";
import type {Dataset,Strategy,Run} from "@/lib/types";
type Workspace={datasets:Dataset[];strategies:Strategy[];runs:Run[];loading:boolean;error:string;refresh:()=>Promise<void>;busy:boolean;progress:number;execute:(strategy:Strategy)=>Promise<Run>};
const Context=createContext<Workspace|null>(null);
export const useWorkspace=()=>{const c=useContext(Context);if(!c)throw new Error("Workspace unavailable");return c;};
export function Badge({kind}:{kind:string}){return <span className={`badge ${kind==="REAL"?"real":"synthetic"}`}>{kind}</span>;}
export function Notice({children,error=false}:{children:ReactNode;error?:boolean}){return <div className={`notice ${error?"error":""}`} role={error?"alert":undefined}><TriangleAlert size={17}/><div>{children}</div></div>;}
export function Empty({title,children}:{title:string;children:ReactNode}){return <div className="empty"><FlaskConical size={30}/><h3>{title}</h3><p>{children}</p></div>;}
export function WorkspaceProvider({children}:{children:ReactNode}){
  const [datasets,setDatasets]=useState<Dataset[]>([]),[strategies,setStrategies]=useState<Strategy[]>([]),[runs,setRuns]=useState<Run[]>([]);
  const [loading,setLoading]=useState(true),[error,setError]=useState(""),[busy,setBusy]=useState(false),[progress,setProgress]=useState(0),[collapsed,setCollapsed]=useState(false);
  const path=usePathname();
  const refresh=useCallback(async()=>{try{const [d,s,r]=await Promise.all([api.listDatasets(),api.listStrategies(),api.listRuns()]);setDatasets(d);setStrategies(s);setRuns(r);setError("");}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setLoading(false);}},[]);
  useEffect(()=>{void refresh();},[refresh]);
  const execute=async(strategy:Strategy)=>{if(busy)throw new Error("An experiment is already running");setBusy(true);setProgress(0);try{const r=await api.runStrategy(strategy,setProgress);await refresh();return r;}finally{setBusy(false);}};
  const nav=[{href:"/",name:"Workspace",icon:LayoutDashboard},{href:"/lab/",name:"Strategy lab",icon:FlaskConical},{href:"/results/",name:"Research results",icon:ChartNoAxesCombined},{href:"/report/",name:"Research report",icon:FileText},{href:"/datasets/",name:"Datasets",icon:Database}];
  return <Context.Provider value={{datasets,strategies,runs,loading,error,refresh,busy,progress,execute}}><div className={`app-shell ${collapsed?"collapsed":""}`}>
    <aside className="sidebar"><Link href="/" className="brand"><div className="brand-symbol"><Activity size={24}/></div><div><strong>SOLANA QUANT</strong><span>RESEARCH LAB</span></div></Link><button className="collapse-control" onClick={()=>setCollapsed(!collapsed)} aria-label={collapsed?"Expand navigation":"Collapse navigation"}>{collapsed?<PanelLeftOpen size={18}/>:<PanelLeftClose size={18}/>}</button>
      <div className="nav-label">RESEARCH WORKSPACE</div><nav>{nav.map(({href,name,icon:Icon})=><Link key={href} href={href} title={name} className={path===href||path===href.slice(0,-1)?"active":""}><Icon size={19}/><span>{name}</span></Link>)}</nav>
      <div className="sidebar-bottom"><div className="mode-label"><span className="status-dot"/>{api.browserMode?"Browser workspace":"Research API"}</div><p>{api.browserMode?"Experiments saved on this device.":"Experiments saved to your database."}</p><div className="version">ENGINE 1.0.0 <span>USD · UTC</span></div></div>
    </aside>
    <div className="app-main"><header className="topbar"><div className="breadcrumb">Research <ChevronRight size={14}/><span>{nav.find(n=>n.href===path||n.href.slice(0,-1)===path)?.name||"Workspace"}</span></div><div className="topbar-right"><span className="chain-label">SOLANA</span><span className="subtle">{api.browserMode?"Offline demo":"Local terminal"}</span></div></header>
      <main>{busy&&<div className="job-banner" role="status"><LoaderCircle className="spin" size={18}/><span>Processing historical events</span><progress max={100} value={progress}/><b>{progress}%</b><span className="subtle">Keep this workspace open</span></div>}
        {loading?<div className="loading" role="status"><LoaderCircle className="spin" size={28}/><h2>Opening your research workspace</h2><p>{api.browserMode?"Loading the Python engine and deterministic dataset…":"Connecting to the research API…"}</p></div>:error?<><Notice error>{error}</Notice><button className="button" onClick={()=>{setLoading(true);void refresh();}}>Retry connection</button></>:children}
      </main><footer>Reproducible research. Measurable assumptions.<span>No live trading · No execution keys</span></footer>
    </div></div></Context.Provider>;
}
