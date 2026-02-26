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
RAWG_API_KEY = os.getenv("RAWG_API_KEY")
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
            "key": RAWG_API_KEY,
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
                "https://api.rawg.io/api/games",
                params=params,
                timeout=10,
            )
            res.raise_for_status()  # Lança erro se a resposta não for 200 OK

            jogos = res.json().get("results", [])
            if jogos:
                selecao = random.sample(jogos, min(5, len(jogos)))
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


def traduzir_dados_com_ia(descricao_ingles, tags_ingles):
    """Usa o Gemini para traduzir a descrição e as tags do jogo para PT-BR."""
    if not descricao_ingles or len(descricao_ingles) < 5:
        return "Descrição não disponível.", tags_ingles

    prompt = f"""
    Você é o sistema do AI Game Matcher.
    Traduza a descrição e as tags a seguir estritamente para o Português do Brasil (PT-BR).
    
    REGRA IMPORTANTE PARA AS TAGS: Traduza termos gamers para o português sempre que possível. 
    (Exemplo: de "Singleplayer" para "Um Jogador", de "Story Rich" para "Rica em História", de "Atmospheric" para "Atmosférico").
    Limpe qualquer código HTML perdido (como &#39;).
    
    RETORNE APENAS UM JSON VÁLIDO. NÃO USE MARKDOWN EXTRA. O formato deve ser:
    {{
        "descricao_ptbr": "texto traduzido aqui",
        "tags_ptbr": ["tag traduzida 1", "tag traduzida 2", "tag traduzida 3"]
    }}

    Descrição original: {descricao_ingles}
    Tags originais: {tags_ingles}
    """

    try:
        resposta = cliente_gemini.models.generate_content(
            model="gemini-3-flash-preview", contents=prompt
        )
        corpo = resposta.text.strip()

        # Limpeza caso a IA responda com marcação de bloco de código
        if corpo.startswith("```json"):
            corpo = corpo[7:-3].strip()
        elif corpo.startswith("```"):
            corpo = corpo[3:-3].strip()

        dados = json.loads(corpo)
        return dados.get("descricao_ptbr", descricao_ingles), dados.get(
            "tags_ptbr", tags_ingles
        )
    except (json.JSONDecodeError, genai.errors.APIError) as e:
        print(f"Erro na tradução da IA: {e}")
        return descricao_ingles, tags_ingles


def obter_detalhes_jogo(slug):
    """Busca informações detalhadas de um jogo específico pelo seu slug."""
    load_dotenv("chaves_api.env", override=True)
    api_key = os.getenv("RAWG_API_KEY")

    url = f"https://api.rawg.io/api/games/{slug}?key={api_key}"

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()

        d = res.json()

        # 1. Pega os textos brutos em inglês do RAWG
        descricao_bruta = d.get("description_raw") or "Sem descrição."
        tags_brutas = [t["name"] for t in d.get("tags", [])[:5]]

        # 2. Passa pela nossa IA tradutora!
        descricao_ptbr, tags_ptbr = traduzir_dados_com_ia(descricao_bruta, tags_brutas)

        return {
            "nome": d.get("name"),
            "descricao": descricao_ptbr,
            "lancamento": d.get("released", "N/A"),
            "nota": d.get("metacritic", "N/A"),
            "imagem": d.get("background_image"),
            "tempo_jogo": d.get("playtime", 0),
            "generos": [g["name"] for g in d.get("genres", [])],
            "plataformas": [p["platform"]["name"] for p in d.get("platforms", [])],
            "desenvolvedores": [dev["name"] for dev in d.get("developers", [])],
            "tags": tags_ptbr,  # <-- Agora as tags também estão em PT-BR
        }
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar detalhes no RAWG: {e}")
    return None


def buscar_video_youtube(nome_jogo):
    """Busca o ID do vídeo no YouTube com sistema de Cache à prova de falhas."""
    arquivo_cache = "youtube_cache.json"
    cache = {}

    # 1. PROTEÇÃO CONTRA CORRUPÇÃO DE ARQUIVO (Tratamento de Exceção)
    if os.path.exists(arquivo_cache):
        try:
            with open(arquivo_cache, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            print("AVISO DE SISTEMA: Cache do YouTube corrompido. Recriando estrutura.")
            cache = {}  # Reseta graciosamente em vez de quebrar a aplicação

    # Retorna do cache instantaneamente se já existir
    if nome_jogo in cache:
        return cache[nome_jogo]

    # 2. USO DE VARIÁVEL GLOBAL (Evita leitura redundante do disco)
    if not YOUTUBE_API_KEY:
        print("Erro: YOUTUBE_API_KEY não configurada no ambiente.")
        return None

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        # 3. BUSCA MAIS PRECISA ("game" adicionado para evitar falsos positivos)
        query_busca = f"{nome_jogo} game official trailer"

        # pylint: disable=no-member
        request = youtube.search().list(
            q=query_busca,
            part="snippet",
            type="video",
            maxResults=1,
        )
        response = request.execute()

        if response["items"]:
            video_id = response["items"][0]["id"]["videoId"]
            cache[nome_jogo] = video_id

            # Salva o JSON formatado (indent=4) para ficar bonito se um recrutador abrir o arquivo
            with open(arquivo_cache, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=4)

            return video_id

    except HttpError as e:
        print(f"Erro de comunicação com a API do YouTube: {e}")

    return None
