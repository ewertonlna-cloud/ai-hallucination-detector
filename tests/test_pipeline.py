"""
tests/test_pipeline.py

Testes do pipeline (run_pipeline.py). O detector é trocado por uma versão
falsa, então nenhum teste aqui baixa ou roda o modelo de IA.

Como rodar (na pasta raiz do projeto):
    python3 -m pytest
"""
import csv

from run_pipeline import processar, salvar_csv
from src.detector import Resultado
from src.mitigacao import AVISO

DATASET = [
    {"id": "a", "tipo": "original", "rotulo": "fiel", "fonte": "F", "resposta": "Resposta boa."},
    {"id": "b", "tipo": "troca_numerica", "rotulo": "alucinada", "fonte": "F", "resposta": "Resposta ruim."},
]


def _detector_falso(fonte, resposta):
    if resposta == "Resposta boa.":
        return Resultado("fiel")
    return Resultado("alucinada", ["motivo de teste"])


def test_processar_libera_a_fiel_e_bloqueia_a_alucinada():
    resultados = processar(DATASET, detector=_detector_falso)

    boa, ruim = resultados
    assert boa["acao"] == "liberada"
    assert boa["texto_final"] == "Resposta boa."
    assert ruim["acao"] == "bloqueada"
    assert ruim["texto_final"] == AVISO
    assert ruim["prioridade_revisao"] == "alta"


def test_processar_mantem_os_campos_originais_do_item():
    resultados = processar(DATASET, detector=_detector_falso)

    assert [r["id"] for r in resultados] == ["a", "b"]
    assert resultados[1]["rotulo"] == "alucinada"
    assert resultados[1]["motivos"] == ["motivo de teste"]


def test_processar_nao_altera_o_dataset_original():
    processar(DATASET, detector=_detector_falso)

    assert "veredito" not in DATASET[0]


def test_salvar_csv_escreve_cabecalho_e_junta_os_motivos(tmp_path):
    resultados = processar(DATASET, detector=_detector_falso)
    resultados[1]["motivos"] = ["primeiro motivo", "segundo motivo"]
    caminho = tmp_path / "saida" / "resultados.csv"

    salvar_csv(resultados, str(caminho))

    with open(caminho, newline="", encoding="utf-8-sig") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert len(linhas) == 2
    assert linhas[0]["id"] == "a"
    assert linhas[1]["veredito"] == "alucinada"
    assert linhas[1]["motivos"] == "primeiro motivo | segundo motivo"


def test_salvar_csv_usa_utf8_com_bom_para_o_excel_abrir_os_acentos(tmp_path):
    caminho = tmp_path / "resultados.csv"

    salvar_csv(processar(DATASET, detector=_detector_falso), str(caminho))

    assert caminho.read_bytes().startswith(b"\xef\xbb\xbf")