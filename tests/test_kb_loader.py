"""
tests/test_kb_loader.py

Testes do leitor da base de conhecimento (src/kb_loader.py).

Como rodar (na pasta raiz do projeto):
    python3 -m pytest
"""
from pathlib import Path

from src.kb_loader import carregar_base, carregar_secoes

RAIZ = Path(__file__).resolve().parents[1]


def test_divide_o_documento_em_secoes(tmp_path):
    arquivo = tmp_path / "doc.md"
    arquivo.write_text("# Título\n\n## A\n\ntexto a\n\n## B\n\ntexto b\n", encoding="utf-8")

    secoes = carregar_secoes(str(arquivo))

    assert [s.titulo for s in secoes] == ["A", "B"]
    assert [s.texto for s in secoes] == ["texto a", "texto b"]


def test_titulo_do_documento_nao_vira_secao(tmp_path):
    arquivo = tmp_path / "doc.md"
    arquivo.write_text("# Título do documento\n\n## Única\n\ntexto\n", encoding="utf-8")

    secoes = carregar_secoes(str(arquivo))

    assert len(secoes) == 1
    assert secoes[0].titulo == "Única"


def test_junta_as_linhas_da_secao_em_um_texto_so(tmp_path):
    arquivo = tmp_path / "doc.md"
    arquivo.write_text("## A\n\nlinha 1\nlinha 2\n", encoding="utf-8")

    secoes = carregar_secoes(str(arquivo))

    assert secoes[0].texto == "linha 1 linha 2"


def test_ignora_secao_sem_texto(tmp_path):
    arquivo = tmp_path / "doc.md"
    arquivo.write_text("## Vazia\n\n## Cheia\n\ntexto\n", encoding="utf-8")

    secoes = carregar_secoes(str(arquivo))

    assert [s.titulo for s in secoes] == ["Cheia"]


def test_guarda_o_nome_do_arquivo_na_secao(tmp_path):
    arquivo = tmp_path / "politica_x.md"
    arquivo.write_text("## A\n\ntexto\n", encoding="utf-8")

    assert carregar_secoes(str(arquivo))[0].documento == "politica_x.md"


def test_base_real_tem_as_cinco_secoes_de_ferias():
    secoes = carregar_base(str(RAIZ / "data" / "knowledge_base"))

    titulos = [s.titulo for s in secoes]
    assert len(secoes) == 5
    assert "Fracionamento" in titulos
    assert "Venda de férias (abono pecuniário)" in titulos