"""Recompute Part 6 teaching cases only. This script reads no company data."""
import json
from decimal import Decimal as D, localcontext, ROUND_HALF_UP
from pathlib import Path
from statistics import median

OUTPUT = Path(__file__).resolve().parents[1] / 'docs/analysis-preparation/teaching-results.json'

def ratio(numerator, denominator, minimum=D('0'), *, use_ev=False):
    if numerator is None or denominator is None:
        return {'status':'missing','value':None}
    if denominator < 0:
        return {'status':'NM: negative denominator','value':None}
    if denominator == 0:
        return {'status':'NM: zero denominator','value':None}
    if denominator <= minimum:
        return {'status':'NM: near zero by predeclared threshold','value':None}
    if use_ev and numerator < 0:
        return {'status':'negative EV: investigate', 'value':None, 'raw_ratio':numerator/denominator}
    return {'status':'valid','value':numerator/denominator}

def growth_payment(g, rate, return_on_capital):
    if not 0 <= g < min(rate, return_on_capital):
        raise ValueError('Positive stable cash flow domain: 0 <= g < min(cost, return)')
    return (1-g/return_on_capital)/(rate-g)

def aggregate(rows, weights):
    if len(rows) != len(weights) or any(w < 0 or w > 1 for w in weights):
        raise ValueError('Weights are the shares included divided by all ordinary shares')
    cap = sum(r['cap']*w for r,w in zip(rows,weights))
    positive = sum(max(D(0),r['ntm_profit'])*w for r,w in zip(rows,weights))
    losses = sum(min(D(0),r['ntm_profit'])*w for r,w in zip(rows,weights))
    return {'weighted_market_cap':cap,'weighted_positive_profit':positive,'weighted_losses':losses,
            **ratio(cap,positive+losses)}

INPUTS = [
 ('甲','240','20','0','24','240','120','30','10'),
 ('乙','216','18','0','21.6','216','108','27','9'),
 ('丙','300','20','0','30','200','100','20','20'),
 ('丁','180','30','18','15','150','100','30','10'),
 ('戊','150','-5','0','-2','150','80','50','5'),
 ('目标','200','20','0','25','250','125','40','10'),
]
FIELDS = 'cap ttm_profit after_tax_oneoff ntm_profit ntm_sales book debt excess_cash'.split()

