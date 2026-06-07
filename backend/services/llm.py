import ollama
from config import settings
from services.sysinfo import recommended_num_ctx


def select_model(task_type: str) -> str:
    fast_tasks = {"classify", "summarize_short", "autocomplete", "quick_answer"}
    return settings.FAST_MODEL if task_type in fast_tasks else settings.REASONING_MODEL


def num_ctx() -> int:
    """Fenêtre de contexte : adaptée à la VRAM libre si NUM_CTX_AUTO, sinon fixe."""
    if settings.NUM_CTX_AUTO:
        return recommended_num_ctx(settings.NUM_CTX)
    return settings.NUM_CTX


def _options() -> dict:
    """Options Ollama communes : fenêtre de contexte bornée (petite VRAM)."""
    return {"num_ctx": num_ctx()}


def _think_kwargs() -> dict:
    """Paramètre `think` Ollama selon le réglage (vide en mode auto)."""
    mode = (settings.THINK or "auto").lower()
    if mode == "on":
        return {"think": True}
    if mode == "off":
        return {"think": False}
    return {}


class ThinkStripper:
    """Filtre incrémental qui retire les blocs <think>…</think> d'un flux de tokens,
    pour garder un chat épuré. Tolère les balises coupées entre deux chunks."""

    _OPEN, _CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self.buf = ""
        self.in_think = False

    @staticmethod
    def _split_prefix_len(buf: str, tag: str) -> int:
        """Longueur de la plus longue fin de `buf` qui est un début de `tag`
        (pour détecter une balise coupée entre deux chunks). 0 si aucune."""
        for k in range(min(len(buf), len(tag) - 1), 0, -1):
            if buf[-k:] == tag[:k]:
                return k
        return 0

    def feed(self, piece: str) -> str:
        self.buf += piece
        out = ""
        while self.buf:
            if not self.in_think:
                i = self.buf.find(self._OPEN)
                if i != -1:
                    out += self.buf[:i]
                    self.buf = self.buf[i + len(self._OPEN):]
                    self.in_think = True
                    continue
                # Pas de balise complète : on émet tout, sauf une éventuelle fin
                # qui pourrait amorcer « <think> » (balise coupée).
                k = self._split_prefix_len(self.buf, self._OPEN)
                out += self.buf[:len(self.buf) - k] if k else self.buf
                self.buf = self.buf[len(self.buf) - k:] if k else ""
                break
            else:
                j = self.buf.find(self._CLOSE)
                if j != -1:
                    self.buf = self.buf[j + len(self._CLOSE):]
                    self.in_think = False
                    continue
                # Toujours dans <think> : on ne garde qu'une amorce de « </think> ».
                k = self._split_prefix_len(self.buf, self._CLOSE)
                self.buf = self.buf[len(self.buf) - k:] if k else ""
                break
        return out

    def flush(self) -> str:
        # Reste émis seulement si on n'est pas dans un bloc <think> non fermé.
        rest = "" if self.in_think else self.buf
        self.buf = ""
        return rest


async def stream_response(messages: list, task_type: str = "reason"):
    model = select_model(task_type)
    client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
    kwargs = dict(model=model, messages=messages, stream=True, options=_options())
    kwargs.update(_think_kwargs())
    try:
        gen = await client.chat(**kwargs)
    except TypeError:
        kwargs.pop("think", None)   # ancienne version d'ollama sans paramètre think
        gen = await client.chat(**kwargs)

    show = settings.SHOW_THINKING
    stripper = None if show else ThinkStripper()
    async for chunk in gen:
        piece = chunk["message"]["content"]
        # Certaines versions d'ollama renvoient le raisonnement à part : on l'ignore
        # en mode épuré (sinon on l'ajoute au flux).
        if show:
            thinking = chunk["message"].get("thinking")
            if thinking:
                piece = thinking + piece
            yield piece
        else:
            emit = stripper.feed(piece)
            if emit:
                yield emit
    if stripper is not None:
        tail = stripper.flush()
        if tail:
            yield tail


async def complete(messages: list, model: str | None = None,
                   num_predict: int = 512, temperature: float = 0.2,
                   think: bool | None = None) -> str:
    """Réponse complète (non streamée). `think=False` désactive le raisonnement
    (utile pour les tâches utilitaires : sinon le « thinking » consomme le budget)."""
    client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
    kwargs = dict(
        model=model or settings.REASONING_MODEL,
        messages=messages,
        stream=False,
        options={"num_ctx": num_ctx(), "num_predict": num_predict, "temperature": temperature},
    )
    if think is not None:
        kwargs["think"] = think
    try:
        resp = await client.chat(**kwargs)
    except TypeError:
        kwargs.pop("think", None)
        resp = await client.chat(**kwargs)
    return resp["message"]["content"]
