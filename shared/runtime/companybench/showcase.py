"""Independent presentation drafts, never a Fact or report store."""
from pathlib import Path
import json,copy,threading,re,math
from datetime import datetime,timezone
from .core import WorkbenchError,atomic_text
_LOCK=threading.RLock()
def feature_templates():
    return json.loads((Path(__file__).parent/'result_features.json').read_text(encoding='utf-8'))

def seed():
    cards=json.loads((Path(__file__).parent/'knowledge.json').read_text(encoding='utf-8'))['cards']
    groups=[('evidence','证据与研究方法',[]),('business','经营与价值创造',[]),('valuation','现金流与估值',[]),('risk','风险与资产配置',[]),('learning','复盘与知识积累',[])]
    for c in cards:
        text=' '.join(c.get('tags',[]))+' '+c['title']
        index=2 if any(x in text for x in ('FCFF','估值','现金','终值','资本','税')) else 3 if any(x in text for x in ('组合','期权','风险','收益','评价','基金','概率')) else 1 if any(x in text for x in ('收入','增长','渠道','行业','品牌','结构')) else 0 if any(x in text for x in ('证据','来源','核验','机制','叙事')) else 4
        groups[index][2].append(c)
    result=[]
    for c in cards:
        result.append(dict(id=c['id'],kind='knowledge',title=c['title'],body=c.get('method',''),evidence=c.get('source',''),boundary=c.get('stop',''),question=c.get('question',''),status='Method',tags=c.get('tags',[]),archived=False,original=copy.deepcopy(c)))
    for ident in ('K50','K59','K63'):
        c=next((x for x in result if x['id']==ident),None)
        if c:
            item=copy.deepcopy(c);item.update(id='result-'+ident,kind='result',title='方法成果｜'+c['title'],tags=['方法成果',*c['tags']]);result.append(item)
    maps=[]
    for key,title,items in groups:
        nodes=[dict(id='root',parent=None,title=title,detail='点击节点查看内容；展开分支探索关联。',card_id=None)]
        for c in items:nodes.append(dict(id=c['id'],parent='root',title=c['title'],detail=c.get('method',''),card_id=c['id']))
        maps.append(dict(id=key,title=title,nodes=nodes,archived=False))
    maps.insert(0,dict(id='overview',title='研究如何走向投资判断',archived=False,nodes=[dict(id='root',parent=None,title='研究与价值',detail='知识、经营、估值和价格的接续地图。',card_id=None)]+[dict(id=g[0],parent='root',title=g[1],detail='在左侧地图列表进入该专题，查看全部关联知识。',card_id=None) for g in groups]))
    return dict(schema_version=1,revision=0,title='我的最终展示',cards=result+feature_templates(),maps=maps,note='独立展示草稿；来源和人工核验仍由原项目维护。')
def directory(root,space):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',space):raise WorkbenchError('展示空间编号无效')
    return Path(root)/'runtime/final-showcase'/space

