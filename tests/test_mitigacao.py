"""
tests/test_mitigacao.py

Testes da mitigação (src/mitigacao.py): o que o usuário vê para cada veredito.

Como rodar (na pasta raiz do projeto):
    python3 -m pytest
"""
from src.detector import Resultado
from src.mitigacao import AVISO, decidir

RESPOSTA = "A empresa oferece auxílio-viagem de R$ 1.500."


def test_resposta_fiel_e_liberada_sem_mudar_o_texto():
    decisao = decidir(RESPOSTA, Resultado("fiel"))

    assert decisao.acao == "liberada"
    assert decisao.texto_final == RESPOSTA
    assert decisao.prioridade_revisao is None


def test_resposta_alucinada_e_bloqueada_com_revisao_de_prioridade_alta():
    decisao = decidir(RESPOSTA, Resultado("alucinada", ["número novo"]))

    assert decisao.acao == "bloqueada"
    assert decisao.texto_final == AVISO
    assert decisao.prioridade_revisao == "alta"


def test_resposta_incerta_e_bloqueada_com_revisao_de_prioridade_media():
    decisao = decidir(RESPOSTA, Resultado("incerta", ["não confirmada"]))

    assert decisao.acao == "bloqueada"
    assert decisao.texto_final == AVISO
    assert decisao.prioridade_revisao == "media"


def test_resposta_bloqueada_nunca_vaza_para_o_usuario():
    for veredito in ("alucinada", "incerta"):
        decisao = decidir(RESPOSTA, Resultado(veredito))
        assert RESPOSTA not in decisao.texto_final