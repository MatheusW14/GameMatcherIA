"""
Módulo principal da aplicação web AI Game Matcher (Flask).
Gerencia as rotas de interface, formulários e integração com o motor de IA.
"""

from flask import Flask, render_template, request
from ia_logica import processar_recomendacoes, obter_detalhes_jogo, buscar_video_youtube

app = Flask(__name__)

# Dicionário de plataformas suportadas pela API do RAWG
PLATAFORMAS = {"pc": 4, "ps5": 187, "ps4": 18, "xbox": 186, "switch": 7}

# Banco de dados estático para o Modo de Teste / Portfólio
MOCK_GAME_DATA = {
    "league-of-legends": {
        "nome": "League of Legends",
        "nota": 78,
        "lancamento": "2009",
        "imagem": "https://media.rawg.io/media/games/78b/78bc81e4eb83de72062f925628e12a60.jpg",
        "descricao": "Um MOBA altamente competitivo focado em estratégia e equipe. Perfeito para quem gosta de desafios mentais rápidos.",
        "video_id": "vzHrjOMfHPY",
        "tempo_jogo": 1500,
        "generos": ["MOBA", "Estratégia"],
        "desenvolvedores": ["Riot Games"],
        "plataformas": ["PC", "macOS"],
        "tags": ["Competitivo", "Multiplayer", "Team-Based", "PVP", "Tactical"],
    },
    "path-of-exile-2": {
        "nome": "Path of Exile 2",
        "nota": "TBD",
        "lancamento": "2024 (Beta)",
        "imagem": "https://media.rawg.io/media/screenshots/460/46046e7f8e8f8a1f8e1e8f8a1f8e1e8f.jpg",
        "descricao": "A evolução do RPG de ação. Com um sistema de builds extremamente complexo que desafia até os jogadores mais veteranos.",
        "video_id": "9p2X6V_V_h8",
        "tempo_jogo": 0,
        "generos": ["RPG de Ação", "Hack and Slash"],
        "desenvolvedores": ["Grinding Gear Games"],
        "plataformas": ["PC", "PS5", "Xbox Series X/S"],
        "tags": ["Complexo", "Sombrio", "Deep Lore", "Loot", "Hardcore"],
    },
    "chess-ultra": {
        "nome": "Chess Ultra",
        "nota": 80,
        "lancamento": "2017",
        "imagem": "https://images.unsplash.com/photo-1579373903781-fd5c0c30c4cd?q=80&w=1074&auto=format&fit=crop",
        "descricao": "A experiência definitiva de xadrez com visuais impressionantes em 4K, multijogador sem interrupções e IA aprovada por Grandes Mestres.",
        "video_id": "4Lp50fGvK_Y",
        "tempo_jogo": 50,
        "generos": ["Estratégia", "Tabuleiro", "Simulação"],
        "desenvolvedores": ["Ripstone"],
        "plataformas": ["PC", "PS4", "Xbox One", "Switch"],
        "tags": ["Tático", "Lógica", "Competitivo", "Realista", "VR"],
    },
}


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Handles the main route of the application, processes user input, and generates game recommendations.
    This function supports both a mock testing mode and a real recommendation mode:
    - If the user inputs "TESTE" (case-insensitive) in the "perfil_usuario" field, mock data is returned.
    - Otherwise, it processes the input and fetches recommendations using the `processar_recomendacoes` function.
    Returns:
        str: The rendered HTML template for the index page, including the recommendations.
    Request Parameters:
        - perfil_usuario (str): The user's profile text input.
        - plataforma (str): The name of the platform selected by the user.
    Variables:
        - recomendacoes (list or None): A list of game recommendations or None if no recommendations are available.
        - texto (str): The trimmed user input from the "perfil_usuario" field.
        - plataforma_nome (str): The name of the platform selected by the user.
        - id_plat (int): The platform ID derived from the `PLATAFORMAS` dictionary or defaulted to 4.
    Notes:
        - The mock data is retrieved from the `MOCK_GAME_DATA` dictionary.
        - The real recommendation logic is handled by the `processar_recomendacoes` function.
        - The recommendations are passed to the "index.html" template for rendering.
    """
    recomendacoes = None

    if request.method == "POST":
        texto = request.form.get("perfil_usuario", "").strip()
        plataforma_nome = request.form.get("plataforma")
        id_plat = PLATAFORMAS.get(plataforma_nome, 4)

        # Ativando o Modo de Teste com a palavra-chave
        if texto.upper() == "TESTE":
            recomendacoes = [
                {
                    "tema": "DADOS DE TESTE (MODO MOCK)",
                    "jogos": [
                        {
                            "nome": MOCK_GAME_DATA["league-of-legends"]["nome"],
                            "nota": MOCK_GAME_DATA["league-of-legends"]["nota"],
                            "slug": "league-of-legends",
                            "imagem": MOCK_GAME_DATA["league-of-legends"]["imagem"],
                        },
                        {
                            "nome": MOCK_GAME_DATA["path-of-exile-2"]["nome"],
                            "nota": MOCK_GAME_DATA["path-of-exile-2"]["nota"],
                            "slug": "path-of-exile-2",
                            "imagem": MOCK_GAME_DATA["path-of-exile-2"]["imagem"],
                        },
                    ],
                },
                {
                    "tema": "SUGESTÕES DE ESTRATÉGIA",
                    "jogos": [
                        {
                            "nome": MOCK_GAME_DATA["chess-ultra"]["nome"],
                            "nota": MOCK_GAME_DATA["chess-ultra"]["nota"],
                            "slug": "chess-ultra",
                            "imagem": MOCK_GAME_DATA["chess-ultra"]["imagem"],
                        }
                    ],
                },
            ]
        else:
            # Caso não seja teste, chama a lógica real que aciona a API do Gemini
            recomendacoes = processar_recomendacoes(texto, id_plat)

    return render_template("index.html", recomendacoes=recomendacoes)


@app.route("/jogo/<slug>")
def detalhe_jogo(slug):
    """
    Renderiza a página de detalhes de um jogo com base no slug fornecido.
    Este método utiliza dados mock para testes ou busca informações reais
    de um jogo através de APIs externas (RAWG e YouTube). Caso o slug não
    seja encontrado ou ocorra um erro na comunicação com as APIs, uma
    mensagem de erro é exibida.
    Args:
        slug (str): Identificador único do jogo.
    Returns:
        Response: Um objeto de resposta HTTP que renderiza a página de detalhes
        do jogo ou a página inicial com uma mensagem de erro.
    """
    # 1. Dados para o Modo Mock (Teste)
    # Agora a rota usa os dados ricos do MOCK_GAME_DATA que criamos!
    if slug in MOCK_GAME_DATA:
        info = MOCK_GAME_DATA[slug]
    else:
        # 2. Lógica Real (Busca no RAWG e Youtube)
        info = obter_detalhes_jogo(slug)
        if info:
            info["video_id"] = buscar_video_youtube(info["nome"])

    # Tratamento de erro elegante caso a API falhe ou a URL seja inválida
    if not info:
        return (
            render_template(
                "index.html",
                recomendacoes={
                    "erro": "Dossiê não encontrado ou falha de comunicação com o servidor RAWG."
                },
            ),
            404,
        )

    return render_template("detalhe.html", jogo=info)


if __name__ == "__main__":
    app.run(debug=True)
