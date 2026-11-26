from learn_german.domain.errors import GenerationError
from learn_german.domain.models import CardContent, CardRequest, ChunkKey


def content_for(request: CardRequest) -> CardContent:
    """Deterministic card content that names the chunk, so tests can tell chunks apart."""
    key = request.key
    return CardContent(
        citation_form=f"{key.noun} {key.verb}",
        shortened_sentence=request.sentence,
        verbal_rewrite=f"Verbal: {request.sentence}",
        translation=f"[{request.hint_language}] {request.sentence}",
        meaning=f"{key.noun} {key.verb} = Bedeutung",
    )


class FakeProvider:
    """Implements `ports.LLMProvider` without a network. Records every request it gets.

    Returns `content_for(request)`, or the content set in `responses` for the request's key,
    and raises `GenerationError` for keys in `fail`. Created before the parallel tracks
    (0026) so M7 can use it; M5 owns it.
    """

    def __init__(
        self, name: str = "fake", model: str = "fake-model", prompt_version: str = "fake-v1"
    ) -> None:
        self._name = name
        self._model = model
        self._prompt_version = prompt_version
        self.requests: list[CardRequest] = []
        self.fail: set[ChunkKey] = set()
        self.responses: dict[ChunkKey, CardContent] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    @property
    def prompt_version(self) -> str:
        return self._prompt_version

    def generate(self, request: CardRequest) -> CardContent:
        self.requests.append(request)
        if request.key in self.fail:
            raise GenerationError(f"fake provider fails for {request.key}")
        return self.responses.get(request.key) or content_for(request)
