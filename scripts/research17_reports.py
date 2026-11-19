"""Reading editions based on the validated model and evidence tables."""

NAMES = {'002507':'涪陵榨菜','600298':'安琪酵母','688188':'柏楚电子','09992':'泡泡玛特','US':'ISRG'}
UNIT = {'CNY':'元','HKD':'港元','USD':'美元'}
POP_SOURCE = 'https://prod-out-res.popmart.com/cms/LATEST_BUSINESS_UPDATE_FOR_THE_THIRD_QUARTER_OF_2026_c437e22e46.pdf'
ISRG_SOURCE = 'https://www.sec.gov/Archives/edgar/data/1035267/000103526726000071/isrg-20260930.htm'


def comparison_line(row):
    price,old,new,delta=(row[k] for k in ('market_close','stage15','stage16','delta'))
    unit=UNIT[row['quote']]
    return (f"2026-11-12 当地未复权收盘 {price:.2f} {unit}。"
            f"阶段 15 冻结基准 {old:.2f} {unit}，阶段 16 基准 {new:.2f} {unit}，"
            f"全精度相减后每股变动 {delta:+.2f} {unit}。")


def fuling(m):
    c=m['critical_points']; x=c['cash_collections']; q=c['market_case']; row=c['rows'][2]
    return (
        '品牌带来的重复购买和渠道覆盖仍能支撑现金。按阶段 16 经营路径，11.42 元低于基准 15.09 元。应以新基地带来的净增吨数和直销现金贡献维持这个判断。',
        f"直销放量可能伴随赊销和重复产能。集团前三季销货收现 {x['q3_ytd_cash_goods_received']:,.2f} 百万元，上年同期 {x['q3_prior_ytd_cash_goods_received']:,.2f}。9 月应收 {x['receivables']:,.2f} 百万元，上年同月 {x['prior_sept_ar']:,.2f}。渠道间回款与销售费用分配仍待核。",
        f"固定基准销量、价格、折现率和权益桥，11.42 元对应稳定营业利润率 {q['margin']['roots'][0]:.2%}、稳定 EBIT {q['normalized_ebit_if_margin_root']:,.2f} 百万元、FCFF {q['normalized_fcff_if_margin_root']:,.2f} 百万元。利润率搜索范围为 2%–80%。",
        f"上半年直销新增毛利 {c['channel_gross']:.2f} 百万元。给定可归属贸易营运资本和基地净现金购建各 5 百万元，直销至多承担 {row['max_attributable_selling_cash']:.2f} 百万元新增销售现金费用，相当于集团销售费用增量的 {row['max_share_of_group_increase']:.2%}。分到集团增量的一半时，直销增量税前现金约 {row['cash_at_half_group_expense']:.2f} 百万元。新基地利用率 35% 时，将新基地产出中替代原产出的份额由 50% 调至 80%，未扣营运资本、未计旧线节约的现金从 +77.55 降至 −28.98 百万元。若渠道现金持续为负且基地净新增迟迟不能覆盖资本开支，采用 11.00 元压力路径。",
        c['next_public'])


def anqi(m):
    c=m['critical_points']; cyc=c['cycles']; grid={r['incremental_roic']:r for r in c['rows']}
    plant=next(x for x in c['plant_thresholds'] if x['effective_incremental_investment']==300 and
               x['saleable_tonnes']==30000 and x['incremental_roic']==.112)
    return (
        '配方适配与工业客户认证可以延续复购，跨区域供货也可能摊薄交付成本。57.71 元基准依赖 5.97% WACC 和投产回报，36.62 元的价差对融资风险和收现敏感。以厂级现金回报确认价差。',
        f"库存出清可能伴随延长客户账期。以期末余额和 273 天累计流量估算，库存从 {cyc[0]['end_inventory_days']:.1f} 降至 {cyc[1]['end_inventory_days']:.1f} 天，应收从 {cyc[0]['end_receivable_days']:.1f} 升至 {cyc[1]['end_receivable_days']:.1f} 天，应付从 {cyc[0]['end_payable_days']:.1f} 降至 {cyc[1]['end_payable_days']:.1f} 天。前三季经营现金减现金购建由 {c['cash_after_capex'][0]:.2f} 降至 {c['cash_after_capex'][1]:.2f} 百万元。集团吨毛利含多个品类和地区，具体产线认证范围及实际利润、占款归属待查。",
        f"锁定阶段 16 其他经营与权益输入，稳定新增 ROIC 为 8%、11.2%、18% 时，分别要将 WACC 压到 {grid[.08]['breakeven_wacc']:.3%}、{grid[.112]['breakeven_wacc']:.3%}、{grid[.18]['breakeven_wacc']:.3%} 才回到 36.62 元。临界线下方对应高于收盘的值。",
        f"若按 7.5% WACC，新增 ROIC 临界点为 {c['roi_at_fixed_wacc']['roots'][0]:.3%}，在 8%–18% 内搜索。新增 ROIC 11.2% 对应 {grid[.112]['value_at_7_5_percent_wacc']:.2f} 元，13.0% 对应 {grid[.13]['value_at_7_5_percent_wacc']:.2f} 元。新增占用 300 百万元和年可售 3 万吨的情景，11.2% 回报需要 {plant['incremental_nopat']:.1f} 百万元 NOPAT、每吨 {plant['pretax_operating_profit_per_saleable_ton']:,.0f} 元税前营业利润。用每吨毛利扣工厂折旧与可归属费用，再匹配客户收现和库存。11 月 17 日预算由 215.24 增至 236.53 百万元，公告初步预计收益率 13.69%，项目尚需审批，实际回报待核。",
        c['next_public'])


