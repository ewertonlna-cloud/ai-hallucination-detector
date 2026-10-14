"""
run_pipeline.py

Roda o pipeline completo com um comando só:
  1. lê o dataset de teste
  2. julga cada resposta com o detector (regras + NLI)
  3. aplica a mitigação (libera a resposta ou troca por um aviso)
  4. salva uma tabela (CSV) e um relatório (HTML) na pasta outputs/

Uso (na pasta raiz do projeto):
    python3 run_pipeline.py
"""
import csv
import json
import time
from pathlib import Path
from typing import Callable

from src.detector import Resultado, detectar
from src.mitigacao import decidir
from src.report import gerar_relatorio_html

ARQUIVO_DATASET = "data/generated/dataset_teste.json"
PASTA_SAIDA = "outputs"


def processar(
    dataset: list[dict],
    detector: Callable[[str, str], Resultado] = detectar,
) -> list[dict]:
    """Passa cada resposta pelo detector e pela mitigação."""
    resultados = []
    for item in dataset:
        resultado = detector(item["fonte"], item["resposta"])
        decisao = decidir(item["resposta"], resultado)
        resultados.append({
            **item,
            "veredito": resultado.veredito,
            "motivos": resultado.motivos,
            "acao": decisao.acao,
            "texto_final": decisao.texto_final,
            "prioridade_revisao": decisao.prioridade_revisao,
        })
    return resultados


def salvar_csv(resultados: list[dict], caminho: str) -> None:
    """Salva a tabela de resultados. O utf-8-sig faz o Excel abrir os acentos certos."""
    campos = ["id", "tipo", "rotulo", "veredito", "acao", "prioridade_revisao", "motivos"]
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        for r in resultados:
            linha = {campo: r.get(campo) for campo in campos}
            linha["motivos"] = " | ".join(r["motivos"])
            escritor.writerow(linha)


def main() -> None:
    print(f"1/4 - Lendo o dataset: {ARQUIVO_DATASET}")
    dataset = json.loads(Path(ARQUIVO_DATASET).read_text(encoding="utf-8"))
    print(f"      {len(dataset)} respostas carregadas.")

    print("2/4 - Julgando cada resposta (regras + NLI)...")
    print("      A primeira vez carrega o modelo e leva alguns minutos.")
    inicio = time.time()
    resultados = processar(dataset)
    print(f"      Pronto em {time.time() - inicio:.0f}s.")

    print("3/4 - Mitigação aplicada.")
    liberadas = sum(r["acao"] == "liberada" for r in resultados)
    print(f"      {liberadas} liberadas, {len(resultados) - liberadas} bloqueadas.")

    print("4/4 - Salvando os resultados...")
    caminho_csv = f"{PASTA_SAIDA}/resultados.csv"
    salvar_csv(resultados, caminho_csv)
    caminho_html = gerar_relatorio_html(resultados, f"{PASTA_SAIDA}/relatorio.html")
    print(f"      Tabela:    {caminho_csv}")
    print(f"      Relatório: {caminho_html}")
    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()