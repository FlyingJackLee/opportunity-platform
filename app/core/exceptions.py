"""Error taxonomy per spec §85. Phase 1 only raises a subset of these
(LLM_ERROR, STRUCTURED_OUTPUT_ERROR, UNKNOWN); the rest are defined now so later
phases (Collector, Push) don't invent a second taxonomy."""


class AppError(Exception):
    error_type: str = "UNKNOWN"


class CollectError(AppError):
    error_type = "COLLECT_ERROR"


class ParseError(AppError):
    error_type = "PARSE_ERROR"


class FilterError(AppError):
    error_type = "FILTER_ERROR"


class LLMError(AppError):
    error_type = "LLM_ERROR"


class RAGError(AppError):
    error_type = "RAG_ERROR"


class StructuredOutputError(AppError):
    error_type = "STRUCTURED_OUTPUT_ERROR"


class PushError(AppError):
    error_type = "PUSH_ERROR"