def study():
    with localcontext() as ctx:
        ctx.prec = 50
        rows = []
        for name,*values in INPUTS:
            r = dict(zip(FIELDS,map(D,values)))
            normalized = r['ttm_profit']-r['after_tax_oneoff']
            ev = r['cap']+r['debt']-r['excess_cash']
            r.update(name=name, normalized_profit=normalized, market_ev=ev,
                     ttm_pe=ratio(r['cap'],r['ttm_profit']), normalized_pe=ratio(r['cap'],normalized),
                     forward_pe=ratio(r['cap'],r['ntm_profit']), pb=ratio(r['cap'],r['book']),
                     forward_ps=ratio(r['cap'],r['ntm_sales']), forward_ev_sales=ratio(ev,r['ntm_sales'],use_ev=True))
            rows.append(r)
        def sample(candidates, key):
            selected = sorted(r[key]['value'] for r in candidates if r[key]['status']=='valid')
            def percentile(p):
                position = D(len(selected)-1)*D(p)
                lower = int(position)
                return selected[lower]+(position-lower)*(selected[min(lower+1,len(selected)-1)]-selected[lower])
            return {'members':[r['name'] for r in candidates],'total':len(candidates),'valid':len(selected),
                    'excluded':{r['name']:r[key]['status'] for r in candidates if r[key]['status']!='valid'},
                    'median':median(selected),'min':min(selected),'max':max(selected),
                    'p25':percentile('.25'),'p75':percentile('.75'),'quantile_method':'linear interpolation at (n−1)p'}
        pe = sample(rows[:4],'forward_pe')
        ev_sales = sample(rows[:4],'forward_ev_sales')
        narrower = sample(rows[:2],'forward_ev_sales')
        all_pe = sample(rows[:5],'forward_pe')
        ag4 = aggregate(rows[:4],[D(1)]*4)
        ag5 = aggregate(rows[:5],[D(1)]*5)
        weighted = aggregate(rows[:2],[D('0.5'),D(1)])
        target = rows[-1]
        shares = D(10)
        equity_from_pe = pe['median']*target['ntm_profit']
        def from_ev(group):
            operating = group['median']*target['ntm_sales']
            equity = operating-target['debt']+target['excess_cash']
            return {'operating_value':operating,'equity_value':equity,'per_share':equity/shares}
        result_ev = from_ev(ev_sales)
        result_small = from_ev(narrower)
        independently_calculated = {
            '丁正常化净利':rows[3]['normalized_profit'],'丁正常化PE':rows[3]['normalized_pe']['value'],
            '目标EV':target['market_ev'],'目标前瞻PE':target['forward_pe']['value'],
            '目标EV/Sales':target['forward_ev_sales']['value'],'甲至丁PE中位数':pe['median'],
            '甲至丁EV/Sales中位数':ev_sales['median'],'PE每股参考值':equity_from_pe/shares,
            'EV/Sales每股参考值':result_ev['per_share'],'甲至丁聚合PE':ag4['value'],
            '甲至戊聚合PE':ag5['value'],'甲乙EV/Sales中位数':narrower['median'],
            '甲乙EV/Sales每股参考值':result_small['per_share'],
        }
        published = ['12','15.00','230','8.00','0.92','10.00','1.20833','25.00','27.21','10.33','12.26','1.08333','24.08']
        verified = []
        for (key,value),answer in zip(independently_calculated.items(),published,strict=True):
            rounded = value.quantize(D(1).scaleb(D(answer).as_tuple().exponent),rounding=ROUND_HALF_UP)
            assert rounded==D(answer),(key,value,answer)
            verified.append({'check':key,'calculated':value,'rounded':rounded,'lecture':answer})
        def m(r, w, g): return growth_payment(D(g),D(w),D(r))
        sotp_equity = D(40*12+60*6+100+50-300)-D(8)/D('.08')
        implied_margins = [D('1.8')/m('.12',w,'.03') for w in ('.08','.09','.10')]
        examples = {
            '8.3': {'same_cap_ev_ebitda':[D(600)/100,D(1170)/100], 'with_nci':D(1050)/100},
            '8.4': {'same_price_ttm_and_forward':[D(100)/2,D(100)/5], 'participation_weighted_demo':weighted,
                    'negative_ev':ratio(D(-20),D(10),use_ev=True),'zero':ratio(D(100),D(0)),
                    'near_zero':ratio(D(100),D('0.02'),D('0.1')),'missing':ratio(None,D(10))},
            '8.5': {'dps':D(2)*D('.6'),'value':D('1.2')/(D('.10')-D('.05')),
                    'forward_pe':D('.6')/D('.05'),'base_pe':D('.6')*D('1.05')/D('.05'),
                    'implied_roe':D('.05')/D('.4'),'cyclical_pe':[D(80)/10,D(80)/4]},
            '8.6': {'pb':[D('.10')/D('.06'),D('.04')/D('.08')],'per_share':[D(1)/D('.06'),D('.4')/D('.08')]},
            '8.7': {'forward_ps':12*D('.1'),'ps_and_ev_sales':[D(600)/1000,D(600+500-100)/1000],
                    'stable_ev_sales':[D('.1')*m('.12','.09','.03'),D('.1')*m('.06','.09','.03')],
                    'gross_vs_net_ev_sales':[D(500)/1000,D(500)/100]},
            '8.8': {'ev_ebitda':[D(900)/100,D(600)/100],'ev_ebit':[D(900)/90,D(600)/50],
                    'lease_before_after_and_mismatch':[D(800)/80,D(900)/100,D(800)/100]},
            '8.9': {'growth_cagr':D('1.44').sqrt()-1,'simple_peg':[D(30)/30,D(18)/12],
                    'stable_peg':[D('.6')/D('.05')/5,D('.6')/D('.10')/5]},
            '8.10': {'ev_ebit':[D('.8')*m('.16','.08','.02'),D('.8')*m('.16','.10','.02'),
                                  D('.8')*m('.16','.08','.04')],
                     'ev_ebit_return_equals_wacc':[D('.8')*m('.08','.08','.02'),D('.8')*m('.08','.08','.04')]},
            '8.11': {'segments':[40*12,60*6],'hq_present_value':D(8)/D('.08'),
                     'equity':sotp_equity,'per_share':sotp_equity/100},
            '8.12': {'relative_discount':1-D(20)/30,'reported_normalized_pe':[D(100)/10,D(100)/5],
                     'year1_year5_pe':[D(100)/5,D(100)/D('12.5')],
                     'four_year_cagr':(D('12.5')/5)**D('.25')-1,'ev_ebitda_cash_scope':[D(800)/100,D(1000)/100]},
            '8.13': {'base_and_thesis_ev_sales':[D('.10')*m('.10','.10','.03'),D('.12')*m('.15','.10','.03')]},
            '8.15': {'implied_margin':implied_margins,
                     'implied_roe':D('.03')+2*D('.06'),'eps':10*D('.15'),'retention':D('.03')/D('.15'),
                     'fcff_check':1000*implied_margins[1]*(1-D('.03')/D('.12')),
                     'ev_check':1000*implied_margins[1]*m('.12','.09','.03')}
        }
        assert examples['8.15']['ev_check']==1800
        assert examples['8.9']['growth_cagr']==D('.2')
        assert all_pe['valid']==4 and all_pe['total']==5 and ag5['weighted_losses']==-2
        assert all(v['value'] is None for k,v in examples['8.4'].items() if k in ['negative_ev','zero','near_zero','missing'])
        for args in (('.12','.09','.09'),('.03','.09','.03'),('.12','.09','-.01')):
            try: m(*args)
            except ValueError: continue
            raise AssertionError('invalid stable domain accepted')
        return {'scope':'Part 6 教学虚构，金额亿元、股数亿股、每股人民币元。非公司Fact。',
                'precision':50,'worksheet_8_16':rows,'comparison_checks':verified,'examples':examples,
                'groups':{'甲至丁PE':pe,'甲至丁EV/Sales':ev_sales,'甲乙EV/Sales':narrower,'甲至戊PE分布':all_pe,
                          '甲至丁聚合':ag4,'甲至戊聚合':ag5},'target_references':{
                              'current_teaching_price':target['cap']/shares,'PE_equity':equity_from_pe,
                              'PE_per_share':equity_from_pe/shares,'EV_to_equity':result_ev,'narrow_group':result_small},
                'interpretation':{
                    'Ding':'税后一次性18由原报30扣除，正常化12，P/E由6升至15。',
                    'Wu':'个体利润为负时P/E记NM。在甲至戊聚合中亏损保留，盈利合计减少2。',
                    'narrower_group':'甲乙成熟组剔开丙丁后，中位EV/Sales从1.20833降至1.08333。参照的成熟度与增长、利润率、杠杆、客户集中度不同，目标公司的适用倍数需另证。',
                    'relative_discount_vs_group_pe':1-target['forward_pe']['value']/pe['median'],
                    'conditional_upside_on_pe_reference':(equity_from_pe/shares)/(target['cap']/shares)-1,
                    'conditional_margin_of_safety_on_pe_reference':1-target['cap']/equity_from_pe,
                    'expected_return':None,
                    'expected_return_reason':'需要持有期、现金分配、退出价格及概率；横向折价不提供这些输入。'},
                'personnel':{'actual_agent':'Agent Decimal machine recomputation','student_hand_calculation':None,
                             'independent_human_reviewer':None,'manual_form':'sessions/teaching-review-template.json'},
                'editorial_notes':[{'location':'8.4 TTM段','issue':'原文“2025年Q3、2025Q4及、2026年Q1和2026Q2”有多余顿号',
                                    'treatment':'按这四个单季度理解，原稿未改'},
                                   {'location':'8.16讲义核对值','issue':'显示位数不同',
                                    'treatment':'计算保留50位有效精度，仅核对时按讲义显示位数四舍五入'}]}

if __name__ == '__main__':
    result=study()
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print('8.16 independently matched:', len(result['comparison_checks']))
