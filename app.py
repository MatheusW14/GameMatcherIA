from flask import Flask, render_template, request
from ia_logica import processar_recomendacoes, obter_detalhes_jogo, buscar_video_youtube

app = Flask(__name__)

# Dicionário de plataformas (igual ao que usamos antes)
PLATAFORMAS = {"pc": 4, "ps5": 187, "ps4": 18, "xbox": 186, "switch": 7}
VIDEOS_MOCK = {
    "league-of-legends": "vzHrjOMfHPY",  # ID real do trailer de LoL
    "path-of-exile-2": "pT8Lp8578",  # ID real do trailer de PoE 2
    "chess-ultra": "4Lp50fGvK_Y",  # ID de um jogo de Xadrez
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
                            "imagem": "https://media.rawg.io/media/games/0d4/0d4949179929f9e54867c4e51f479427.jpg",
                        }
                    ],
                },
            ]
        else:
            # Caso não seja teste, chama a lógica real
            recomendacoes = processar_recomendacoes(texto, id_plat)

    return render_template("index.html", recomendacoes=recomendacoes)


@app.route("/jogo/<slug>")
def detalhe_jogo(slug):
    # 1. Verifica se é um jogo de teste para evitar gastar API
    if slug in VIDEOS_MOCK:
        # Simulamos os dados do RAWG e do YouTube para teste
        info = {
            "nome": slug.replace("-", " ").title(),
            "descricao": f"Este é um resumo de teste para o jogo {slug}. A IA está em modo Mock.",
            "lancamento": "2026",
            "nota": 99,
            "imagem": "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800",
            "video_id": VIDEOS_MOCK[slug],  # Pega o ID fixo sem chamar a API
        }
    else:

        info = obter_detalhes_jogo(slug)
        if info:
            info["video_id"] = buscar_video_youtube(info["nome"])

    return render_template("detalhe.html", jogo=info)


if __name__ == "__main__":
    app.run(debug=True)
