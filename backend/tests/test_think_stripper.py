"""ThinkStripper : retire les blocs <think>…</think> d'un flux de tokens (chat épuré)."""
from services.llm import ThinkStripper


def run(pieces):
    s = ThinkStripper()
    out = "".join(s.feed(p) for p in pieces)
    return out + s.flush()


class TestThinkStripper:
    def test_no_think_passthrough(self):
        assert run(["Bonjour ", "le ", "monde"]) == "Bonjour le monde"

    def test_strips_full_block_single_chunk(self):
        assert run(["<think>je réfléchis</think>Réponse"]) == "Réponse"

    def test_keeps_text_before_and_after(self):
        assert run(["Avant <think>secret</think> après"]) == "Avant  après"

    def test_tag_split_across_chunks(self):
        # <think> coupé en deux tokens, puis </think> aussi
        pieces = ["Salut <thi", "nk>caché ici</thi", "nk>fin"]
        assert run(pieces) == "Salut fin"

    def test_unclosed_think_is_dropped(self):
        # bloc de raisonnement non terminé en fin de flux → non affiché
        assert run(["Texte <think>raisonnement sans fin"]) == "Texte "

    def test_multiple_blocks(self):
        assert run(["a<think>x</think>b<think>y</think>c"]) == "abc"

    def test_token_by_token(self):
        full = "Hello <think>reasoning</think>World"
        assert run(list(full)) == "Hello World"
