"""
tests/test_corruptor.py

Testes do gerador de alucinações (src/corruptor.py). O mais importante aqui é
garantir as REGRAS do dataset: sem elas, os números do detector não valem nada.
  - a paráfrase correta nunca pode mudar um número
  - cada alucinação difere da resposta original
  - a geração é reproduzível (mesma semente, mesmo dataset)

Como rodar (na pasta raiz do projeto):
    python3 -m pytest
"""
import json
import random
import re
from pathlib import Path

import pytest

from src.corruptor import (
    gerar_dataset,
    inverter_negacao,
    parafrasear,
    trocar_entidade,
    trocar_numero,
)

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _rodar_na_raiz(monkeypatch):
    """Os caminhos do projeto são relativos à pasta raiz; garante que o teste rode de lá."""
    monkeypatch.chdir(RAIZ)


def _numeros(texto: str) -> list[str]:
    return re.findall(r"\d+", texto)


# ---------------------------------------------------------------------------
# Funções de corrupção, uma a uma
# ---------------------------------------------------------------------------

def test_trocar_numero_troca_um_numero_e_preserva_fracao():
    original = "Pode vender até 1/3 das férias, com 15 dias de antecedência."

    nova, descricao = trocar_numero(original, random.Random(0))

    assert "1/3" in nova          # a fração não é mexida
    assert "15" not in nova       # o número solto foi trocado
    assert "15" in descricao


def test_trocar_numero_sem_numeros_devolve_none():
    assert trocar_numero("Texto sem número nenhum.", random.Random(0)) is None


def test_trocar_entidade_troca_o_termo_do_dominio():
    nova, _ = trocar_entidade("O gestor direto aprova o pedido.")
    assert nova == "O diretor financeiro aprova o pedido."


def test_trocar_entidade_sem_termo_conhecido_devolve_none():
    assert trocar_entidade("Frase sem nenhum termo da tabela.") is None


def test_inverter_negacao_inverte_o_sentido():
    nova, _ = inverter_negacao("É preciso solicitar com antecedência.")
    assert nova == "Não é preciso solicitar com antecedência."


def test_inverter_negacao_sem_padrao_conhecido_devolve_none():
    assert inverter_negacao("Frase qualquer.") is None


# ---------------------------------------------------------------------------
# Regras do dataset completo
# ---------------------------------------------------------------------------

def test_parafrase_nunca_altera_numeros():
    pares = json.loads(Path("data/generated/qa_corretos.json").read_text(encoding="utf-8"))
    for par in pares:
        resultado = parafrasear(par["resposta_correta"])
        if resultado is None:
            continue
        nova, _ = resultado
        assert _numeros(nova) == _numeros(par["resposta_correta"]), par["id"]


def test_dataset_tem_30_itens_10_fieis_e_20_alucinadas():
    dataset = gerar_dataset()

    assert len(dataset) == 30
    assert sum(item["rotulo"] == "fiel" for item in dataset) == 10
    assert sum(item["rotulo"] == "alucinada" for item in dataset) == 20


def test_geracao_e_reproduzivel():
    assert gerar_dataset() == gerar_dataset()


def test_toda_alucinada_difere_da_resposta_original():
    dataset = gerar_dataset()
    original_por_par = {i["id_par"]: i["resposta"] for i in dataset if i["tipo"] == "original"}

    for item in dataset:
        if item["rotulo"] == "alucinada":
            assert item["resposta"] != original_por_par[item["id_par"]], item["id"]


def test_troca_numerica_muda_exatamente_um_numero():
    dataset = gerar_dataset()
    original_por_par = {i["id_par"]: i["resposta"] for i in dataset if i["tipo"] == "original"}

    for item in dataset:
        if item["tipo"] != "troca_numerica":
            continue
        antes = _numeros(original_por_par[item["id_par"]])
        depois = _numeros(item["resposta"])
        assert len(antes) == len(depois), item["id"]
        assert sum(a != b for a, b in zip(antes, depois)) == 1, item["id"]


def test_fabricacao_mantem_a_resposta_original_e_adiciona_no_final():
    dataset = gerar_dataset()
    original_por_par = {i["id_par"]: i["resposta"] for i in dataset if i["tipo"] == "original"}

    for item in dataset:
        if item["tipo"] == "fabricacao":
            original = original_por_par[item["id_par"]]
            assert item["resposta"].startswith(original), item["id"]
            assert len(item["resposta"]) > len(original), item["id"]