def bochu(m):
    c=m['critical_points']; steps=m['bridge']; r=c['turnover']; band=c['renewal']; mrg=c['margin_bridge'][1]
    return (
        '控制软件的既有设备、工艺适配和售后可带来持续复购，但现价已要求更强的兑现。经营基准 92.76 元低于 96.20 元，等控制系统续购或软硬配套毛利得到验证。',
        '设备厂商景气上行也能解释销量；硬件和整套方案放量若压低毛利并拉长备货，增长很难等比变为现金。三季报将利息、投资、公允价值收益与核心经营利润分开后，前三季报表营业利润 1,226.03 百万元，按收入减成本、销售、管理、研发和税附后的核心利润 938.19 百万元。利息、投资和公允价值净收益分别为 91.06、17.06 和 46.97 百万元。库存由上年 9 月的 216.23 增至 403.39 百万元，期末成本周转代理约从 166 天延长至 216 天。最强反方是硬件附着率、大客户续购和规模毛利一起改善。',
        f"阶段 15 的 98.66 元高于收盘。去掉把总收入误差回填到单一驱动的校正后为 {steps[0]['end']:.2f} 元，再按控制销量证据校正后为 {steps[-1]['end']:.2f} 元。按原基准其他输入，96.20 元要求 2027 控制销量增速由 {c['volume_growth']:.3%} 升至 {c['volume_threshold']:.3%}，或稳定核心营业利润率由 {c['principal_margin']:.2%} 升至 {c['margin_threshold']:.2%}。",
        f"销量缺口约为 {band[0]['incremental_equivalent_sets']:.0f} 套 2025 年销量当量。若全部来自续购且可续购机会池占年销量 60%–100%，需多兑现 {band[-1]['incremental_retention_pp']:.2f}–{band[0]['incremental_retention_pp']:.2f} 个百分点。若全由占收入 25% 的软硬配套贡献，配套毛利率需提高 {mrg['required_hardware_gross_margin_pp']:.2f} 个百分点。若全靠售后，稳定期需年化节约税前约 {mrg['equivalent_stable_annual_after_sales_savings']:.2f} 百万元。库存单独压缩 30 或 60 天仅到 {r[3]['value_per_share']:.2f}／{r[4]['value_per_share']:.2f} 元，配合控制销量分别达到 {r[3]['growth_solo_threshold']:.3%}／{r[4]['growth_solo_threshold']:.3%} 才跨线。",
        c['next_public'])


def pop_pair(c, turn, rent):
    return [r for r in c['rows'] if r['h2_inventory_turn']==turn and r['rent_multiplier']==rent
            and r['assumed_2025_q3_h2_share']==.50]


def popmart(m):
    c=m['critical_points']; turns=c['group_h1_inventory_turn']
    b=pop_pair(c,turns[1],1.); s=pop_pair(c,1.35,1.15)
    return (
        f"IP 接续已有集团层面的证据，选品、渠道和授权生态仍可能支撑复购。2026H1 集团剔除 THE MONSTERS 后同口径收入增长 {c['ex_top_ip_group_yoy']:.2%}。暂时保留 166.65 港元条件基准，现金安全垫须经下半年联合检验。",
        f"爆款之外的增长可能来自新区域、新门店和高铺货。中国区门店销售除以平均门店数增长 {c['china_store_proxy']:.2%}，成熟店的同门店同周期销售仍缺批次证据。集团上半年披露毛利率由 70.34% 降至 69.68%，折扣与促销后的同款和同店毛利待拆。上半年年化平均库存周转从 {turns[0]:.2f} 降至 {turns[1]:.2f}，现金租金 {c['h1_cash_rent']/100:.2f} 亿元人民币。扩张若伴随打折、租金和库存累积，会同时压低价值。",
        f"Q3 公告原文为「集团整体收入（未经审计）同比下降 45%–50%」。在 2025Q3 占当年 H2 的情景权重 50%、库存周转 {turns[1]:.2f} 次、H2 现金租金约 {b[0]['h2_cash_rent']/100:.2f} 亿元时，143.40 港元要求 Q4 收入 {b[0]['required_q4_revenue']/100:.2f}–{b[1]['required_q4_revenue']/100:.2f} 亿元人民币。绝对 Q3、Q4 收入仍需披露。固定折现率、扩店及基础毛利，搜索 H2 同比收入倍数 0.25–0.85。",
        f"当周转降至 1.35 次、H2 现金租金约 {s[0]['h2_cash_rent']/100:.2f} 亿元，Q4 门槛抬至 {s[0]['required_q4_revenue']/100:.2f}–{s[1]['required_q4_revenue']/100:.2f} 亿元。低于所观察租金与周转组合的临界 Q4，将条件基准降至现价以下。现金租赁口径沿用阶段 16 历史、显式期和终值联动，并保留期初营运资本底线。高 Q3 权重下若推算 Q3 已越过临界 H2，该行出现非负 Q4 无等值解。",
        c['next_public'])


