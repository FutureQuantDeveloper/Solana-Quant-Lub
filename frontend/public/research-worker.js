/* The exact server Python engine executes here, off the browser's UI thread. */
let boot;
async function runtime() {
  if (!boot) boot = (async () => {
    importScripts("/runtime/pyodide.js");
    const py = await loadPyodide({indexURL:"/runtime/"});
    py.FS.mkdirTree("/home/pyodide/app");
    const files = ["__init__.py","domain.py","factors.py","strategies.py","metrics.py","quality.py","engine.py","demo.py","reports.py"];
    await Promise.all(files.map(async f => {
      const response = await fetch("/research/"+f);
      if (!response.ok) throw new Error("Shared engine source could not be loaded");
      py.FS.writeFile("/home/pyodide/app/"+f, await response.text());
    }));
    py.runPython("import json\nfrom app.demo import generate_demo\nfrom app.domain import StrategyConfig\nfrom app.engine import run_backtest, digest\nfrom app.quality import assess\nfrom app.reports import report_markdown\ndemo = generate_demo()\n");
    return py;
  })();
  return boot;
}
self.onmessage = async ({data: message}) => {
  const {id, action, payload} = message;
  try {
    const py = await runtime();
    py.globals.set("payload_json", JSON.stringify(payload ?? {}));
    py.globals.set("progress_callback", value => self.postMessage({id,progress:value}));
    let value;
    if (action === "initialize") value = py.runPython("json.dumps({'dataset': {**{k:v for k,v in demo.items() if k != 'events'}, 'quality': assess(demo), 'content_hash': digest(demo)}, 'config': StrategyConfig().to_dict()})");
    else if (action === "run") value = py.runPython("json.dumps(run_backtest(demo, json.loads(payload_json), progress_callback), allow_nan=False)");
    else if (action === "report") value = JSON.stringify(py.runPython("report_markdown(json.loads(payload_json))"));
    else if (action === "export_dataset") value = py.runPython("json.dumps(demo)");
    else if (action === "validate") value = py.runPython("json.dumps(StrategyConfig.from_dict(json.loads(payload_json)).to_dict())");
    else throw new Error("Unsupported research command");
    self.postMessage({id, value:JSON.parse(value)});
  } catch (error) {self.postMessage({id,error:String(error.message || error)});}
};
