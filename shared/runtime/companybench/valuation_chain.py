"""Scope-explicit cash-flow arithmetic. Results are conditional, never company Facts."""
import argparse,json
from pathlib import Path
from fractions import Fraction
from .research_depth import number,display

def n(x):
    return x if isinstance(x,Fraction) else number(x)
def packed(obj):
    if isinstance(obj,Fraction):return display(obj)
    if isinstance(obj,list):return [packed(v) for v in obj]
    if isinstance(obj,dict):return {k:packed(v) for k,v in obj.items()}
    return obj

def forecast(base_revenue, rows):
    """Explicit cash tax required. Choose total or components, never both."""
    prev=n(base_revenue)
    if prev<=0 or not rows:raise ValueError('需要正基期收入与逐年输入')
    result=[]
    for i,row in enumerate(rows,1):
        r=n(row['revenue']);ebit=r*n(row['ebit_margin']);tax=n(row['cash_operating_tax'])
        if r<0 or tax<0:raise ValueError('负收入或退税须另建适用模型')
        total='reinvestment' in row
        parts=any(k in row for k in ('capex','da','delta_ncwc'))
        if total==parts:raise ValueError('净再投资总额与完整分项必须且只能选一种')
        ri=n(row['reinvestment']) if total else n(row['capex'])-n(row['da'])+n(row['delta_ncwc'])
        result.append({'year':i,'revenue':r,'ebit':ebit,'cash_operating_tax':tax,'cash_after_operating_tax':ebit-tax,'reinvestment':ri,'fcff':ebit-tax-ri,'revenue_change':r-prev})
        prev=r
    return packed({'state':'ConditionalCalculation','new_fact':False,'rows':result,'boundary':'现金税由调用者独立预测；不自动使用有效税率。负再投资须有资产退出/营运资本回收依据。'})

def discount(cashflows, rates):
    if not cashflows or len(cashflows)!=len(rates):raise ValueError('每期现金流须对应每期资本成本')
    factor=Fraction(1);rows=[]
    for i,(cf,k) in enumerate(zip(cashflows,rates),1):
        k=n(k)
        if k<=-1:raise ValueError('折现率须大于-100%')
        factor/=1+k
        rows.append({'year':i,'factor':factor,'pv':n(cf)*factor})
    return packed({'state':'ConditionalCalculation','new_fact':False,'rows':rows,'pv_explicit':sum(x['pv'] for x in rows),'terminal_discount_factor':factor,'boundary':'仅年末现金流现值，不含终值或权益桥。'})

def terminal(nopat_next,g,new_roic,stable_wacc,explicit_rates,pv_explicit):
    p,g,r,k=map(n,(nopat_next,g,new_roic,stable_wacc))
    if not (p>0 and r>0 and 0<=g<min(r,k)):raise ValueError('本正现金流稳态模型要求NOPAT>0、0<=g<min(新增回报,WACC)')
    if not explicit_rates:raise ValueError('需要显性期各年折现率')
    factor=n(discount(['0']*len(explicit_rates),explicit_rates)['terminal_discount_factor'])
    rr=g/r;ri=p*rr;cf=p-ri;tv=cf/(k-g);pv=tv*factor;value=n(pv_explicit)+pv
    return packed({'state':'ConditionalCalculation','new_fact':False,'rr':rr,'reinvestment_next':ri,'fcff_next':cf,'tv_at_horizon':tv,'pv_terminal':pv,'operating_value':value,'terminal_share':pv/value if value>0 else None,'boundary':'数值通过不证明稳定期成立；显性末年投入与下一年利润衔接须单独核对。终值占比可超过100%。'})

def capital_cost(rf,erp,beta,equity_weight,debt_cost,tax_shield_rate):
    rf,erp,b,e,d,t=map(n,(rf,erp,beta,equity_weight,debt_cost,tax_shield_rate))
    if not(0<=e<=1 and 0<=t<=1 and d>=0 and erp>=0):raise ValueError('权重/税盾率须在0到1，债务成本与ERP非负')
    ke=rf+b*erp
    return packed({'state':'ConditionalCalculation','new_fact':False,'ke':ke,'wacc':e*ke+(1-e)*d*(1-t),'boundary':'仅普通股与债务；市场权重、债务边际成本及当期充分税盾需有独立依据。'})

def transition(nopat_last,nopat_next,reinvestment_last,new_roic):
    gap=n(nopat_next)-n(nopat_last)-n(reinvestment_last)*n(new_roic)
    return packed({'unexplained_profit_change':gap,'closed_under_new_investment_only':gap==0,'boundary':'差额可来自旧资产效率/利润率/税负变化；需另解释，不自动否定模型。'})

def main():
    p=argparse.ArgumentParser(description='现金流与终值条件复算，不补缺参数或写入Fact')
    p.add_argument('action',choices=['forecast','discount','terminal','capital-cost','transition'])
    p.add_argument('--input',type=Path,required=True)
    a=p.parse_args();obj=json.loads(a.input.read_text(encoding='utf-8-sig'))
    fn={'forecast':forecast,'discount':discount,'terminal':terminal,'capital-cost':capital_cost,'transition':transition}[a.action]
    print(json.dumps(fn(**obj),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
