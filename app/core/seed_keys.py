"""Natural keys shared between scripts/seed_phase2.py and
app/llm/providers/fixtures.py so the stub gateway's canned ExpertResult
references real seeded organization/department/capability rows without any
runtime coupling between the two modules -- both just call
app.core.ids.seed_uuid(<one of these strings>)."""

ORG_ZHUJIAN_WEI = "org:重庆市住房和城乡建设委员会"
ORG_FAGAI_WEI = "org:重庆市发展和改革委员会"
ORG_GUOZI_WEI = "org:重庆市国有资产监督管理委员会"

DEPT_CHENGJIAN_CHU = "dept:重庆市住房和城乡建设委员会:城建处"
DEPT_KEJI_XINXI_CHU = "dept:重庆市住房和城乡建设委员会:科技信息处"
DEPT_ZHUJIAN_ANQUAN_CHU = "dept:重庆市住房和城乡建设委员会:安全监管处"

CAPABILITY_AI_YUJING = "capability:AI风险预警"
CAPABILITY_IOT = "capability:IoT感知平台"
CAPABILITY_SHUJU_ZHILI = "capability:数据治理"

# Organization-level owner for ORG_ZHUJIAN_WEI -- proves the Department Owner
# -> Organization Owner fallback path (spec §61's worked example: 城建处 has
# no department-level owner, falls back to the org-level one).
OWNER_ZHUJIANWEI_ORG = "customer_owner:重庆市住房和城乡建设委员会:org"
# Department-level owner scoped specifically to DEPT_KEJI_XINXI_CHU -- a
# different person from the org-level owner above, proving department-level
# takes priority and giving the no-dedup multi-department test two distinct
# recipients to assert on (CONTEXT.md: no push dedup across departments).
OWNER_ZHUJIANWEI_KEJI_DEPT = "customer_owner:重庆市住房和城乡建设委员会:科技信息处"
