"""Publish the Stage 15 reading editions and complete filterable data exports."""
import csv
import html
import json
import re
from collections import Counter
from statistics import median

from build_research15_panel import FLOW, STAGES
from extract_research15 import OUTPUT
from recalculate_research14 import ROOT, read, save, sha

LABELS = {'confirm_existing':'沿用','revise_then_confirm':'补全后确认',
          'register_and_confirm':'新登记','link_existing':'跳转至已确认披露'}
BATCHES = ('R12-FIRST-8','R14-002507-8','R14-600298-8','R14-688188-8','R14-9992-8','R14-ISRG-8')
TITLES = {
 'audit':'阶段14全部核验裁定', 'current-ledger':'当前有效审核标签和事件', 'coverage':'原件覆盖和版本',
 'annual':'年度财务底表', 'stage-metrics':'历史分段增速、现金转化和资本回报', 'filing-cells':'报表提取行及列位', 'supplemental-cells':'已补原表行',
 'comparison_columns':'原披露和比较栏差异', 'interim':'近期同比、单期、累计、余额与滚动',
 'conflicts':'列位及口径冲突', 'operating-locators':'经营披露原件定位',
 'business-disclosures':'业务原数与来源', 'operating-bridges':'经营桥和滞后兑现',
 'forecast-parameters':'预测及估值参数', 'cashflows':'逐年三情景现金流',
 'valuation-summary':'估值结果和权益桥','valuation-attribution':'同日旧新差额',
 'capital-actions':'股数、派息和回购','relative':'相对估值证券权利和样本','sensitivities':'敏感性与市场反解','backtests':'历史留出误差',
 'market':'同日市场观测','gaps':'缺项、口径断点和实际决定标签',
 'research-judgments':'研究解释、反证与取舍',
}
CSS = """
:root{font-family:system-ui,'Microsoft YaHei',sans-serif;color:#172624;background:#f8f9f5;color-scheme:light}
body{max-width:1220px;margin:auto;padding:clamp(12px,3vw,36px);line-height:1.62}
header{border-bottom:1px solid #c9d5ce;margin-bottom:20px;padding-bottom:14px}
a{color:#005852;text-underline-offset:3px} h1{line-height:1.16;margin:.5em 0} h2{margin-top:1.6rem}
nav,.controls{display:flex;gap:10px 18px;flex-wrap:wrap;align-items:end}
input,select,button{font:inherit;border:1px solid #9cb2a3;border-radius:5px;padding:6px 8px;background:white;color:#172624}
button{cursor:pointer} .status{margin:.8em 0;color:#354e49}
.scroll{overflow:auto;max-height:72vh;border:1px solid #c9d5ce;border-radius:6px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{padding:8px 12px;border-bottom:1px solid #e0e7e1;text-align:left;vertical-align:top}
thead th{position:sticky;top:0;background:#e7efe9;white-space:nowrap}
td{min-width:90px;max-width:360px;overflow-wrap:anywhere}
pre{max-width:420px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8rem}
article{max-width:82ch} article p{line-height:1.8} .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.tile{padding:13px 16px;border:1px solid #d6e1d9;border-radius:6px;background:white}
@media print{.controls,nav{display:none}.scroll{max-height:none;overflow:visible}thead th{position:static}}
"""
JS = """
const rows = JSON.parse(document.querySelector('#data').textContent);
const columns = JSON.parse(document.querySelector('#columns').textContent);
const selector = [...document.querySelectorAll('select')];
const body = document.querySelector('tbody');
const search = document.querySelector('input[type=search]');
const status = document.querySelector('#status');
const filters = ['company','tag','scenario'];
let page = 0;
const size = 60;
selector.forEach((select, i) => {
  [...new Set(rows.map(row => row[filters[i]]).filter(Boolean))].sort().forEach(value => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.append(option);
  });
});
const index = rows.map(row => JSON.stringify(row).toLowerCase());
function render() {
  const terms = search.value.toLowerCase().trim().split(/\s+/);
  const result = rows.filter((row, i) => selector.every((s, n) => !s.value || row[filters[n]] === s.value) &&
                                         terms.every(term => index[i].includes(term)));
  const maxPage = Math.max(0, Math.ceil(result.length / size) - 1);
  page = Math.min(maxPage, Math.max(0, page));
  status.textContent = '共 ' + result.length + ' 行 · 第 ' + (page+1) + ' / ' + (maxPage+1) + ' 页';
  body.replaceChildren();
  for (const row of result.slice(page * size, (page+1)*size)) {
    const tr = document.createElement('tr');
    if (row.anchor) tr.id = row.anchor;
    columns.forEach(key => {
      const td = document.createElement('td');
      const value = row[key];
      if (key === 'url' && value && /^https?:/.test(value)) {
        const a = document.createElement('a');
        a.textContent = '发行人或监管原件';
        a.href = value;
        td.append(a);
      } else if (key === 'jump' && value) {
        const a = document.createElement('a');
        a.textContent = '当前账本条目';
        a.href = value;
        td.append(a);
      } else if (value != null && typeof value === 'object') {
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        const pre = document.createElement('pre');
        summary.textContent = '展开';
        pre.textContent = JSON.stringify(value,null,2);
        details.append(summary,pre);
        td.append(details);
      } else {
        td.textContent = value ?? '—';
      }
      tr.append(td);
    });
    body.append(tr);
  }
}
document.querySelector('.controls').addEventListener('input', () => { page=0; render(); });
document.querySelector('#prev').onclick=()=>{page--; render();};
document.querySelector('#next').onclick=()=>{page++; render();};
if (location.hash) {
  const anchor = decodeURIComponent(location.hash.substring(1));
  const match = rows.find(x => x.anchor === anchor);
  if (match) search.value = match.anchor;
}
render();
"""
NARRATIVE = {
 '002507': [
   '家庭消费者为熟悉的口味与上架可得性付款。经销商集中接货再向终端铺货，涪陵承担腌制、原料库存和基地投入。品牌回报要同时体现在同规格售价、渠道周转和现金。2016—2020年适合观察规模和利润率能否同升，2021—2022年用来观察量价与原料错位，2023—2025年检验旧基地盈利能否覆盖新投入。',
   '2024至2025年，食品收入增量44.91百万元，销量贡献25.26百万元，组均价和结构贡献19.65百万元。同期集团销售费用增59.39百万元。将量价增收与集团费用并列可检验利润是否兑现。独立核算渠道需用各渠道毛利扣返利、运费、人工和回款成本，分配前不能据此判断直营贡献为负。',
   '2026年前三季累计收入增3.45%，现金购建支出398.69百万元，期末应收143.58百万元。新渠道扩张也可能放宽账期，回款改善还需经销与直营收现拆分。基准采用销量初始增2.0%、组均价与结构增0.8%，再按留出偏差校正销量。若基地转固后吨成本升高且折扣或返利扩大，压力利润率更合适。',
   '结论分歧集中于直营增量来自终端动销或信用期延长。下一步以固定SKU净价、经销商到终端库存、期后收款以及新老基地吨折旧区分。千禾与海天可作货架和经销比较，需先核品类盈利与经销责任。'
 ],
 '600298': [
   '食品和发酵加工客户为批次稳定、功能和交付连续性付款。安琪用糖蜜等原料发酵、加工，再经区域销售或出口交货。新厂支出先进入在建，认证与爬坡决定酵母吨毛利和现金回收时间。2001—2006年主营业务收入保留旧制度口径。2007年起并列新准则与过渡重述，2013—2019年用于检验投产前后的回收。',
   '2024至2025年，酵母及深加工销量增15.83%，组均价与结构降4.96%。销量贡献1,675.99百万元，组均价与结构拖累581.29百万元。海外与境内需在地区表另桥，分产品增量和地区增量不叠加。糖蜜、能源和低毛利品种都能推动吨毛利变化，需新厂分月产量、达标品比例、认证订单和价格对读。',
   '2026年前三季收入增15.45%，CFO降22.80%。本期现金购建1,305.26百万元。下游放量可能延续，库存和收现使盈利兑现滞后。基准采用可售销量初始增7.8%、组均价增1.2%，再按留出偏差校正销量。稳态约12%核心利润率受历史利润和海外爬坡约束。安琪以资本回收瓶颈检验长期增长。',
   '安琪的低折现率放大终值。基准敏感性中，6%与8% WACC 对应的价值可能跨过36.62元收盘价。若项目的税后确实回报高且稳定，可保留较强的增长路径。若账款或新厂耗用持续，经营折价和更高融资风险会共同压缩价值。乐斯福等业务参照需单独取得可交易同权证券及酵母分部净债务。'
 ],
 '688188': [
   '设备商为控制精度、调试时间和售后兼容付款。柏楚从板卡和软件切入，随后向切割头、总线和软硬配套延伸。研发发生在出货之前，配套转换会增加备货和技术支持。2019—2021年检验控制系统放量，2022年收入回撤给出需求周期反例，2023—2025年检验硬件占比改变时主业能否继续取得高回报。',
   '2024至2025年，平面、管材、三维和其他主营分别增168.10、107.22、27.12、146.34百万元。研发和库存需与客户配套订单和现金对应。报告营业利润与核心经营利润差额保留在表中，利息与投资收入按金融收益处理。',
   '2026年前三季收入增16.05%，CFO增7.49%，期末库存403.39百万元。若存货服务配套渗透，现有客户套件购买率和期后回款应同步抬升。若主要来自机器投资周期或备货，库存周转可能先下行。基准系统出货初始增7.5%，配套和组均价增4.2%，再按留出偏差校正出货。',
   '同一类整机厂订单复苏也能造成配套收入增量。需要客户分批、研发生效日期和配套毛利，才能把高回报归给续购。运动控制公司可作为投入率参照，整机业务、收入确认及证券权利差异需要逐项核净。'
 ],
 '09992': [
   '会员和访客为角色、收藏体验和购买便利付款。公司组织设计授权、生产与发售，通过门店、电商及海外网络交付。IP投入可以在几季后兑现，扩店与租金先形成成本承诺。2017—2019年用招股书跟踪上市前规模，2022年放缓与2024—2025年爆款扩张给出两种盈利状态。',
   '2025年 THE MONSTERS 收入14,161.06百万元，占集团38.1%。2026H1该系列由4,814.02降至4,454.36百万元。同口径扣去该系列后，2026H1收入为12,718.56百万元，对比上年9,062.26百万元。同期库存由2025年末5,472.84百万元升至6,101.53百万元，H1 CFO由5,977.47降至3,637.32百万元。收入接续与现金兑现出现分化。',
   '2026Q3集团整体收入（未经审计）同比下降 45%–50%。中国下降25%–30%，亚太（不含中国）下降65%–70%，美洲下降70%–75%，欧洲及其他地区下降50%–55%，中国线下下降5%–10%，中国线上下降45%–50%。区间来自公司自愿经营更新，2026H1为最新完整报表。基准H2收入为2025H2的53%，这是条件估计，Q3绝对值及Q4走势仍待披露。',
   '若2025的发行密度把需求提前，剔除爆款后的同店与复购有机会恢复。若门店扩张稀释店效，租金和折扣会压低回报。需要商圈和开店月份分组的同店、扣折扣毛利、租金及库存账龄。IP授权公司与重店零售公司各覆盖一种驱动，缺少权利和租赁一致的可比倍数。'
 ],
 'US': [
   '医院向 Intuitive 采购或租赁设备，为服务和耗材持续付款。医院能否提高设备周转、控制每例成本并让团队保持熟练度，决定系统从首次装机到耗材与服务的现金价值。2015—2019年观察装机和后续收入，2020年手术量冲击与2021年恢复检验需求敏感性，2024—2025年观察 da Vinci 5 与租赁。',
   '2025年 da Vinci 装机约11,106台，2024年约9,902台，2025年装机出货1,721台。2024至2025年耗材、系统、服务分别增939.9、507.7、265.0百万美元。按财年首尾装机平均计算利用率只作粗略代理，装机后启用月份和Ion混合会影响单位数。',
   '2026年前三季收入增21.02%。经营现金流含其他负债变动631.8百万美元，450百万美元和解与付款时点分列。670.5百万美元为库存转设备的非现金划转，现金购建另为329.0百万美元。基准采用活跃装机贡献9.4%、利用率和每例收入贡献2.2%，再按留出偏差校正。',
   '竞争来自腹腔镜和开放手术，也来自获批平台。FDA 对 Hugo 和 Versius 的许可建立了适应证内的替代条件。医院端多平台利用率、术式构成、培训、耗材与总例成本决定份额。设备商集团倍数混合不同盈利源。保持其他基准输入时，市场价格要求显著高于模型的增长，或更低折现率。'
 ],
}
BREAKS = {
 '002507':'2010更正版、2016更新版与原件分列。收入准则、租赁、SKU及经销与直销分类变更需逐段核。应收与转固后利用率会改资本回报。',
 '600298':'2001—2006旧准则主营口径与2007新准则分段。2005更正及2007重述保留。部分早期合并/母公司混排仅锁定财务摘要。不同报告的产量、产能与外售量不可互代。',
 '688188':'IPO前财务归报表及招股书专块。产品切面重新分类，比较栏作为桥的同范围输入。股票股本、授予和每股口径分开。',
 '09992':'招股书为重组集团及比较边界。中国及海外渠道口径与报告时期一致。使用权资产、折旧及支付租金分列，公司股本货币额与实际股数分开。',
 'US':'2017和2021各一拆三，现金流重述留比较列。2017会计披露及现金流同列比较须核。部分旧购建含知识产权。期末股数与加权平均数必须分开。',
}


