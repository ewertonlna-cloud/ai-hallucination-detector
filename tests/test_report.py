"""
tests/test_report.py

Testes do relatório HTML (src/report.py).

Como rodar (na pasta raiz do projeto):
    python3 -m pytest
"""
from src.report import calcular_resumo, gerar_relatorio_html, situacao


def _item(rotulo, veredito, **extras):
    """Cria um resultado de exemplo, já com os campos que o relatório usa."""
    acao = "liberada" if veredito == "fiel" else "bloqueada"
    prioridade = {"fiel": None, "alucinada": "alta", "incerta": "media"}[veredito]
    item = {
        "id": "q1-teste",
        "tipo": "original",
        "rotulo": rotulo,
        "veredito": veredito,
        "motivos": [],
        "resposta": "Uma resposta qualquer.",
        "acao": acao,
        "texto_final": "Uma resposta qualquer." if acao == "liberada" else "Aviso.",
        "prioridade_revisao": prioridade,
    }
    item.update(extras)
    return item


# ---------------------------------------------------------------------------
# Comparação do veredito com o gabarito
# ---------------------------------------------------------------------------

def test_situacao_fiel_reconhecida_e_acerto():
    assert situacao(_item("fiel", "fiel")) == ("acerto", "bom")


def test_situacao_fiel_bloqueada_e_falso_alarme():
    assert situacao(_item("fiel", "alucinada")) == ("falso alarme", "ruim")
    assert situacao(_item("fiel", "incerta")) == ("falso alarme", "ruim")


def test_situacao_alucinada_pega_e_acerto():
    assert situacao(_item("alucinada", "alucinada")) == ("acerto", "bom")


def test_situacao_alucinada_incerta_e_escalada_para_revisao():
    assert situacao(_item("alucinada", "incerta")) == ("escalada para revisão", "aviso")


def test_situacao_alucinada_liberada_passou_despercebida():
    assert situacao(_item("alucinada", "fiel")) == ("passou despercebida", "ruim")


# ---------------------------------------------------------------------------
# Resumo numérico
# ---------------------------------------------------------------------------

def test_resumo_conta_cada_categoria():
    resultados = [
        _item("fiel", "fiel"),
        _item("fiel", "fiel"),
        _item("alucinada", "alucinada"),
        _item("alucinada", "incerta"),
        _item("alucinada", "fiel"),
    ]

    resumo = calcular_resumo(resultados)

    assert resumo["total"] == 5
    assert resumo["liberadas"] == 3          # 2 fiéis + 1 alucinada que passou
    assert resumo["bloqueadas_alta"] == 1
    assert resumo["bloqueadas_media"] == 1
    assert resumo["fieis_ok"] == 2
    assert resumo["total_fieis"] == 2
    assert resumo["falsos_alarmes"] == 0
    assert resumo["alucinacoes_pegas"] == 1
    assert resumo["alucinacoes_escaladas"] == 1
    assert resumo["alucinacoes_perdidas"] == 1
    assert resumo["total_alucinadas"] == 3


# ---------------------------------------------------------------------------
# O arquivo HTML
# ---------------------------------------------------------------------------

def test_relatorio_escapa_html_perigoso(tmp_path):
    perigoso = "<script>alert('oi')</script>"
    resultados = [_item("fiel", "fiel", resposta=perigoso, texto_final=perigoso)]

    caminho = gerar_relatorio_html(resultados, str(tmp_path / "relatorio.html"))
    html = open(caminho, encoding="utf-8").read()

    assert "<script>alert" not in html   # o código não pode entrar como HTML de verdade
    assert "&lt;script&gt;" in html      # aparece como texto, inofensivo


def test_relatorio_tem_a_secao_de_limitacoes(tmp_path):
    caminho = gerar_relatorio_html([_item("fiel", "fiel")], str(tmp_path / "r.html"))
    html = open(caminho, encoding="utf-8").read()

    assert "Limitações conhecidas" in html


def test_relatorio_cria_a_pasta_de_saida_se_nao_existir(tmp_path):
    destino = tmp_path / "pasta" / "nova" / "relatorio.html"

    caminho = gerar_relatorio_html([_item("fiel", "fiel")], str(destino))

    assert destino.exists()
    assert caminho == str(destino)