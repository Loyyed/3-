"""Thin project persistence adapter; all arithmetic delegates to shared valuation_chain."""
import sys,inspect,uuid,hashlib
from pathlib import Path
from engine import load,save,now

def calculate(action,inputs):
 from companybench import valuation_chain as v
 funcs={'forecast':v.forecast,'discount':v.discount,'capital-cost':v.capital_cost,'terminal':v.terminal,'transition':v.transition};assert action in funcs,'未知计算动作';fn=funcs[action];missing=[k for k in inspect.signature(fn).parameters if k not in inputs or inputs[k] is None]
 if missing:return {'state':'BlockedMissingInputs','missing_fields':missing,'new_fact':False,'impact':'无法执行'+action+'；按公司参数登记补同范围字段'}
 try:return {**fn(**inputs),'state':'ConditionalCalculation','new_fact':False}
 except (ValueError,KeyError,TypeError) as ex:return {'state':'BlockedInvalidInputs','error':str(ex),'new_fact':False,'impact':'保留原输入，按方法适用域修正；不得填零凑数'}
def perform(e,d,actor):
 company=d['company'];assert company in e.companies();p=e.companies()[company];action=d['calculation'];inputs=d['inputs'];assert isinstance(inputs,dict);meta=d.get('parameter_metadata',{});result=calculate(action,inputs);index=load(p/'work/valuation/index.json',{'runs':[]});version=1+len(index['runs']);rid='V'+uuid.uuid4().hex[:12];rel='work/valuation/v'+str(version)+'-'+rid+'.json';source=Path(__import__('companybench.valuation_chain',fromlist=['x']).__file__);record={'id':rid,'version':version,'at':now(),'actor':actor,'company':company,'action':action,'inputs':inputs,'parameter_metadata':meta,'result':result,'module_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'dependencies':['shared/runtime/companybench/valuation_chain.py','shared/runtime/companybench/research_depth.py'],'recalculate':'python -B scripts/recalculate_valuation.py --company '+company+' --record '+rel,'scope_boundary':'条件算术不是公司Fact；未完成beta业务去再杠杆、税损明细、归母权利桥'};save(p/rel,record);index['runs'].append({'id':rid,'path':rel,'action':action,'state':result['state'],'version':version});save(p/'work/valuation/index.json',index);return record