def isrg(m):
    c=m['critical_points']; p1,p2=c['rows']; hist=c['historic_23_25_cagr']
    lease=[r for r in c['lease'] if r['path']==1 and r['years']==5 and r['annual_maintenance']==.10]
    fixed,usage=lease
    def profile(p):
        return (f"装机增 {p['installation_growth']:.0%}、每台活跃装机术量增 {p['surgeries_per_active_growth']:.2%}、"
                f"每例变现增 {p['realization_growth']:.1%}，2031 年平均活跃装机 {p['year_2031_avg_active']:,.0f} 台，"
                f"da Vinci {p['year_2031_da_vinci']/1e6:.3f} 百万例，含 Ion 的合并耗材分母 {p['ia_denominator']/1e6:.3f} 百万例，"
                f"每例耗材 {p['per_combined_procedure']:,.0f} 美元，平均装机归一后 da Vinci 每台 {p['year_2031_da_vinci_per_avg_installed']:.0f} 例")
    return (
        '术式培训、器械配套和存量设备使用支撑耗材与服务的重复收入。439.89 美元要求业务和资本回报同时明显加速，现有经营证据支持保留 178.69 美元基准。',
        f"2026Q3 da Vinci 期末装机 12,094 台、上年同期 10,763 台，前三季 da Vinci 与 Ion 术量约增 15% 和 35%。医院术量密度持续提升可以支持价格。2025 年平均装机对应 da Vinci 每台 300 例、含 Ion 的每例耗材约 1,826 美元。2023–2025 装机、平均装机利用率和含 Ion 每例耗材收入年复合变动依次 {hist['installation']:.2%}、{hist['utilization']:.2%}、{hist['realization']:.2%}。",
        f"在 8% WACC 与每套租赁制造现金 0.85 百万美元下，两条路径均回代 439.89 美元。路径一为{profile(p1)}。路径二为{profile(p2)}。术量采用 da Vinci 独立分母衡量利用率，耗材变现采用 da Vinci 加 Ion 合并分母。装机 13%／16% 固定后，利用率增速数值反解的范围为 −3% 至 12%，按基准 9.77% WACC 则在该区间搜索无交点。",
        f"每套五年回收、年维护 0.10 百万美元、期末零残值时，需年租金现金 {fixed['required_gross_recurring_cash']:.3f} 百万美元。10-Q 年化固定与按量代理为 {fixed['live_revenue_proxy']:.3f} 和 {usage['live_revenue_proxy']:.3f} 百万美元。固定端需更长回收期、支付提升或更低成本；按量路径须验证术量密度和维护现金。2031 年路径一按量每台收入代理约 {usage['forecast_gross_revenue_per_unit']:.3f} 百万美元，路径二约 {next(x for x in c['lease'] if x['path']==2 and x['kind']=='按量代理')['forecast_gross_revenue_per_unit']:.3f} 百万美元。路径二的术量强度较接近历史，但依赖更高的装机增速和制造现金。两路径 2031 年制造设备现金分别约 {p1['annual_new_lease_cash']:,.0f}、{p2['annual_new_lease_cash']:,.0f} 百万美元。单套成本若升至 1.03 百万，条件值降至 {p1['sensitivity_to_unit_manufacturing'][-1]['value']:.2f}／{p2['sensitivity_to_unit_manufacturing'][-1]['value']:.2f} 美元。",
        c['next_public'])


NARRATIVE = {'002507':fuling,'600298':anqi,'688188':bochu,'09992':popmart,'US':isrg}
HEADINGS = ('首选判断','最强反方','现价对应的经营预期','翻转条件','下次可核对的公开指标')
