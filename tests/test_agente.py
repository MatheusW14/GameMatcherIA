"""Testes do agente com Gemini e RAWG simulados (não gastam cota nem precisam de chave)."""

import os
import sys
from types import SimpleNamespace

from google import genai
from google.genai import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agente  # noqa: E402
from agente import AgenteJogos  # noqa: E402


def jogo_rawg(slug, nome, **extra):
    base = {
        "slug": slug,
        "name": nome,
        "released": "2020-05-01",
        "metacritic": 88,
        "rating": 4.3,
        "playtime": 12,
        "background_image": f"https://img/{slug}.jpg",
        "genres": [{"name": "Adventure"}],
        "tags": [{"name": "Singleplayer"}, {"name": "Atmospheric"}],
    }
    base.update(extra)
    return base


class RespostaFalsa:
    def __init__(self, chamadas=None, texto=None):
        self.function_calls = [SimpleNamespace(name=n, args=a) for n, a in (chamadas or [])]
        self.text = texto
        parts = [types.Part(text=texto)] if texto else []
        self.candidates = [SimpleNamespace(content=types.Content(role="model", parts=parts))]


class ClienteFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.configs = []
        self.models = self

    def generate_content(self, model, contents, config):
        self.configs.append(config)
        return self.respostas.pop(0)


def rawg_falso(monkeypatch, por_caminho):
    chamadas = []

    def fake_get(url, params=None, timeout=None):
        chamadas.append((url, dict(params)))
        caminho = url.replace(agente.RAWG_API, "")
        dados = por_caminho[caminho]

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return dados

        return R()

    monkeypatch.setattr(agente.requests, "get", fake_get)
    return chamadas


def test_so_recomenda_jogos_que_as_ferramentas_retornaram(monkeypatch):
    rawg = rawg_falso(monkeypatch, {"/games": {"results": [jogo_rawg("hades", "Hades")]}})
    cliente = ClienteFalso(
        [
            RespostaFalsa(chamadas=[("verificar_jogo", {"nome": "Hades"})]),
            RespostaFalsa(
                texto='```json\n{"grupos": [{"tema": "Ação", "jogos": ['
                '{"slug": "hades", "motivo": "Ação rápida."},'
                '{"slug": "jogo-inventado", "motivo": "Não existe."},'
                '{"slug": "hades", "motivo": "Repetido."}]}]}\n```'
            ),
        ]
    )
    grupos, passos = AgenteJogos(cliente, "KEY", 4).executar("quero ação")

    assert [j["slug"] for j in grupos[0]["jogos"]] == ["hades"]
    assert grupos[0]["jogos"][0]["imagem"] == "https://img/hades.jpg"
    assert grupos[0]["jogos"][0]["motivo"] == "Ação rápida."
    assert passos[0]["ferramenta"] == "verificar_jogo"
    assert rawg[0][1]["key"] == "KEY"


def test_plataforma_e_aplicada_pelo_codigo_nao_pelo_modelo(monkeypatch):
    rawg = rawg_falso(monkeypatch, {"/games": {"results": []}})
    cliente = ClienteFalso(
        [
            # o modelo tenta passar outra plataforma: o argumento extra é rejeitado
            RespostaFalsa(chamadas=[("buscar_jogos_por_filtros", {"generos": "rpg", "platforms": 999})]),
            RespostaFalsa(chamadas=[("buscar_jogos_por_filtros", {"generos": "indie", "ano_minimo": 2018.0})]),
            RespostaFalsa(texto='{"grupos": []}'),
        ]
    )
    agente_ = AgenteJogos(cliente, "KEY", 187)
    grupos, passos = agente_.executar("qualquer coisa")

    assert grupos == []
    assert "erro" in passos[0]["resumo"]  # argumento inválido não derruba o agente
    url, params = rawg[0]
    assert params["platforms"] == 187
    assert params["dates"].startswith("2018-01-01,")  # float do Gemini virou int


def test_limite_de_rodadas_forca_resposta_final(monkeypatch):
    rawg_falso(monkeypatch, {"/games": {"results": [jogo_rawg("celeste", "Celeste")]}})
    loop = [RespostaFalsa(chamadas=[("verificar_jogo", {"nome": f"x{i}"})]) for i in range(agente.MAX_RODADAS)]
    final = RespostaFalsa(texto='{"grupos": [{"tema": "T", "jogos": [{"slug": "celeste", "motivo": "m"}]}]}')
    cliente = ClienteFalso(loop + [final])
    grupos, _ = AgenteJogos(cliente, "KEY", 4).executar("plataforma")

    assert grupos[0]["jogos"][0]["slug"] == "celeste"
    assert cliente.configs[-1].tool_config.function_calling_config.mode == "NONE"


def test_json_invalido_aciona_o_plano_b(monkeypatch):
    rawg_falso(monkeypatch, {"/games": {"results": [jogo_rawg("hades", "Hades")]}})
    cliente = ClienteFalso(
        [
            RespostaFalsa(chamadas=[("verificar_jogo", {"nome": "Hades"})]),
            RespostaFalsa(texto="Recomendo Hades, é ótimo!"),  # sem JSON
            RespostaFalsa(texto='{"grupos": [{"tema": "T", "jogos": [{"slug": "hades", "motivo": "m"}]}]}'),
        ]
    )
    grupos, _ = AgenteJogos(cliente, "KEY", 4).executar("x")
    assert grupos[0]["jogos"][0]["slug"] == "hades"
    assert cliente.configs[-1].response_schema is not None


def test_verificar_jogo_mede_similaridade(monkeypatch):
    rawg_falso(
        monkeypatch,
        {"/games": {"results": [jogo_rawg("the-witcher-3-wild-hunt", "The Witcher 3: Wild Hunt"),
                                jogo_rawg("outro", "Totalmente Diferente")]}},
    )
    r = AgenteJogos(None, "KEY", 4).verificar_jogo("The Witcher 3")
    assert r["encontrado"] and r["resultados"][0]["slug"] == "the-witcher-3-wild-hunt"
    assert r["resultados"][0]["similaridade"] >= 0.9


def test_erro_do_rawg_nao_vaza_a_chave(monkeypatch):
    def quebrado(url, params=None, timeout=None):
        raise agente.requests.exceptions.ConnectionError(f"falha em {url}?key={params['key']}")

    monkeypatch.setattr(agente.requests, "get", quebrado)
    r = AgenteJogos(None, "SEGREDO", 4).verificar_jogo("Hades")
    assert "SEGREDO" not in str(r)


def test_sdk_consegue_gerar_declaracoes_das_ferramentas():
    cliente = genai.Client(api_key="chave-falsa")
    ag = AgenteJogos(cliente, "KEY", 4)
    for f in (ag.buscar_jogos_por_filtros, ag.verificar_jogo, ag.detalhes_jogo):
        decl = types.FunctionDeclaration.from_callable(client=cliente, callable=f)
        assert decl.name == f.__name__ and decl.description
