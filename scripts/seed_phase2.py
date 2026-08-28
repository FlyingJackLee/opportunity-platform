"""Idempotent Phase 2 seed data -- a small representative slice (not spec
§102's full trial-run scale), enough for retrieval and the acceptance test to
be meaningful. Run after `alembic upgrade head`:

    uv run python scripts/seed_phase2.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import make_engine, make_session_factory
from app.core.ids import seed_uuid
from app.core.seed_keys import (
    CAPABILITY_AI_YUJING,
    CAPABILITY_IOT,
    CAPABILITY_SHUJU_ZHILI,
    DEPT_CHENGJIAN_CHU,
    DEPT_KEJI_XINXI_CHU,
    DEPT_ZHUJIAN_ANQUAN_CHU,
    ORG_FAGAI_WEI,
    ORG_GUOZI_WEI,
    ORG_ZHUJIAN_WEI,
    OWNER_ZHUJIANWEI_KEJI_DEPT,
    OWNER_ZHUJIANWEI_ORG,
)
from app.knowledge.ingestion import (
    ingest_capability,
    ingest_knowledge_chunk,
)
from app.llm.gateway import LLMGateway
from app.llm.providers.stub import StubLLMGateway
from app.models.customer_owner import CustomerOwner
from app.models.department import Department
from app.models.organization import Organization
from app.models.prompt_template import PromptTemplate
from app.models.score_config import ScoreConfig
from app.repositories.prompt_repository import DEFAULT_PROMPTS
from app.repositories.score_config_repository import DEFAULT_WEIGHTS

REGION = "重庆市"

ORGANIZATIONS = [
    (ORG_ZHUJIAN_WEI, "重庆市住房和城乡建设委员会", "市住建委", "GOV"),
    (ORG_FAGAI_WEI, "重庆市发展和改革委员会", "市发改委", "GOV"),
    (ORG_GUOZI_WEI, "重庆市国有资产监督管理委员会", "市国资委", "GOV"),
]

DEPARTMENTS = [
    (
        DEPT_CHENGJIAN_CHU,
        ORG_ZHUJIAN_WEI,
        "城建处",
        "市政基础设施建设管理",
        ["城市生命线", "基础设施", "市政工程"],
    ),
    (
        DEPT_KEJI_XINXI_CHU,
        ORG_ZHUJIAN_WEI,
        "科技信息处",
        "行业数字化、信息化建设统筹",
        ["数字化", "信息化", "数据治理"],
    ),
    (
        DEPT_ZHUJIAN_ANQUAN_CHU,
        ORG_ZHUJIAN_WEI,
        "安全监管处",
        "建设工程安全生产监管",
        ["安全生产", "应急管理", "风险监测"],
    ),
    (
        "dept:重庆市发展和改革委员会:高技术处",
        ORG_FAGAI_WEI,
        "高技术处",
        "高技术产业与数字经济项目审批",
        ["数字经济", "专项资金"],
    ),
    (
        "dept:重庆市发展和改革委员会:数字经济处",
        ORG_FAGAI_WEI,
        "数字经济处",
        "数字经济发展规划",
        ["数字化", "数据治理"],
    ),
    (
        "dept:重庆市国有资产监督管理委员会:创新发展处",
        ORG_GUOZI_WEI,
        "创新发展处",
        "国企数字化转型推动",
        ["数字化", "国企改革"],
    ),
    (
        "dept:重庆市国有资产监督管理委员会:监管一处",
        ORG_GUOZI_WEI,
        "监管一处",
        "国有企业运营监管",
        ["综合监管"],
    ),
]

# (natural_key, title, content, topic)
INDUSTRY_KNOWLEDGE = [
    (
        "knowledge:城市生命线概述",
        "城市生命线安全工程概述",
        "城市生命线覆盖燃气、供水、桥梁、地下管网等领域，典型建设需求包括物联感知、风险监测、风险预警、数据治理、综合监管。业务建设优先寻找业务主管部门；存在数字化建设不代表科技信息部门必然牵头。",
        "城市生命线",
    ),
    (
        "knowledge:燃气安全监测",
        "燃气管网安全监测常见需求",
        "燃气管网泄漏监测、压力监测是常见的物联感知需求，通常由住建部门下属的燃气管理处室或城建处牵头，科技信息处提供技术协同。",
        "燃气",
    ),
    (
        "knowledge:供水管网监测",
        "供水管网风险监测常见需求",
        "供水管网漏损监测、水质监测是常见建设内容，容易误判为纯技术项目，实际仍需业务主管部门主导需求。",
        "供水",
    ),
    (
        "knowledge:桥梁健康监测",
        "桥梁结构健康监测常见需求",
        "桥梁结构健康监测涉及传感器部署、结构安全预警平台建设，安全监管处通常参与风险评估环节。",
        "桥梁",
    ),
    (
        "knowledge:地下管网普查",
        "地下管网普查与数据治理",
        "地下管网普查、建档、数据治理是城市生命线数字化的基础工作，往往先于风险监测平台建设。",
        "地下管网",
    ),
    (
        "knowledge:风险监测预警平台",
        "风险监测预警平台建设要点",
        "风险监测预警平台整合多源感知数据，输出预警信息，是城市生命线数字化的核心系统，一般由城建处牵头、科技信息处协同。",
        "风险监测",
    ),
    (
        "knowledge:数据治理常见需求",
        "政企数据治理常见需求",
        "多源数据汇聚、数据标准、数据质量是数据治理的典型场景，通常由科技信息处或数据主管部门牵头。",
        "数据治理",
    ),
    (
        "knowledge:综合监管平台",
        "综合监管平台建设要点",
        "综合监管平台汇聚各业务系统数据，服务于跨部门协同监管，涉及多个业务处室共同参与需求确认。",
        "综合监管",
    ),
    (
        "knowledge:数字经济专项资金",
        "数字经济专项资金申报要点",
        "数字经济相关项目常与专项资金申报绑定，发改委高技术处、数字经济处是关键决策部门。",
        "数字经济",
    ),
    (
        "knowledge:国企数字化转型",
        "国有企业数字化转型常见路径",
        "国企数字化转型项目通常由国资委创新发展处牵头统筹，涉及多家下属企业协同推进。",
        "国企改革",
    ),
]

# (natural_key, name, scenarios, description)
CAPABILITIES = [
    (
        CAPABILITY_AI_YUJING,
        "AI风险预警",
        ["风险监测", "异常检测", "预警推送"],
        "基于多源感知数据的AI风险监测与预警能力",
    ),
    (
        CAPABILITY_IOT,
        "IoT感知平台",
        ["物联感知", "设备接入", "传感器管理"],
        "物联网设备接入与感知数据汇聚平台",
    ),
    (
        CAPABILITY_SHUJU_ZHILI,
        "数据治理",
        ["多源数据汇聚", "数据标准", "数据质量"],
        "政企数据治理与数据资产管理能力",
    ),
    (
        "capability:智慧工地",
        "智慧工地",
        ["施工安全监测", "视频智能分析"],
        "工地安全生产智能化管理能力",
    ),
    (
        "capability:数字孪生",
        "数字孪生",
        ["三维建模", "仿真推演"],
        "城市/园区数字孪生建模与仿真能力",
    ),
    (
        "capability:政务数据中台",
        "政务数据中台",
        ["数据汇聚", "数据共享交换"],
        "跨部门政务数据汇聚与共享中台能力",
    ),
    (
        "capability:视频智能分析",
        "视频智能分析",
        ["视频结构化", "行为识别"],
        "视频监控智能分析与事件识别能力",
    ),
]


async def _seed_organizations_and_departments(session: AsyncSession) -> None:
    for natural_key, name, short_name, org_type in ORGANIZATIONS:
        await session.merge(
            Organization(
                id=seed_uuid(natural_key),
                name=name,
                short_name=short_name,
                region=REGION,
                organization_type=org_type,
                status="ACTIVE",
            )
        )
    for natural_key, org_key, name, responsibility, topic_tags in DEPARTMENTS:
        await session.merge(
            Department(
                id=seed_uuid(natural_key),
                organization_id=seed_uuid(org_key),
                name=name,
                responsibility=responsibility,
                topic_tags=topic_tags,
                status="ACTIVE",
            )
        )
    await session.commit()


# (natural_key, org_key, dept_key_or_None, owner_name, owner_user_id, dingtalk_user_id)
# ORG_FAGAI_WEI/ORG_GUOZI_WEI deliberately get no Customer Owner at all --
# that's the fixture proving the fallback-to-public-group path (Phase 4 plan
# §6), reusing organizations Phase 2 already seeded rather than inventing
# unrelated test data.
CUSTOMER_OWNERS = [
    (
        OWNER_ZHUJIANWEI_ORG,
        ORG_ZHUJIAN_WEI,
        None,
        "张三",
        "zhangsan",
        "zhangsan_dingtalk",
    ),
    (
        OWNER_ZHUJIANWEI_KEJI_DEPT,
        ORG_ZHUJIAN_WEI,
        DEPT_KEJI_XINXI_CHU,
        "李四",
        "lisi",
        "lisi_dingtalk",
    ),
]


async def _seed_customer_owners(session: AsyncSession) -> None:
    for (
        natural_key,
        org_key,
        dept_key,
        owner_name,
        owner_user_id,
        dingtalk_user_id,
    ) in CUSTOMER_OWNERS:
        await session.merge(
            CustomerOwner(
                id=seed_uuid(natural_key),
                organization_id=seed_uuid(org_key),
                department_id=seed_uuid(dept_key) if dept_key else None,
                owner_name=owner_name,
                owner_user_id=owner_user_id,
                dingtalk_user_id=dingtalk_user_id,
                enabled=True,
            )
        )
    await session.commit()


async def _seed_industry_knowledge(session: AsyncSession, gateway: LLMGateway) -> None:
    for natural_key, title, content, topic in INDUSTRY_KNOWLEDGE:
        await ingest_knowledge_chunk(
            session,
            gateway,
            id=seed_uuid(natural_key),
            knowledge_type="INDUSTRY",
            title=title,
            content=content,
            industry="住建",
            region=REGION,
            topic=topic,
        )
    await session.commit()


async def _seed_capabilities(session: AsyncSession, gateway: LLMGateway) -> None:
    for natural_key, name, scenarios, description in CAPABILITIES:
        await ingest_capability(
            session,
            gateway,
            id=seed_uuid(natural_key),
            name=name,
            scenarios=scenarios,
            industries=["住建"],
            description=description,
        )
    await session.commit()


async def _seed_prompt_templates(session: AsyncSession) -> None:
    for task_type, prompt in DEFAULT_PROMPTS.items():
        await session.merge(
            PromptTemplate(
                id=seed_uuid(f"prompt_template:{task_type}:v1"),
                name=f"{task_type} v1",
                task_type=task_type,
                version="v1",
                content=prompt.content,
                enabled=True,
            )
        )
    await session.commit()


async def _seed_score_config(session: AsyncSession) -> None:
    for metric_key, weight in DEFAULT_WEIGHTS.items():
        await session.merge(
            ScoreConfig(
                id=seed_uuid(f"score_config:{metric_key}"),
                metric_key=metric_key,
                weight=weight,
                enabled=True,
            )
        )
    await session.commit()


async def seed_all(session: AsyncSession, gateway: LLMGateway) -> None:
    await _seed_organizations_and_departments(session)
    await _seed_customer_owners(session)
    await _seed_industry_knowledge(session, gateway)
    await _seed_capabilities(session, gateway)
    await _seed_prompt_templates(session)
    await _seed_score_config(session)


async def main() -> None:
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    gateway = StubLLMGateway(embedding_dimension=settings.embedding_dimension)
    async with session_factory() as session:
        await seed_all(session, gateway)
    await engine.dispose()
    print("seed data ready")


if __name__ == "__main__":
    asyncio.run(main())
