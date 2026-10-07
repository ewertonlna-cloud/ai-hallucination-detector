"""
demo_nli.py
Teste isolado do modelo de NLI (Natural Language Inference) que vai virar
a Camada 2 do detector de alucinações.

Objetivo: entender como o modelo classifica pares (fonte, resposta) em
entailment / neutral / contradiction -- ANTES de integrar isso num pipeline.

Nota: trocamos o modelo original (cross-encoder/nli-deberta-v3-small) por um
modelo MULTILÍNGUE, porque o primeiro foi treinado só em inglês (SNLI/MultiNLI)
e não entende português de forma confiável.
"""

import time
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

# Ordem EXATA definida pelo próprio modelo (config id2label) -- não é a mesma
# ordem usada pelos modelos da família cross-encoder/nli-*, então não dá pra
# reaproveitar a lista antiga.
ROTULOS = ["entailment", "neutral", "contradiction"]

# (fonte, resposta_gerada, rótulo_esperado, descrição do caso)
CASOS_DE_TESTE = [
    (
        "Funcionários têm direito a 30 dias de férias remuneradas por ano, "
        "que podem ser divididos em até 3 períodos.",
        "De acordo com a política, os funcionários têm 30 dias de férias remuneradas anuais.",
        "entailment",
        "Resposta fiel e direta",
    ),
    (
        "Funcionários têm direito a 30 dias de férias remuneradas por ano, "
        "que podem ser divididos em até 3 períodos.",
        "Os funcionários têm direito a 45 dias de férias remuneradas por ano.",
        "contradiction",
        "Alucinação óbvia: número trocado",
    ),
    (
        "Funcionários têm direito a 30 dias de férias remuneradas por ano, "
        "que podem ser divididos em até 3 períodos.",
        "A empresa concede um mês de descanso pago anualmente aos colaboradores, "
        "podendo ser fracionado em até três vezes.",
        "entailment",
        "Paráfrase correta (o caso que a Camada 1, baseada em regras, erraria)",
    ),
    (
        "Funcionários têm direito a 30 dias de férias remuneradas por ano, "
        "que podem ser divididos em até 3 períodos.",
        "Além das férias, a empresa oferece reembolso integral de plano de saúde "
        "para toda a família do funcionário.",
        "neutral",
        "Fabricação: informação não presente na fonte",
    ),(
        "Funcionários têm direito a 30 dias de férias remuneradas por ano, "
        "que podem ser divididos em até 3 períodos.",
        "A política da empresa garante aos colaboradores 30 dias de descanso "
        "remunerado a cada ano, podendo ser fracionados em até três vezes.",
        "entailment",
        "Paráfrase mantendo a quantidade exata (isola se o erro do caso 3 foi "
        "a troca '30 dias' -> 'um mês')",
    ),
]


def main():
    print(f"Carregando modelo '{MODEL_NAME}'... (1a vez baixa ~1GB, pode demorar mais que antes)")
    inicio_carga = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    print(f"Modelo carregado em {time.time() - inicio_carga:.1f}s\n")

    for fonte, resposta, esperado, descricao in CASOS_DE_TESTE:
        inicio = time.time()
        entrada = tokenizer(fonte, resposta, truncation=True, return_tensors="pt")
        with torch.no_grad():
            saida = model(**entrada)
        probabilidades = torch.softmax(saida.logits[0], dim=-1).tolist()
        duracao = time.time() - inicio

        indice_previsto = probabilidades.index(max(probabilidades))
        previsto = ROTULOS[indice_previsto]
        confianca = probabilidades[indice_previsto]

        acertou = "OK" if previsto == esperado else "ERRO"

        print(f"--- {descricao} ---")
        print(f"Fonte:    {fonte}")
        print(f"Resposta: {resposta}")
        print(
            f"Esperado: {esperado} | Previsto: {previsto} ({confianca:.1%}) "
            f"[{duracao*1000:.0f}ms] -> {acertou}"
        )
        print()


if __name__ == "__main__":
    main()