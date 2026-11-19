"""Stage 16 source register and same-scope driver holdouts."""
from collections import defaultdict
from statistics import median
from pathlib import Path

from recalculate_research14 import ROOT, read, save, sha
from confirm_research15 import review_core

AS_OF = '2026-11-12'
CHECKED = '2026-11-19'
OUT = ROOT/'docs/research16'
BASE = ROOT/'docs/research15'
BASE_SHA = '769e6e443aba87c7a94704f4da5efb876d7ba65f'

# Each observation is taken from the cited original line or comparison column.
VOLUME = {
 '002507': [
 (2021,15.32,'002507-1309',19),(2022,14.03,'002507-2022',18),
 (2023,13.45,'002507-2023',20),(2024,13.26,'002507-2024',20),(2025,13.40,'002507-6cd117ea1ac8beee',23)],
 '600298': [
 (2021,329398,'600298-5445efd3d106ef39',18),(2022,315758.61,'600298-67eeebe5a51dee86',18),
 (2023,348505.70,'600298-174439da1375f513',19),(2024,403914.67,'600298-e14665c0175d59df',19),
 (2025,467870.07,'600298-a14b53fefcfc0356',15)],
 '09992': [
 (2020,187,'Sae0f1e1845c9aa8f',12),(2021,288,'Sae0f1e1845c9aa8f',12),
 (2022,329,'S1312bd4fec38932f',14),(2023,363,'S1312bd4fec38932f',14),
 (2024,401,'S9b89a4686ffb5fe8',15)],
 '688188': [(2024,60993,'688188-4daf701c6095d460',26),(2025,65064,'688188-a343f0dc3c27d114',29)],
 'US': [(2018,4986,'Sfb795f4a51c45110',736),(2019,5582,'Sfb795f4a51c45110',736),
        (2020,5989,'Sa49ea83ea3ce7ef2',884),(2021,6730,'S78f74b10f3f686c7',932),
        (2022,7544,'S665e685caf9f272d',967),(2023,8606,'Sf92ee8eb3f06a597',1020),
        (2024,9902,'Se4905bffbdcd3611',1022),(2025,11106,'Se7f95d2f97642180',938)],
}
DRIVER = {
 '002507':('食品加工销售量','万吨','财年自报当期。2023年报2022比较栏14.02，与2022原披露14.03分列。'),
 '600298':('酵母及深加工销售量','吨','产品组合吨数。2026H1发酵产量单列，产量与销货量分别使用。'),
 '09992':('中国内地年末实体门店','家','内地旧口径，2025起中国区重述分列。仅校正扩店情景。'),
 '688188':('控制系统销量','套','2024为新分类起点。随动功能集成改变单套定义。'),
 'US':('da Vinci 期末安装基数','台','全部安装基数是活跃装机代理，医院实际开机分母缺失。'),
}
EXTRA = [
 ('002507-b901d0b919e32cba','2026H1','直销四品类收入与成本',
  [[83.20841944,39.37747787,59.05096235,28.45456718],[5.91147430,4.35889486,4.58963508,3.64784138],
   [3.98103781,2.74999590,3.41781063,2.26724219],[29.15465105,20.76149874,7.00166303,5.77036061]],
  '人民币百万元','物理第13页；本期收入/成本、同期收入/成本','榨菜、萝卜、泡菜、其他。'),
 ('002507-b901d0b919e32cba','2026H1','经销四品类收入与成本',
  [[1068.21044468,449.91563400,1063.58197517,442.14714753],[20.51597071,17.01296232,28.55963342,22.09242184],
   [104.31354494,70.02702538,115.17353060,78.02917756],[48.24120206,35.86633993,29.54389793,18.61224108]],
  '人民币百万元','物理第13页','同上，毛利尚需扣渠道履约费用。'),
 ('002507-b901d0b919e32cba','2026H1','食品四类销量［榨菜、萝卜、泡菜、其他］',[[6.10,.19,.63,.41],[5.93,.20,.69,.27]],'万吨','物理第17页','本期和同期，各类四舍五入。'),
 ('002507-b901d0b919e32cba','2026H1','绿色智能化一期计划/在建产能',[16,16],'万吨','物理第17页；产能及产量情况','两列分别为设计和在建，实际产量空白。'),
 ('002507-b901d0b919e32cba','2026H1','旧基地设计年产能和当期产量',[[9.76,4.36],[1.36,.45],[3.08,1.62],[1.32,.6],[1.51,.35]],'万吨','物理第17页','半年产量与全年设计产能。'),
 ('600298-a14b53fefcfc0356','2025FY','酵母及深加工收入、成本和销售量',[11948.83615368,8100.22466591,467870.07],'人民币百万元、吨','物理第14–15页，分产品与产销量','集团分部。'),
 ('600298-a14b53fefcfc0356','2025FY','项目进度','总部生物智造中心、印尼新工厂加速建设','文本','物理第11页','部分其他产线投产；不能将集团销售吨数归属印尼新厂。'),
 ('600298-48dbfbb4962cfdb9','2026H1','产量与产能',[25.4,.116,49],'万吨、比例、万吨','物理第8、10页','发酵产量、同比和全集团发酵年产能。'),
 ('600298-48dbfbb4962cfdb9','2026H1','认证范围','GMO 酒精酵母获美 FDA-GRAS 认证','文本','物理第9页','具体产品认证。按工厂、客户验收及订单仍缺。'),
 ('600298-5c763f656754f15e','2026YTD9','合并利息费用',[142.35444363,135.34639315],'人民币百万元','物理第10页，合并累计利润表','当期与同期，含资本化前后的口径限制。'),
 ('600298-a14b53fefcfc0356','2025FY','利息费用',[171.65667615,106.95604278],'人民币百万元','物理第79页，合并利润表','2025、2024比较。'),
 ('688188-a343f0dc3c27d114','2025FY','控制系统与智能硬件销量、库存',[[65064,7340],[56824,7963]],'套','物理第29页，产销量情况','硬件是年报分类，单件毛利、配套率和客户续购缺分拆。'),
 ('688188-4daf701c6095d460','2024FY','控制系统与智能硬件销量、库存',[[60993,5226],[35118,3127]],'套','物理第26页，产销量情况','按2024调整后的分类。'),
 ('688188-a343f0dc3c27d114','2025FY','分解决方案与主营毛利率',[77.92,80.53,52.64],'百分数','物理第27–28页；主营、其他解决方案','2025/2024主营及2025其他解决方案。其他包含多项业务。'),
 ('S92234424087f455a','2026Q3','集团收入同比下滑区间',[.45,.50],'比例','物理第1页，Overall and Regional Revenue Performance','未经审计，集团整体。'),
 ('S94301d078620d7a6','2025Q3','集团收入同比增长区间',[2.45,2.50],'比例','物理第1页，Overall and Regional Revenue Performance','与2024Q3对比，缺金额。'),
 ('S47095a39c6425b11','2025FY','中国区、亚太、美洲、欧洲与其他期末门店',[445,85,64,36],'家','物理第16–17页；区域门店','中国区含范围调整；集团630。'),
 ('S01b68f6b1c14e53d','2026H1','中国区、亚太、美洲、欧洲与其他期末门店',[455,90,86,45],'家','物理第12–13页；区域门店','集团676。'),
 ('S3dfd53d74d23aab4','2025H1','中国区同口径期初和期末门店',[431,443],'家','物理第12页','两期门店数形成简单平均代理。'),
 ('S01b68f6b1c14e53d','2026H1','中国区实体门店收入',[6089.686,4405.948],'人民币百万元','物理第19页；Retail stores','2026H1与2025H1，根据渠道表千元原数。'),
 ('S01b68f6b1c14e53d','2026H1','THE MONSTERS 收入',[4454.361,4814.017],'人民币百万元','物理第26页；分IP','2026H1与2025H1。'),
 ('S47095a39c6425b11','2025FY','租赁附注',[592.713,81.887,1338.240,1284.337,608.288],'人民币百万元','物理第301页，附注16','使用权折旧、利息、短期及可变租赁费用、经营与融资租赁现金。'),
 ('S47095a39c6425b11','2024FY','租赁附注',[452.318,42.628,457.906,424.926,505.104],'人民币百万元','物理第301页，附注16；2024比较栏','同列序。'),
 ('S01b68f6b1c14e53d','2026H1','租赁附注',[451.934,81.056,673.120,708.255,502.889],'人民币百万元','物理第102页，附注15；第71页','同列序。'),
 ('S01b68f6b1c14e53d','2025H1','租赁附注',[254.184,28.275,513.331,433.149,263.592],'人民币百万元','物理第102页，附注15；2025比较栏','同列序。'),
 ('S83c179dfd93521d4','2026YTD9','耗材、系统、服务、经营租赁、可变租赁、买断',[5218.7,2104.8,1388.3,787,504,153],'百万美元','10-Q 附注4，第32表；MD&A 系统收入和经常收入','租赁含Ion，可变主要按手术量。'),
 ('S83c179dfd93521d4','2025YTD9','耗材、系统、服务、经营租赁、可变租赁、买断',[4360.6,1687.8,1150.1,632,380,91],'百万美元','10-Q 附注4，第32表及MD&A同比栏','同列序。'),
 ('S83c179dfd93521d4','2026Q3','设备期末安装［da Vinci、Ion、固定租赁、按量租赁］',[12094,1152,1581,1974],'台','MD&A Installed Base，第59表','租赁数量只列 da Vinci。收入中含 Ion。'),
 ('S83c179dfd93521d4','2025Q3','设备期末安装［da Vinci、Ion、固定租赁、按量租赁］',[10763,954,1379,1736],'台','MD&A Installed Base，第59表比较栏','同列序。'),
 ('S83c179dfd93521d4','2026YTD9','设备与和解现金证据',[670.5,329,450,631.8,822.0,53.2,10.5],'百万美元','10-Q 第16–17表，附注7及MD&A','非现金划转、现金购建流出、和解计提、其他负债现金调节、存货现金调节流出、产品及服务关税退款。'),
 ('S83c179dfd93521d4','2026Q3','诉讼程序','10月达成附法院批准条件的450百万美元协议','文本','10-Q 附注7；收入表与现金流分列','现金流表未列450为期内实际支付。'),
 ('Se7f95d2f97642180','2025FY','手术量与服务分母',[3153000,2683000,144100,95500,11106,9902,995,805],'例、台','MD&A 经营摘要和 Ion 段，文本933、938、941、977','2025及2024 da Vinci术量、Ion术量、da Vinci安装及Ion安装。'),
 ('Se7f95d2f97642180','2023–2025FY','经营与可变租赁收入',[[501,217],[654,338],[874,531]],'百万美元','MD&A文本块1008','当年及前两年比较。'),
 ('Se4905bffbdcd3611','2024FY','da Vinci术量',2683000,'例','MD&A活跃手术段落，文本1017','当前财年。'),
 ('Sf92ee8eb3f06a597','2023FY','da Vinci术量',2286000,'例','MD&A经营摘要，文本1015','当前财年。'),
 ('S665e685caf9f272d','2022FY','da Vinci术量',1875000,'例','MD&A经营摘要，文本962','当前财年。'),
 ('S78f74b10f3f686c7','2021FY','da Vinci术量',1594000,'例','MD&A经营摘要，文本928','当前财年。'),
 ('Se7f95d2f97642180','2025FY','全年收入构成',[6018.9,2473.7,1572.1],'百万美元','MD&A 第20表','耗材、系统、服务。'),
]


