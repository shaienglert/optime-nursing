import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
function walk(root:string):string[]{return readdirSync(root).flatMap((name)=>{const p=join(root,name);return statSync(p).isDirectory()?walk(p):[p];});}
describe('legacy decision authority boundary',()=>{it('keeps legacy recommendation engine out of live UI',()=>{const bad:string[]=[];for(const root of ['app','components','context'].map((n)=>join(process.cwd(),'src',n))){for(const p of walk(root)){if(!/\.(ts|tsx|js|jsx)$/.test(p))continue;const c=readFileSync(p,'utf8');if(c.includes('optime-v2-engine')||c.includes('runOptimeV2Engine'))bad.push(p);}}expect(bad).toEqual([]);});});
