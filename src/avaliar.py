"""
src/avaliar.py

Mede quanto o detector acerta. Roda o detector em cada item do dataset de
teste (data/generated/dataset_teste.json) e compara o veredito dele com o
rótulo que a gente já sabe (fiel ou alucinada).

Como rodar (na pasta raiz do projeto):
    python3 -m src.avaliar
"""
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable

from src.detector import Resultado, verificar_regras

ARQUIVO_DATASET = "data/generated/dataset_teste.json"
ORDEM_TIPOS = [
    "original",
    "parafrase_correta",
    "troca_numerica",
    "troca_entidade",
    "inversao_negacao",
    "fabricacao",
]


def carregar_dataset(caminho: str = ARQUIVO_DATASET) -> list[dict]:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def avaliar(classificador: Callable[[str, str], Resultado], dataset: list[dict]) -> list[dict]:
    """Roda o classificador em cada item e guarda o veredito junto do rótulo real."""
    resultados = []
    for item in dataset:
        resultado = classificador(item["fonte"], item["resposta"])
        resultados.append({**item, "veredito": resultado.veredito, "motivos": resultado.motivos})
    return resultados


def imprimir_relatorio(nome: str, resultados: list[dict]) -> None:
    por_tipo: dict[str, Counter] = defaultdict(Counter)
    esperado_por_tipo: dict[str, str] = {}
    for r in resultados:
        por_tipo[r["tipo"]][r["veredito"]] += 1
        esperado_por_tipo[r["tipo"]] = r["rotulo"]

    print(f"=== {nome} ===\n")
    print(f"{'tipo':<20}{'esperado':<12}{'fiel':>6}{'alucinada':>11}{'incerta':>9}")
    for tipo in ORDEM_TIPOS:
        c = por_tipo[tipo]
        print(
            f"{tipo:<20}{esperado_por_tipo[tipo]:<12}"
            f"{c['fiel']:>6}{c['alucinada']:>11}{c['incerta']:>9}"
        )

    fieis = [r for r in resultados if r["rotulo"] == "fiel"]
    alucinadas = [r for r in resultados if r["rotulo"] == "alucinada"]
    fieis_ok = sum(r["veredito"] == "fiel" for r in fieis)
    falsos_alarmes = sum(r["veredito"] == "alucinada" for r in fieis)
    pegas = sum(r["veredito"] == "alucinada" for r in alucinadas)
    passaram = [r for r in alucinadas if r["veredito"] == "fiel"]
    incertas = sum(r["veredito"] == "incerta" for r in resultados)

    print("\nResumo:")
    print(f"  Respostas fiéis reconhecidas como fiéis:   {fieis_ok}/{len(fieis)}")
    print(f"  Falsos alarmes (fiel marcada alucinada):   {falsos_alarmes}")
    print(f"  Alucinações pegas:                         {pegas}/{len(alucinadas)}")
    print(f"  Alucinações que passaram despercebidas:    {len(passaram)}")
    print(f"  Casos incertos (vão para a próxima etapa): {incertas}")

    if passaram:
        print("\nO que passou despercebido:")
        for r in passaram:
            print(f"  [{r['id']}] {r['alteracao']}")


if __name__ == "__main__":
    dataset = carregar_dataset()
    resultados = avaliar(verificar_regras, dataset)
    imprimir_relatorio("Camada 1 (regras)", resultados)