def disclosure_data(annual):
    catalog = {}
    for directory in (ROOT/'companies').iterdir():
        for s in read(directory/'sources/catalog.json'):
            catalog[s['id']] = (directory,s)
    observed = []
    checked = set()
    def add(sid,period,metric,value,unit,locator,note):
        directory,s=catalog[sid]
        when=s.get('disclosed_at') or s.get('disclosure_date') or s.get('published_at')
        assert when<=AS_OF
        if sid not in checked:
            assert sha(directory/s['path'])==s['sha256']
            checked.add(sid)
        row=dict(company=directory.name, tag='原文披露·Agent对读', period=str(period), metric=metric,
                 value=value,unit=unit,source_id=sid,source_sha256=s['sha256'],url=s['url'], locator=locator,
                 disclosed=when,checked=CHECKED,note=note)
        observed.append(row)
        return row
    series={}
    for code,items in VOLUME.items():
        series[code]=[]
        for year,v,sid,where in items:
            if sid in ('002507-1309','002507-2022','002507-2023','002507-2024'):
                sid=next(x['source'] for x in annual if x['company'].startswith(code) and x['period']==f'{year}-FY')
            metric,unit,note=DRIVER[code]
            mark=f'HTML MD&A 文本块{where}' if code=='US' else f'PDF物理第{where}页'
            row=add(sid,year,metric,v,unit,mark,note)
            series[code].append(row)
    for args in EXTRA:
        add(*args)
    return observed,series


