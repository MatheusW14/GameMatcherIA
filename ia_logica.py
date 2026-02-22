import os
import requests
import json
import datetime
import random
from dotenv import load_dotenv
from google import genai
from googleapiclient.discovery import build

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

    # 1. IA analisa o perfil
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
    except Exception:
        return {"erro": "Falha na análise da IA"}

    # 2. Busca no RAWG
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

        res = requests.get(
            "https://api.rawg.io/api/games",
            params=params,
            timeout=10,
        )

        if res.status_code == 200:
            jogos = res.json().get("results", [])
            if jogos:
                # Sorteamos 3 para dar aquela variedade que você queria
                selecao = random.sample(jogos, min(3, len(jogos)))

                lista_jogos_limpa = []
                for j in selecao:
                    lista_jogos_limpa.append(
                        {
                            "nome": j["name"],
                            "slug": j["slug"],
                            "nota": j.get("metacritic", "N/A"),
                            "imagem": j.get(
                                "background_image"
                            ),  # Agora pegamos a imagem para o site!
                        }
                    )

                resultados_finais.append(
                    {"tema": p["tema"], "jogos": lista_jogos_limpa}
                )

    return resultados_finais


def obter_detalhes_jogo(slug):
    """Busca informações detalhadas de um jogo específico pelo seu slug."""
    load_dotenv("chaves_api.env")
    api_key = os.getenv("CHAVE_RAWG")

    url = f"https://api.rawg.io/api/games/{slug}?key={api_key}"

    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return {
                "nome": d.get("name"),
                "descricao": d.get("description_raw") or "Descrição não disponível.",
                "lancamento": d.get("released", "N/A"),
                "nota": d.get("metacritic", "N/A"),
                "imagem": d.get("background_image"),
                "site": d.get("website"),
            }
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar detalhes: {e}")
    return None


def buscar_video_youtube(nome_jogo):
    """Busca o ID do vídeo no YouTube com sistema de Cache para economizar cota."""
    arquivo_cache = "youtube_cache.json"

    # 1. Tenta carregar o cache existente
    cache = {}
    if os.path.exists(arquivo_cache):
        with open(arquivo_cache, "r", encoding="utf-8") as f:
            cache = json.load(f)

    # 2. Se o jogo já estiver no cache, retorna o ID sem gastar API
    if nome_jogo in cache:
        return cache[nome_jogo]

    # 3. Se não estiver, faz a busca na API do Google
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

            # 4. Salva o novo ID no arquivo de cache para a próxima vez
            cache[nome_jogo] = video_id
            with open(arquivo_cache, "w", encoding="utf-8") as f:
                json.dump(cache, f)
            return video_id

    except Exception as e:
        print(f"Erro na API do YouTube: {e}")

    return None