def esc(v):
    return html.escape(str(v), quote=True)


def compact(data):
    return json.dumps(data, ensure_ascii=False, separators=(',',':'), allow_nan=False)


def slug(text):
    return re.sub(r'[^\w.-]', '-', text)


def csv_data(file, rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    def cell(value):
        return compact(value) if isinstance(value,(list,dict)) else value
    with file.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator=chr(10))
        writer.writeheader()
        writer.writerows({k:cell(v) for k,v in row.items()} for row in rows)


def page(title, body, prefix=''):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style>'
            f'</head><body><header><nav><a href="{prefix}index.html">阶段15总览</a></nav><h1>{esc(title)}</h1>'
            f'</header>{body}</body></html>')


def export_table(key, title, rows, columns=None, write_json=True, display_rows=None):
    if write_json:
        save(OUTPUT/(key+'.json'),rows)
    csv_data(OUTPUT/(key+'.csv'),rows)
    display = display_rows if display_rows is not None else rows
    columns = columns or list(dict.fromkeys(k for row in rows for k in row))[:15]
    heads = ''.join('<th scope="col">'+esc(k)+'</th>' for k in columns)
    safe = lambda obj:compact(obj).replace('<',chr(92)+'u003c')
    body = f"""<nav><a href="{key}.csv" download>完整 CSV</a><a href="{key}.json" download>完整 JSON</a></nav>
    <section class="controls"><label>公司<br><select><option value="">全部</option></select></label>
    <label>标签<br><select><option value="">全部</option></select></label>
    <label>情景<br><select><option value="">全部</option></select></label>
    <label>搜索期间、指标、原件或事件<br><input type="search" placeholder="例如 2026-Q3"></label></section>
    <div class="status" id="status" aria-live="polite"></div><nav><button id="prev">上一页</button>
    <button id="next">下一页</button></nav><div class="scroll"><table><thead><tr>{heads}</tr></thead>
    <tbody></tbody></table></div><script type="application/json" id="data">{safe(display)}</script>
    <script type="application/json" id="columns">{safe(columns)}</script><script>{JS}</script>"""
    (OUTPUT/(key+'.html')).write_bytes(page(title,body).encode('utf-8'))


