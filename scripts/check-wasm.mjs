// Execute the same Python modules in WebAssembly, then compare to native CPython.
import {loadPyodide} from "../frontend/node_modules/pyodide/pyodide.mjs";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import assert from "node:assert/strict";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const py=await loadPyodide();
py.FS.mkdirTree("/home/pyodide/app");
for(const file of ["__init__.py","domain.py","factors.py","strategies.py","metrics.py","quality.py","engine.py","demo.py","reports.py"])
  py.FS.writeFile("/home/pyodide/app/"+file,fs.readFileSync(path.join(root,"backend/app",file),"utf8"));
const code="from app.demo import generate_demo\nfrom app.engine import run_backtest\nimport json\nprint(json.dumps(run_backtest(generate_demo(), {}), allow_nan=False))";
const python=process.env.QUANT_PYTHON || path.join(root,".venv/bin/python");
const native=JSON.parse(execFileSync(python,["-c",code],{env:{...process.env,PYTHONPATH:path.join(root,"backend")},maxBuffer:10*1024*1024,encoding:"utf8"}));
const wasm=JSON.parse(py.runPython(code.replace("print(json.dumps(","json.dumps(").replace("allow_nan=False))","allow_nan=False)")));
assert.equal(native.fingerprint,wasm.fingerprint);
for(const segment of ["in_sample","out_of_sample"]){
  assert.equal(native[segment].trades.length,wasm[segment].trades.length);
  for(const key of ["net_return_pct","gross_return_pct","max_drawdown_pct","costs_usd"])
    assert.ok(Math.abs(native[segment].metrics[key]-wasm[segment].metrics[key])<1e-8,`${segment} ${key}`);
}
console.log(JSON.stringify({check:"Native / WebAssembly parity",passed:true,fingerprint:wasm.fingerprint,out_of_sample:wasm.out_of_sample.metrics}));
