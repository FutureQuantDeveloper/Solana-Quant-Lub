import fs from "node:fs/promises";
import path from "node:path";
import {fileURLToPath} from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const front = path.join(root, "frontend");
await fs.mkdir(path.join(front, "public/runtime"), {recursive:true});
await fs.mkdir(path.join(front, "public/research"), {recursive:true});
for (const file of ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"])
  await fs.copyFile(path.join(front,"node_modules/pyodide",file), path.join(front,"public/runtime",file));
for (const file of ["__init__.py","domain.py","factors.py","strategies.py","metrics.py","quality.py","engine.py","demo.py","reports.py"])
  await fs.copyFile(path.join(root,"backend/app",file), path.join(front,"public/research",file));
console.log("Prepared the shared Python engine and self-hosted Pyodide runtime.");
