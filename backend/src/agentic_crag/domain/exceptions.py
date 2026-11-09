class AgenticCragError(Exception):
    code: str = "ERR_UNKNOWN"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class EmptyCorpusError(AgenticCragError):
    code = "E01_EMPTY_CORPUS"


class ProviderQuotaError(AgenticCragError):
    code = "E02_PROVIDER_QUOTA"


class ProviderUnavailableError(AgenticCragError):
    code = "E02_PROVIDER_UNAVAILABLE"


class WebSearchTimeoutError(AgenticCragError):
    code = "E04_WEB_SEARCH_TIMEOUT"


class MalformedPdfError(AgenticCragError):
    code = "ERR_SCANNED_OR_EMPTY_PDF"


class QueryTooLongError(AgenticCragError):
    code = "E08_QUERY_TOO_LONG"


class EmbeddingDimensionMismatchError(AgenticCragError):
    code = "ERR_EMBED_DIM_MISMATCH"