def standalone(m, company, dataset, stage_bridges, counters):
    code=company.split('_')[0]
    names=company.split('_',1)[1]
    folder=OUTPUT/code
    folder.mkdir(exist_ok=True)
    annual=[r for r in dataset['annual'] if r['company']==company]
    recent=[r for r in dataset['interim'] if r['company']==company]
    relevant=[r for r in dataset['current-ledger'] if r['company']==company]
    terminal=m['cases']['base']['terminal']
    at=m['attribution'][0]
    unit=m['security']['quote']
    base=m['cases']['base']
    desc = f"2026-11-12 当地未复权收盘 {m['price']:.2f} {unit}。阶段14基准 {at['baseline']:.2f}，阶段15基准 {at['new']:.2f}，压力 {m['cases']['stress']['per_share']:.2f}，改善 {m['cases']['improve']['per_share']:.2f}。"
    count = f"当前原披露 Fact {counters[company]} 条。阶段14、长期收入新增确认及六批跳转可从账本追到原件与确认事件。"
    long = f"财年覆盖 {annual[0]['period'][:4]}—2025，共 {len(annual)} 年。近期采用 2024—2026 同期披露，2026最新完整报表为 {'H1' if code=='09992' else 'Q3'}。{BREAKS[code]}"
    time_series=[r for r in dataset['stage-metrics'] if r['company']==company]
    history=f"{time_series[0]['stage']}至{time_series[-1]['stage']}的年度样本，分段增速、利润率、现金转化和投入回报见依据及总览筛选表。"
    updated = (f"基准 WACC {base['wacc']:.2%}，稳定增长 {terminal['growth']:.2%}，稳定核心利润率 {terminal['margin']:.2%}，"
               f"新增资本回报 {terminal['incremental_return']:.2%}，终值占企业价值 {terminal['pv_share']:.2%}。"
               f"历史和模型重估 {at['long_history_and_forecast_redesign']:+.2f}，近期 {at['recent_recalibration']:+.2f}，"
               f"口径 {at['accounting_adjustment']:+.2f} {unit}/股。")
    if code=='600298':
        sb={item['variable']:item['per_share'] for item in m['sensitivity']}
        updated+=f"固定其他基准输入时，6% WACC 对应 {sb['WACC 6%']:.2f} 元，8% 对应 {sb['WACC 8%']:.2f} 元。"
    elems=[('交易时点与价值',desc),('证据窗口',long),('商业模式与资本占用',NARRATIVE[code][0]+' '+history),
           ('量价、结构和现金',NARRATIVE[code][1]),('最近披露形成的参数更新',NARRATIVE[code][2]),
           ('条件估值和终值',updated),('反方、相对估值与下一项证据',NARRATIVE[code][3]),
           ('依据与研究边界',count+' 本稿估值按条件模型，正文判断为解释或预测。年度经营投入资本子集为净营运交易余额、固定资产、在建、无形及使用权资产的可得部分。用相邻年度平均存量计算代理ROIC，新增回报仅在投入增量为正时报告。')]
    files = [('完整依据 JSON','basis.json'),('可复算模型 JSON','model.json'),
             ('Markdown','report.md'),('预测现金流 CSV','cashflows.csv')]
    md='# '+names+'证券分析\n\n'+'\n\n'.join('## '+h+'\n\n'+p for h,p in elems)+'\n'
    (folder/'report.md').write_bytes(md.encode('utf-8'))
    body='<article>'+''.join(f'<h2>{esc(h)}</h2><p>{esc(p)}</p>' for h,p in elems)+'</article>'
    body+='<nav>'+''.join(f'<a href="{url}" download>{label}</a>' for label,url in files)+'</nav>'
    (folder/'report.html').write_bytes(page(names+'证券分析',body,'../').encode('utf-8'))
    save(folder/'basis.json', dict(company=company, statement_window='2026-11-12', annual=annual, recent=recent,
          facts=relevant, stages=time_series, bridges=stage_bridges, calibration=m['calibration'], stage14_model=m['baseline_sha256'],
          writing_policy_sha256=sha(ROOT/'docs/analysis-preparation/writing-v2.md'), interpretations=elems))
    local_model=ROOT/'companies'/company/'work/research15/model.json'
    (folder/'model.json').write_bytes(local_model.read_bytes())
    csv_data(folder/'cashflows.csv',[r for r in dataset['cashflows'] if r['company']==company])


