from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.collectors import router as collectors_router
from app.api.events import router as events_router
from app.api.owners import router as owners_router
from app.api.runs import router as runs_router
from app.collector.crawler import StaticCrawler
from app.collector.scheduler import CollectorScheduler
from app.core.config import Settings, get_settings
from app.core.db import make_engine, make_session_factory
from app.core.logging import configure_logging
from app.delivery.channel import DeliveryChannel
from app.graph.checkpoint import checkpointer_context, setup_checkpointer
from app.graph.graph import build_graph
from app.llm.gateway import LLMGateway


def build_llm_gateway(settings: Settings) -> LLMGateway:
    if settings.llm_provider == "stub":
        from app.llm.providers.stub import StubLLMGateway

        return StubLLMGateway(embedding_dimension=settings.embedding_dimension)

    from app.llm.providers.openai_compatible import OpenAICompatibleLLMGateway

    if not settings.llm_api_key:
        raise RuntimeError(
            "LLM_API_KEY is required when LLM_PROVIDER=openai_compatible"
        )
    return OpenAICompatibleLLMGateway(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
    )


def build_delivery_channel(settings: Settings) -> DeliveryChannel:
    if settings.dingtalk_webhook_url:
        from app.delivery.dingtalk import DingTalkAdapter

        return DingTalkAdapter()

    from app.delivery.recording import RecordingDeliveryChannel

    return RecordingDeliveryChannel()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)

    engine = make_engine(settings)
    app.state.session_factory = make_session_factory(engine)
    app.state.llm_gateway = build_llm_gateway(settings)
    app.state.delivery_channel = build_delivery_channel(settings)

    async with checkpointer_context(settings) as checkpointer:
        await setup_checkpointer(checkpointer)
        app.state.graph = build_graph(
            app.state.llm_gateway,
            checkpointer,
            app.state.session_factory,
            app.state.delivery_channel,
            settings,
        )

        scheduler = None
        if settings.collector_scheduler_enabled:
            scheduler = CollectorScheduler(
                session_factory=app.state.session_factory,
                crawler_factory=StaticCrawler,
                llm_gateway=app.state.llm_gateway,
                graph=app.state.graph,
            )
            await scheduler.start()

        yield

        if scheduler is not None:
            await scheduler.stop()

    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Opportunity Intelligence Platform", lifespan=lifespan)
    app.include_router(events_router)
    app.include_router(runs_router)
    app.include_router(collectors_router)
    app.include_router(owners_router)
    return app


app = create_app()
