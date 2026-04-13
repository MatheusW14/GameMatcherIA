"""
Módulo principal da aplicação web AI Game Matcher (Flask).
Gerencia as rotas de interface, formulários e integração com o motor de IA.
"""

from flask import Flask, render_template, request
import psycopg2
import os
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
        "tags": [
            "Competitivo",
            "Multijogador",
            "Foco em Equipe",
            "JxJ (PvP)",
            "Tático",
        ],
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
        "tags": [
            "Complexo",
            "Sombrio",
            "História Profunda",
            "Saque (Loot)",
            "Extremo",
        ],
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
        "tags": [
            "Tático",
            "Lógica",
            "Competitivo",
            "Realista",
            "Realidade Virtual",
        ],
    },
}


@app.route("/", methods=["GET", "POST"])
def index():
    recomendacoes = None

    if request.method == "POST":
        texto = request.form.get("perfil_usuario", "").strip()
        plataforma_nome = request.form.get("plataforma")
        id_plat = PLATAFORMAS.get(plataforma_nome, 4)

        # --- INÍCIO DA INTEGRAÇÃO COM O BANCO DE DADOS ---
        if texto and texto.upper() != "TESTE":
            try:
                # Liga ao banco do container usando a variável do docker-compose
                conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
                cur = conn.cursor()

                # Cria a tabela se ela ainda não existir
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS historico_buscas (
                        id SERIAL PRIMARY KEY,
                        termo_buscado TEXT NOT NULL,
                        data_busca TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Salva o humor gamer pesquisado
                cur.execute(
                    "INSERT INTO historico_buscas (termo_buscado) VALUES (%s)", (texto,)
                )

                conn.commit()
                cur.close()
                conn.close()
                print("Busca guardada na base de dados com sucesso!")
            except Exception as e:
                print(f"Erro na base de dados: {e}")
        # --- FIM DA INTEGRAÇÃO ---

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
    if slug in MOCK_GAME_DATA:
        info = MOCK_GAME_DATA[slug]
    else:
        info = obter_detalhes_jogo(slug)
        if info:
            info["video_id"] = buscar_video_youtube(info["nome"])

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
    app.run(host="0.0.0.0", port=5000, debug=True)