def build():
    audit=read(OUTPUT/'audit.json')
    current=read(OUTPUT/'current-ledger.json')
    tables={k:read(OUTPUT/(k+'.json')) for k in (
        'coverage','annual','filing-cells','supplemental-cells','comparison_columns','interim',
        'conflicts','operating-locators','backtests')}
    models=read(OUTPUT/'valuation.json')
    company_name={m['company']:m['company'].split('_')[0] for m in models}
    sources={r['id']:r for r in tables['coverage']}
    counters=Counter(r['company'] for r in current if r['tag']=='Fact')
    audit_rows=[]
    for row in current:
        row['anchor']=company_name[row['company']]+'-'+row['id']
        row['period']=row['scope'].get('period')
        row['actor']=row.get('verifier')
        row['url']=sources.get(row['sources'][0]['source_id'],{}).get('url') if row['sources'] else None
    for row in audit['rows']:
        cid,rid=row['company'],row['ledger_id']
        before=row['current']
        anchor=company_name[cid]+'-'+rid
        exact=next(x for x in current if x['anchor']==anchor)
        assert exact['binding']==before['binding'] and exact['tag']=='Fact'
        audit_rows.append(dict(**row, tag='Fact', disposition=LABELS[row['verdict']],
                               reviewed_value=before.get('range') or before.get('value'),
                               confirmation_event=before['confirmation_event'],
                               actor=before['verifier'], jump='current-ledger.html#'+anchor,
                               url=sources.get(row['source_id'],{}).get('url'),
                               event=exact['event']))
    tables.update(audit=audit_rows, **{'current-ledger':current})
    tables['market']=[dict(company=k,tag='市场观测',**row) for k,row in audit['price_observations'].items()]
    tables.update({k:[] for k in ('cashflows','forecast-parameters','valuation-summary','valuation-attribution','sensitivities',
        'operating-bridges','business-disclosures','gaps','research-judgments','relative','stage-metrics','capital-actions')})
    for m in models:
        company=m['company']; code=company_name[company]
        company_dir=ROOT/'companies'/company
        ref=read(company_dir/'work/research12/source-data.json')['rows']
        bridges=read(company_dir/'work/research12/calculation.json')['bridges']
        series=[r for r in tables['annual'] if r['company']==company]
        anchor_refs=[r['source'] for r in series if r['parameter_window']]
        for y0,y1,stage in STAGES[code]:
            period_rows=[r for r in series if y0<=int(r['period'][:4])<=y1]
            stats={field:[r['derived'][field] for r in period_rows if r['derived'][field] is not None]
                   for field in ('core_margin','cfo_margin','cfo_to_nopat','store_roic_proxy','incremental_return_proxy')}
            first=period_rows[0]['values']['revenue']; last=period_rows[-1]['values']['revenue']
            annual_growth=(last/first)**(1/(y1-y0))-1 if y1>y0 else period_rows[0]['values']['reported_revenue_growth']
            tables['stage-metrics'].append(dict(company=company,period=f'{y0}—{y1}',stage=stage,
                 revenue_first=first,revenue_last=last,cagr_or_single_year=annual_growth,
                 medians={key:median(vals) if vals else None for key,vals in stats.items()},
                 sample_count={key:len(vals) for key,vals in stats.items()},
                 report_sources=[dict(id=r['source'],sha256=r['sha256'],url=r['url']) for r in period_rows],
                 tag='算术',basis='首尾年度收入与可得年度中位数，单年段使用报告比较栏。'))
        bindings=[dict(id=r['id'],binding=r['binding'],confirmation_event=r['confirmation_event'])
                  for r in current if r['company']==company and r['tag']=='Fact']
        for symbol, reason in m['relative']['universe']:
            tables['relative'].append(dict(company=company,symbol=symbol,screen=reason,
                issuer_rights=m['security']['right'], own_market=m['relative']['stage14_market'],
                conditional_sample=m['relative']['sample'], tag='比较区间与缺项'))
        for r in series:
            year=int(r['period'][:4]); vs=r['values']
            factor=(9 if year<=2016 else 3 if year<=2020 else 1) if code=='US' else None
            tables['capital-actions'].append(dict(company=company,period=r['period'],source=r['source'],
                 share_capital_millions=vs.get('share_capital'), original_average_basic_million_shares=vs.get('shares_basic'),
                 original_average_diluted_million_shares=vs.get('shares_diluted'), share_conversion=factor,
                 basic_at_2021_share_basis=vs['shares_basic']*factor if factor and 'shares_basic' in vs else None,
                 diluted_at_2021_share_basis=vs['shares_diluted']*factor if factor and 'shares_diluted' in vs else None,
                 dividends=vs.get('dividends'),repurchases=vs.get('repurchases'),
                 combined_distributions_including_interest=vs.get('combined_distribution'),
                 locators={k:v for k,v in r['locators'].items() if k in ('share_capital','shares_basic','shares_diluted','dividends','repurchases','combined_distribution')},
                 split_sources=['https://www.sec.gov/Archives/edgar/data/1035267/000103526717000139/a20170930ex-991.htm',
                                'https://www.sec.gov/Archives/edgar/data/1035267/000103526721000174/a20210930ex-991.htm'] if factor else [],
                 tag='原数及股数桥',basis='加权平均百万股；股本是报表货币额。空白表示所选表未锁定该项。'))
        for r in ref:
            p=r['period']
            metric=r['metric']
            if (metric in ('food_revenue','food_volume','dealer_revenue','direct_revenue','yeast_revenue','yeast_cost',
                          'yeast_volume','foreign_revenue','plane_revenue','pipe_revenue','three_d_revenue','other_main_revenue',
                          'prc_revenue','apac_revenue','america_revenue','europe_revenue','ia','systems','service',
                          'equipment_transfer','lease_payment','cash_sales','interest_income','investment','fair_value') and r['value'] is not None):
                tables['business-disclosures'].append(dict(company=company,tag='原数定位',**r))
        for row in tables['filing-cells']+tables['supplemental-cells']:
            if row['company']==company and row['report']=='prospectus':
                tables['business-disclosures'].append({**row,'period':'上市前（比较期见原表列）'})
        if code=='09992':
            bridges.append(dict(name='2025H1→2026H1按头部IP和其余收入桥',period='2026-H1',
                start=13876.276,end=17172.921,steps=[dict(metric='THE MONSTERS',contribution=4454.361-4814.017),
                dict(metric='除该IP外',contribution=(17172.921-4454.361)-(13876.276-4814.017))],
                residual=0,sources=['S01b68f6b1c14e53d物理第26页及第64页'],
                note='其余含新老IP、渠道和地区共同变化。'))
        if code=='US':
            bridges.append(dict(name='2025术量与装机强度',period='2025-FY',
                da_vinci_procedures=3153000, prior_da_vinci_procedures=2683000,
                da_vinci_end_systems=11106, prior_da_vinci_end_systems=9902, new_placements=1721,
                procedures_per_average_installed_system=3153000/((11106+9902)/2),
                total_procedures_including_ion=3153000+144100,
                company_ia_per_total_procedure_proxy=6018.9e6/(3153000+144100),
                service_per_average_da_vinci_and_ion_installed=1572.1e6/((11106+9902+995+805)/2),
                sources=['Se7f95d2f97642180 HTML 第20表及经营讨论文本933、937、938、941、977'],
                note='公司耗材/服务覆盖不同术种、装机和产品。平均年末数量代替按日激活数量，代理用于跟踪而非单位合同价。'))
        if code=='600298':
            bridges.append(dict(name='2025酵母及深加工吨经济性',period='2025-FY',
                ton=467870.07, revenue_per_ton=11948836153.68/467870.07,
                cost_per_ton=8100224665.91/467870.07,
                gross_per_ton=(11948836153.68-8100224665.91)/467870.07,
                sources=['600298-a14b53fefcfc0356 物理第14—15页'],
                note='集团分部均值含产品、地区、汇率和客户组合。回收仍需新厂的实际吨出货与现金。'))
        if code=='600298':
            bridges.append(dict(name='2012→2013年主营地区桥',period='2013-FY',start=2704.50960997,
                end=3082.37931446,steps=[dict(metric='国内',contribution=2087.89623483-1823.86361099),
                dict(metric='国外',contribution=994.48307963-880.64599898)],residual=0,
                sources=['600298-99597759863c7b23物理第108—109页'],
                note='同一财年比较栏人民币口径，主营地区切面独立于产品桥。'))
        for prior,current_year in zip(series,series[1:]):
            a,b=prior['values'],current_year['values']
            if not all(k in a and k in b for k in ('revenue','cfo','capex')):
                continue
            bridges.append(dict(name='合并收入与现金变动', period=current_year['period'],
                                start=a['revenue'], end=b['revenue'],
                                revenue_change=b['revenue']-a['revenue'],
                                cfo_change=b['cfo']-a['cfo'], previous_cash_capex=a['capex'],
                                current_cash_capex=b['capex'],
                                cfo_less_capex_b=b['cfo']-b['capex'],
                                sources=[prior['source'],current_year['source']],
                                note='上期购建与本期收入和现金配对，跨期时序用于检验，具体项目归属仍待查。'))
        for b in bridges:
            tables['operating-bridges'].append(dict(company=company,tag='算术',basis='阶段12原表桥或阶段15年报同范围比较',**b))
        for k,case in m['cases'].items():
            factors=case['terminal']
            tables['cashflows'].extend(dict(company=company,scenario=k,**r) for r in case['rows'])
            tables['valuation-summary'].append(dict(company=company,scenario=k,price=m['price'],
                     per_share=case['per_share'], wacc=case['wacc'],pv_share=factors['pv_share'],
                     enterprise_value=case['enterprise_value'], equity=case['equity'],
                     terminal=factors,bridge=case['bridge'], tag='条件估值'))
            applied=case['rows'][1]
            parameter_values={
                m['parameters']['drivers'][0]: (applied['driver_1'],'逐年收入'),m['parameters']['drivers'][1]:(applied['driver_2'],'逐年收入'),
                '2026未披露期收入':(case['rows'][0]['undisclosed_revenue'],'2026收入、剩余现金'),
                '成熟营业利润率':(factors['margin'],'稳态营业利润和 NOPAT'), '新增资本回报':(factors['incremental_return'],'过渡再投资和 g/ROIC'),
                '长期收入增速':(factors['growth'],'稳定 NOPAT、终值和再投资'),
                '现金税率':(applied['cash_tax']/applied['operating_profit'],'NOPAT'),
                '营运资本比例设定':(m['parameters']['wc'][('base','stress','improve').index(k)],'营运资本占用'),
                '折现率':(case['wacc'],'显式期和终值现值'),
            }
            for key,(value,affected) in parameter_values.items():
                tables['forecast-parameters'].append(dict(company=company,scenario=k,parameter=key,
                        chosen=value, model_item=affected, evidence=anchor_refs, confirmed_bindings=bindings if key in
                        (m['parameters']['drivers'][0],m['parameters']['drivers'][1]) else [],
                        historical_window=m['parameters']['window'], mature_window=m['parameters']['steady_window'],
                        current_update=m['parameters']['check'], counterevidence=NARRATIVE[code][3], tag='Forecast'))
        tables['valuation-attribution'].extend(dict(company=company,**row) for row in m['attribution'])
        tables['sensitivities'].extend(dict(company=company,tag='条件估值',**row) for row in m['sensitivity'])
        tables['sensitivities'].extend(dict(company=company,tag='市场反解',variable=k,**row) for k,row in m['reverse_dcf'].items())
        for i,p in enumerate(NARRATIVE[code],1):
            tables['research-judgments'].append(dict(company=company,id=f'P15-{i}',interpretation=p,
                source_ids=anchor_refs, tag='解释' if i<3 else '预测' if i==3 else '反证条件'))
        tables['gaps'].append(dict(company=company, tag='口径断点', note=BREAKS[code]))
        tables['gaps'].append(dict(company=company, tag='缺项', note=NARRATIVE[code][3]))
        tables['gaps'].append(dict(company=company, tag='实际决定', note='用户授权实施 Agent 核对原披露。本次账本没有投资决定记录。'))
        for r in series:
            missing=[name for name,value in r['derived'].items() if value is None]
            missing.extend(k for k in ('revenue','cfo','cash_collections','capex','dividends','repurchases','shares_basic')
                           if k not in r['values'])
            if missing:
                tables['gaps'].append(dict(company=company, period=r['period'],source=r['source'],tag='缺项',
                                          missing=missing,note='留空。二次取数须定位原表、列位及适用口径。'))
        standalone(m,company,tables,bridges,counters)
    # The full signed ruling remains available alongside the augmented, flat export.
    (OUTPUT/'audit-with-bindings.json').write_bytes((OUTPUT/'audit.json').read_bytes())
    save(OUTPUT/'audit-rows.json',audit_rows)
    columns={
        'audit':['company','group','index','claim','reviewed_value','official_period','official_unit','disposition',
                 'source_id','location','confirmation_event','actor','jump','url'],
        'current-ledger':['company','id','claim','value','range','tag','period','sources','binding','confirmation_event','actor','url'],
        'annual':['company','period','stage','parameter_window','source','values','derived','locators','url'],
        'interim':['company','period','source','cumulative','single','yoy','single_yoy','endpoint','rolling','locators'],
        'filing-cells':['company','report','metric','value','unit','id','table','page','html_table','column','raw_line','url','tag'],
        'coverage':['company','report','title','filed','id','pages','readable_pages','html_tables','statement_cells','sha256','url'],
    }
    for key,rows in tables.items():
        if key=='audit':
            export_table('audit-rows',TITLES[key],rows,columns[key])
        else:
            export_table(key,TITLES[key],rows,columns.get(key),write_json=key not in (
                'coverage','annual','filing-cells','supplemental-cells','comparison_columns','interim',
                'conflicts','operating-locators','backtests'))
    for batch in BATCHES:
        rows=sorted((r for r in audit_rows if r['group']==batch),key=lambda r:r['index'])
        assert [r['index'] for r in rows]==list(range(1,9))
        export_table(batch,batch+' 原顺序',rows,columns['audit'])
    entries=''.join(f'<div class="tile"><strong>{esc(t)}</strong><br><a href="{k}.html">筛选表</a> · '
                    f'<a href="{k}.csv" download>CSV</a> · <a href="{k}.json" download>JSON</a></div>'
                    for key,t in TITLES.items() for k in [key if key!='audit' else 'audit-rows'])
    company_cards=''.join(f'<div class="tile"><a href="{code}/report.html">{esc(c.split("_",1)[1])}研究稿</a> · '
              f'<a href="{code}/model.json" download>模型</a> · {counters[c]} 条当前 Fact</div>'
              for c,code in company_name.items())
    batches=''.join(f'<div class="tile"><a href="{b}.html">{b}</a> · <a href="{b}.csv" download>CSV</a> · '
                    f'<a href="{b}.json" download>JSON</a></div>' for b in BATCHES)
    index='<p>估值与信息截止 2026-11-12 各交易所当地收盘。有效状态取发布时 ReviewStore 视图。</p>'
    index+='<h2>五家公司</h2><div class="grid">'+company_cards+'</div>'
    index+='<h2>六批原顺序</h2><div class="grid">'+batches+'</div>'
    index+='<h2>全部审核数据表</h2><p><a href="audit-with-bindings.json" download>完整裁定及当前绑定</a></p><div class="grid">'+entries+'</div>'
    (OUTPUT/'index.html').write_bytes(page('五家公司证券分析 · 阶段 15',index).encode('utf-8'))
    print('Audit and issuer panels:',len(audit_rows),'positions,',sum(counters.values()),'active facts')


if __name__=='__main__':
    build()
