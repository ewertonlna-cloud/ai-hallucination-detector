"""
src/corruptor.py

Gerador de alucinações de propósito. Pega cada resposta correta do gabarito
(data/generated/qa_corretos.json) e produz versões alteradas de forma
controlada. Como é código (e não IA), sabemos EXATAMENTE o que foi mudado em
cada caso, e é isso que permite medir depois se o detector acertou.

Regra do projeto: cada resposta alucinada difere da original por UMA única
alteração. Assim, quando o detector errar, sabemos qual tipo de erro ele não
percebeu.

Tipos gerados por resposta:
  - original           (fiel)      a resposta correta, sem mexer
  - parafrase_correta  (fiel)      troca palavras por sinônimos, mantém os fatos
  - troca_numerica     (alucinada) um número é trocado por outro
  - troca_entidade     (alucinada) um nome/termo é trocado por outro
  - inversao_negacao   (alucinada) o sentido é invertido ("pode" vira "não pode")
  - fabricacao         (alucinada) uma frase inventada é adicionada no final

Nota: as tabelas de trocas abaixo são específicas dos documentos desta base.
Ao adicionar documentos novos, pode ser preciso acrescentar linhas nelas.

Como rodar (na pasta raiz do projeto):
    python3 -m src.corruptor
"""
import json
import random
import re
from collections import Counter
from pathlib import Path

from src.kb_loader import carregar_base

SEMENTE = 42  # semente fixa: rodar de novo gera exatamente o mesmo dataset
ARQUIVO_ENTRADA = "data/generated/qa_corretos.json"
ARQUIVO_SAIDA = "data/generated/dataset_teste.json"

# Número "solto": não faz parte de uma fração (1/3) nem é pedaço de outro número.
PADRAO_NUMERO = re.compile(r"(?<![/\d])\d+(?![/\d])")

# (texto original, texto trocado). Vale a primeira linha que aparecer na resposta.
TROCAS_ENTIDADE = [
    ("conforme a CLT", "conforme o regimento interno"),
    ("sistema interno de RH", "sistema interno de TI"),
    ("gestor direto", "diretor financeiro"),
    ("terço constitucional", "bônus anual"),
    ("dias corridos", "dias úteis"),
    ("solicitação formal", "solicitação verbal"),
]

# (trecho original, trecho com sentido invertido). Vale a primeira linha que aparecer.
INVERSOES_NEGACAO = [
    ("Sim, é possível", "Não, não é possível"),
    ("não pode ter", "pode ter"),
    ("É preciso", "Não é preciso"),
    ("tem direito a", "não tem direito a"),
    ("é feito", "não é feito"),
]

# Frases inventadas: não existem em nenhum documento da base.
DETALHES_FABRICADOS = [
    " Além disso, o funcionário recebe um bônus de 10% sobre o salário no mês das férias.",
    " Funcionários com mais de 5 anos de empresa ganham 5 dias extras de férias.",
    " A empresa também oferece um auxílio-viagem de R$ 1.500 para quem tirar férias em janeiro.",
]

# Sinônimos que NÃO mudam nenhum fato. Todas as linhas que aparecerem são aplicadas.
PARAFRASES = [
    ("Todo funcionário", "Qualquer colaborador"),
    ("conforme a CLT", "de acordo com a CLT"),
    ("podem ser divididas", "podem ser fracionadas"),
    ("Um deles", "Um dos períodos"),
    ("É preciso solicitar", "É necessário solicitar"),
    ("no mínimo", "pelo menos"),
    ("gestor direto", "gestor imediato"),
    ("é feito", "é realizado"),
    ("início do período", "começo do período"),
    ("é possível vender", "pode-se vender"),
    ("o equivalente a", "ou seja,"),
]


def trocar_numero(resposta: str, rng: random.Random) -> tuple[str, str] | None:
    """Troca um número solto por outro valor. Devolve (nova_resposta, descrição)."""
    candidatos = list(PADRAO_NUMERO.finditer(resposta))
    if not candidatos:
        return None
    alvo = rng.choice(candidatos)
    original = int(alvo.group())
    novo = original + rng.choice([2, 5, 10])
    nova = resposta[: alvo.start()] + str(novo) + resposta[alvo.end():]
    return nova, f"número {original} trocado por {novo}"


