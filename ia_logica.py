"""
Módulo principal de integração de APIs (Gemini, RAWG e YouTube).
Gerencia a análise de perfil do usuário e a busca por dados e trailers de jogos.
"""

import os
import json
import datetime
import random
import requests
from dotenv import load_dotenv
from google import genai
from googleapiclient.discovery import build
from googleapiclient.errors import (
    HttpError,
)  # <-- Adicionado para tratar erros do YouTube

# Carregamos as chaves do seu arquivo .env
load_dotenv("chaves_api.env")
CHAVE_GEMINI = os.getenv("GEMINI_API_KEY")
CHAVE_RAWG = os.getenv("RAWG_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not CHAVE_GEMINI:
    raise ValueError(
        "ERRO: A chave do Gemini não foi carregada. Verifique o arquivo chaves_api.env"
    )

cliente_gemini = genai.Client(api_key=CHAVE_GEMINI)


def processar_recomendacoes(texto_usuario, plataforma_id):
    """
    Função mestra que recebe o texto e a plataforma e retorna
    um dicionário com os jogos encontrados.
    """
    prompt = f"""
    Analise: "{texto_usuario}"
    Crie perfis de busca independentes. Retorne APENAS JSON:
    {{ "perfis": [ {{"tema": "Título", "termo_busca": "termo", "epoca": "recente/qualquer"}} ] }}
    """

    try:
        resposta = cliente_gemini.models.generate_content(
            model="gemini-3-flash-preview", contents=prompt
        )
        corpo = resposta.text.strip()
        if corpo.startswith("```json"):
            corpo = corpo[7:-3].strip()

        dados_ia = json.loads(corpo)
        perfis = dados_ia.get("perfis", [])
    except (
        json.JSONDecodeError,
        genai.errors.APIError,
    ) as e:  # Captura erros específicos do Gemini e JSON
        print(f"Erro na IA: {e}")
        return {"erro": "Falha na análise da IA"}

    resultados_finais = []
    ano_atual = datetime.datetime.now().year

    for p in perfis:
        params = {
            "key": CHAVE_RAWG,
            "search": p["termo_busca"],
            "platforms": plataforma_id,
            "metacritic": "70,100",
            "ordering": "-added",
            "page_size": 15,
        }

        if p["epoca"] == "recente":
            params["dates"] = f"{ano_atual-5}-01-01,{ano_atual}-12-31"

        try:
            res = requests.get(
                "[https://api.rawg.io/api/games](https://api.rawg.io/api/games)",
                params=params,
                timeout=10,
            )
            res.raise_for_status()  # Lança erro se a resposta não for 200 OK

            jogos = res.json().get("results", [])
            if jogos:
                selecao = random.sample(jogos, min(3, len(jogos)))
                lista_jogos_limpa = []
                for j in selecao:
                    lista_jogos_limpa.append(
                        {
                            "nome": j["name"],
                            "slug": j["slug"],
                            "nota": j.get("metacritic", "N/A"),
                            "imagem": j.get("background_image"),
                        }
                    )
                resultados_finais.append(
                    {"tema": p["tema"], "jogos": lista_jogos_limpa}
                )

        except (
            requests.exceptions.RequestException
        ) as e:  # Trata erros do RAWG corretamente
            print(f"Erro ao buscar no RAWG: {e}")

    return resultados_finais


def obter_detalhes_jogo(slug):
    """Busca o máximo de informações detalhadas do RAWG."""
    load_dotenv("chaves_api.env")
    api_key = os.getenv("RAWG_API_KEY")
    url = f"[https://api.rawg.io/api/games/](https://api.rawg.io/api/games/){slug}?key={api_key}"

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()

        d = res.json()
        return {
            "nome": d.get("name"),
            "descricao": d.get("description_raw") or "Descrição não disponível.",
            "lancamento": d.get("released", "N/A"),
            "nota": d.get("metacritic", "N/A"),
            "imagem": d.get("background_image"),
            "tempo_jogo": d.get("playtime", 0),
            "generos": [g["name"] for g in d.get("genres", [])],
            "plataformas": [p["platform"]["name"] for p in d.get("platforms", [])],
            "desenvolvedores": [dev["name"] for dev in d.get("developers", [])],
            "tags": [t["name"] for t in d.get("tags", [])[:5]],
        }
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar detalhes no RAWG: {e}")
    return None


def buscar_video_youtube(nome_jogo):
    """Busca o ID do vídeo no YouTube com sistema de Cache para economizar cota."""
    arquivo_cache = "youtube_cache.json"
    cache = {}

    if os.path.exists(arquivo_cache):
        with open(arquivo_cache, "r", encoding="utf-8") as f:
            cache = json.load(f)

    if nome_jogo in cache:
        return cache[nome_jogo]

    load_dotenv("chaves_api.env")
    api_key = os.getenv("YOUTUBE_API_KEY")

    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        request = youtube.search().list(
            q=f"{nome_jogo} official trailer",
            part="snippet",
            type="video",
            maxResults=1,
        )
        response = request.execute()

        if response["items"]:
            video_id = response["items"][0]["id"]["videoId"]
            cache[nome_jogo] = video_id
            with open(arquivo_cache, "w", encoding="utf-8") as f:
                json.dump(cache, f)
            return video_id

    except HttpError as e:  # Trata especificamente erros da API do Google
        print(f"Erro na API do YouTube: {e}")

    return None
