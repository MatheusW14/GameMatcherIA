from flask import Flask, render_template, request
from ia_logica import processar_recomendacoes

app = Flask(__name__)

# Dicionário de plataformas (igual ao que usamos antes)
PLATAFORMAS = {"pc": 4, "ps5": 187, "ps4": 18, "xbox": 186, "switch": 7}
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
}


@app.route("/", methods=["GET", "POST"])
def index():
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
                            "nome": "League of Legends",
                            "nota": 78,
                            "slug": "league-of-legends",
                            "imagem": "https://media.rawg.io/media/games/78b/78bc81e4eb83de72062f925628e12a60.jpg",
                        },
                        {
                            "nome": "Path of Exile 2",
                            "nota": "TBD",
                            "slug": "path-of-exile-2",
                            "imagem": "https://media.rawg.io/media/screenshots/460/46046e7f8e8f8a1f8e1e8f8a1f8e1e8f.jpg",
                        },
                    ],
                },
                {
                    "tema": "SUGESTÕES DE ESTRATÉGIA",
                    "jogos": [
                        {
                            "nome": "Chess Ultra",
                            "nota": 80,
                            "slug": "chess-ultra",
                            "imagem": "https://media.rawg.io/media/games/0d4/0d4949179929f9e54867c4e51f479427.jpg",
                        }
                    ],
                },
            ]
        else:
            # Caso não seja teste, chama a lógica real
            recomendacoes = processar_recomendacoes(texto, id_plat)

    return render_template("index.html", recomendacoes=recomendacoes)


# Mock data for video IDs
VIDEOS_MOCK = {
    "league-of-legends": "vzHrjOMfHPY",
    "path-of-exile-2": "9p2X6V_V_h8",
}


@app.route("/jogo/<slug>")
def detalhe_jogo(slug):
    # 1. Dados para o Modo Mock (Teste)
    if slug in VIDEOS_MOCK:
        info = {
            "nome": slug.replace("-", " ").title(),
            "descricao": f"Este é um resumo de teste para o jogo {slug}. A IA está em modo Mock.",
            "lancamento": "2026",
            "nota": 99,
            "imagem": "https://media.rawg.io/media/games/78b/78bc81e4eb83de72062f925628e12a60.jpg",
            "video_id": VIDEOS_MOCK[slug],
            "tempo_jogo": 100,  # Adicionado para evitar erro
            "generos": ["Teste", "IA"],
            "plataformas": ["PC", "Web"],
            "desenvolvedores": ["Seu Nome"],
            "tags": ["Inovação", "Python"],
        }
    else:
        # 2. Busca Real
        from ia_logica import obter_detalhes_jogo, buscar_video_youtube

        info = obter_detalhes_jogo(slug)
        if info:
            info["video_id"] = buscar_video_youtube(info["nome"])

    if not info:
        return "Jogo não encontrado", 404

    return render_template("detalhe.html", jogo=info)


if __name__ == "__main__":
    app.run(debug=True)
