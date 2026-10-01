export const num=(n:number|null|undefined,d=2)=>n==null?"—":n.toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
export const pct=(n:number|null|undefined)=>n==null?"—":`${n>0?"+":""}${num(n)}%`;
export const usd=(n:number|null|undefined)=>n==null?"—":`$${num(n)}`;
export const day=(ts:number)=>new Date(ts*1000).toLocaleDateString("en-US",{month:"short",day:"numeric",timeZone:"UTC"});
export const time=(ts:number)=>new Date(ts*1000).toLocaleString("en-GB",{month:"short",day:"2-digit",hour:"2-digit",minute:"2-digit",timeZone:"UTC"});