def trocar_entidade(resposta: str) -> tuple[str, str] | None:
    """Troca um nome/termo do domínio por outro."""
    for original, trocado in TROCAS_ENTIDADE:
        if original in resposta:
            return resposta.replace(original, trocado, 1), f"'{original}' trocado por '{trocado}'"
    return None


def inverter_negacao(resposta: str) -> tuple[str, str] | None:
    """Inverte o sentido de uma afirmação."""
    for original, invertido in INVERSOES_NEGACAO:
        if original in resposta:
            return resposta.replace(original, invertido, 1), f"'{original}' invertido para '{invertido}'"
    return None


def fabricar_detalhe(resposta: str, rng: random.Random) -> tuple[str, str]:
    """Adiciona no final uma frase que não existe na fonte."""
    detalhe = rng.choice(DETALHES_FABRICADOS)
    return resposta + detalhe, f"frase inventada adicionada:{detalhe}"


def parafrasear(resposta: str) -> tuple[str, str] | None:
    """Troca palavras por sinônimos, mantendo todos os fatos."""
    nova = resposta
    for original, sinonimo in PARAFRASES:
        nova = nova.replace(original, sinonimo)
    if nova == resposta:
        return None
    return nova, "sinônimos trocados, fatos mantidos"


def gerar_variantes(par: dict, fonte: str, rng: random.Random) -> list[dict]:
    """Gera todas as versões (fiel e alucinadas) de uma resposta correta."""
    resposta = par["resposta_correta"]
    candidatas = [
        ("original", "fiel", (resposta, "resposta correta, sem alteração")),
        ("parafrase_correta", "fiel", parafrasear(resposta)),
        ("troca_numerica", "alucinada", trocar_numero(resposta, rng)),
        ("troca_entidade", "alucinada", trocar_entidade(resposta)),
        ("inversao_negacao", "alucinada", inverter_negacao(resposta)),
        ("fabricacao", "alucinada", fabricar_detalhe(resposta, rng)),
    ]
    itens = []
    for tipo, rotulo, resultado in candidatas:
        if resultado is None:
            continue  # esse tipo não se aplica a esta resposta
        nova_resposta, alteracao = resultado
        itens.append({
            "id": f"{par['id']}-{tipo}",
            "id_par": par["id"],
            "documento": par["documento"],
            "secao": par["secao"],
            "pergunta": par["pergunta"],
            "fonte": fonte,
            "resposta": nova_resposta,
            "rotulo": rotulo,
            "tipo": tipo,
            "alteracao": alteracao,
        })
    return itens


def gerar_dataset(arquivo_entrada: str = ARQUIVO_ENTRADA, semente: int = SEMENTE) -> list[dict]:
    """Lê o gabarito, gera todas as variantes e devolve o dataset completo."""
    rng = random.Random(semente)
    fontes = {(s.documento, s.titulo): s.texto for s in carregar_base()}
    pares = json.loads(Path(arquivo_entrada).read_text(encoding="utf-8"))

    dataset: list[dict] = []
    for par in pares:
        fonte = fontes[(par["documento"], par["secao"])]
        dataset.extend(gerar_variantes(par, fonte, rng))
    return dataset


if __name__ == "__main__":
    dataset = gerar_dataset()
    Path(ARQUIVO_SAIDA).write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    por_rotulo = Counter(item["rotulo"] for item in dataset)
    por_tipo = Counter(item["tipo"] for item in dataset)
    print(f"{len(dataset)} itens gerados e salvos em {ARQUIVO_SAIDA}")
    print(f"  por rótulo: {dict(por_rotulo)}")
    print(f"  por tipo:   {dict(por_tipo)}\n")

    print("Exemplo, todas as versões da primeira pergunta (q1):")
    for item in dataset:
        if item["id_par"] == "q1":
            print(f"\n[{item['tipo']} | {item['rotulo']}]")
            print(f"  {item['resposta']}")
            print(f"  -> {item['alteracao']}")