import {execFileSync} from "node:child_process";
import {cpSync,rmSync} from "node:fs";
const options={stdio:"inherit",env:{...process.env,NEXT_PUBLIC_EXECUTION_MODE:"browser",STATIC_EXPORT:"1",NEXT_TELEMETRY_DISABLED:"1"}};
execFileSync("npm",["--prefix","frontend","run","prepare:browser"],options);
execFileSync("npm",["--prefix","frontend","run","build"],options);
rmSync("dist",{recursive:true,force:true});
cpSync("frontend/out","dist",{recursive:true});