def validate(doc):
    if not isinstance(doc,dict) or doc.get('schema_version')!=1:raise WorkbenchError('不支持的展示格式')
    if not isinstance(doc.get('title'),str) or len(doc['title'])>300:raise WorkbenchError('展示标题无效')
    if not isinstance(doc.get('cards'),list) or not isinstance(doc.get('maps'),list):raise WorkbenchError('需要卡片与导图列表')
    if len(doc['cards'])>3000 or len(doc['maps'])>100:raise WorkbenchError('单展示空间最多3000卡、100图')
    ids=set()
    for c in doc['cards']:
        if not isinstance(c,dict) or not isinstance(c.get('id'),str) or c['id'] in ids:raise WorkbenchError('卡片编号缺失或重复')
        ids.add(c['id'])
        if c.get('kind') not in ('knowledge','result'):raise WorkbenchError('未知卡片类型')
        for k in ('title','body','evidence','boundary'):
            if not isinstance(c.get(k),str) or len(c[k])>100000:raise WorkbenchError('卡片文字格式无效')
    for c in doc['cards']:
        if 'feature' not in c:continue
        f=c['feature']
        if not isinstance(f,dict) or not isinstance(f.get('sections'),list) or len(f['sections'])>40:raise WorkbenchError('专题最多40个分析单元')
        for key in ('kicker','headline','subtitle','summary'):
            if not isinstance(f.get(key),str):raise WorkbenchError('专题标题和摘要必须是文字')
        section_ids=set()
        for sec in f['sections']:
            if not isinstance(sec.get('id'),str) or sec['id'] in section_ids:raise WorkbenchError('专题分析单元编号重复或缺失')
            section_ids.add(sec['id'])
            for key in ('title','body','annotation'):
                if not isinstance(sec.get(key),str):raise WorkbenchError('分析与注释必须是文字')
            if not isinstance(sec.get('chain',[]),list) or not all(isinstance(x,str) for x in sec.get('chain',[])):raise WorkbenchError('导图环节格式无效')
            if not isinstance(sec.get('knowledge_ids',[]),list) or any(x not in ids for x in sec.get('knowledge_ids',[])):raise WorkbenchError('专题关联知识卡不存在')
            ch=sec.get('chart')
            if ch is None:continue
            if ch.get('type') not in ('bar','line') or not isinstance(ch.get('unit'),str):raise WorkbenchError('图表类型或单位无效')
            labels=ch.get('labels');series=ch.get('series')
            if not isinstance(labels,list) or not 1<=len(labels)<=30 or not all(isinstance(x,str) for x in labels):raise WorkbenchError('图表需1—30个文字标签')
            if not isinstance(series,list) or not 1<=len(series)<=6:raise WorkbenchError('图表需1—6个数值系列')
            for row in series:
                vals=row.get('values')
                if not isinstance(row.get('name'),str) or not isinstance(vals,list) or len(vals)!=len(labels):raise WorkbenchError('系列数据长度与标签不匹配')
                if any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e15 for x in vals):raise WorkbenchError('图表数值缺失或超出范围')
    mapids=set()
    for m in doc['maps']:
        if not isinstance(m.get('id'),str) or m['id'] in mapids:raise WorkbenchError('导图编号缺失或重复')
        mapids.add(m['id']);nodes=m.get('nodes')
        if not isinstance(m.get('title'),str) or not isinstance(nodes,list) or not 1<=len(nodes)<=1000:raise WorkbenchError('导图需要1—1000个节点')
        by={n['id']:n for n in nodes}
        if len(by)!=len(nodes):raise WorkbenchError('节点编号重复')
        if sum(n.get('parent') is None for n in nodes)!=1:raise WorkbenchError('每张导图须有一个根节点')
        for n in nodes:
            if not isinstance(n.get('title'),str) or not isinstance(n.get('detail',''),str):raise WorkbenchError('节点文字无效')
            if n.get('card_id') and n['card_id'] not in ids:raise WorkbenchError('节点关联卡片不存在')
            seen=set();cur=n
            while cur.get('parent') is not None:
                if cur['id'] in seen:raise WorkbenchError('导图不能循环引用')
                seen.add(cur['id'])
                if cur['parent'] not in by:raise WorkbenchError('父节点不存在')
                cur=by[cur['parent']]
    return doc

def load(root,space='general',revision=None):
    p=directory(root,space)
    if revision is not None:
        if not isinstance(revision,int) or revision<0:raise WorkbenchError('版本号无效')
        p=p/'history'/f'{revision}.json'
    else:p=p/'current.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else seed() if revision is None else (_ for _ in ()).throw(WorkbenchError('历史版本不存在'))

def save(root,space,doc,expected_revision):
    validate(doc)
    with _LOCK:
        current=load(root,space)
        if type(expected_revision) is not int or expected_revision!=current['revision']:raise WorkbenchError('展示已被其他窗口修改，请先导出草稿，再刷新合并')
        p=directory(root,space);history=p/'history';history.mkdir(parents=True,exist_ok=True)
        old=history/f"{current['revision']}.json"
        if not old.exists():atomic_text(old,json.dumps(current,ensure_ascii=False,indent=2))
        new=copy.deepcopy(doc);new['revision']=current['revision']+1;new['updated_at']=datetime.now(timezone.utc).isoformat()
        atomic_text(p/'current.json',json.dumps(new,ensure_ascii=False,indent=2));return new

def history(root,space):
    p=directory(root,space)/'history'
    return sorted([int(x.stem) for x in p.glob('*.json')],reverse=True) if p.exists() else []