def evaluate_holdouts(series):
    rows=[]
    bias={}
    for code,samples in series.items():
        errors=[]
        for i in range(2,len(samples)):
            start=max(0,i-3)
            available=samples[start:i]
            actual=samples[i]
            if any(r['disclosed']>=actual['disclosed'] for r in available):
                continue
            growth=median(b['value']/a['value']-1 for a,b in zip(available,available[1:]))
            estimate=available[-1]['value']*(1+growth)
            error=estimate/actual['value']-1
            errors.append(error)
            rows.append(dict(company=actual['company'],period=actual['period'],metric=actual['metric'],estimate=estimate,
                    actual=actual['value'],signed_error=error, forecast_growth=growth, unit=actual['unit'],
                    info_cutoff=available[-1]['disclosed'],training=available,target=actual, tag='留出算术'))
        bias[code]=dict(count=len(errors),median_signed_error=median(errors) if errors else None,
                        med_abs_error=median(abs(e) for e in errors) if errors else None)
    latest, target=series['688188']
    # A one-step check based on 2024's published growth. Rounded restated product
    # classification supplies a benchmark only, preserving the scenario decision.
    g=-.1083
    est=latest['value']*(1+g)
    err=est/target['value']-1
    rows.append(dict(company=target['company'],period=target['period'],metric=target['metric'],
          estimate=est,actual=target['value'],signed_error=err,forecast_growth=g,unit=target['unit'],
          info_cutoff=latest['disclosed'],training=[latest],target=target,tag='单次留出算术',
          note='使用2024年报第26页所报控制系统同比−10.83%。随动功能集成造成单位定义断点，校正不直接外推。'))
    bias['688188']=dict(count=1,median_signed_error=err,med_abs_error=abs(err),
                        use='单次留出仅作参照；基准使用2025同名披露增长率。')
    return rows,bias


def current_facts():
    core=review_core()
    facts=[]
    for directory in (ROOT/'companies').iterdir():
        store=core.ReviewStore(directory)
        assert store.history_valid()
        facts.extend(dict(company=directory.name, tag='Fact', **r) for r in store.facts())
    return facts
