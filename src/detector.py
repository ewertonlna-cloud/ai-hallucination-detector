"""
src/detector.py

Motor de detecção de alucinações. Recebe a FONTE (o trecho do documento) e uma
RESPOSTA, e devolve um veredito:
  - "fiel"       a resposta parece sustentada pela fonte
  - "alucinada"  a resposta parece conter algo que a fonte não sustenta
  - "incerta"    o detector não consegue decidir (vai para a próxima camada
                 ou para uma pessoa revisar)

Camada 1 (regras determinísticas): não usa IA, roda na hora e é 100%
explicável: todo alerta vem com o motivo escrito, o que permite auditoria.
Ela pega números, siglas e negações que aparecem do nada, mas não entende o
SENTIDO da frase.

Camada 2 (NLI, Natural Language Inference): um modelo de linguagem já treinado
julga, frase por frase da resposta, se a fonte sustenta (entailment), contradiz
(contradiction) ou não permite concluir nada (neutral). É a mesma ideia da
métrica "faithfulness" de frameworks como o RAGAS: decompor a resposta em
afirmações e checar cada uma contra a fonte.

Limitação conhecida (documentar no README): o modelo NLI tem dificuldade com
paráfrases muito reescritas em português, e pode tratar aproximações como
"30 dias" e "um mês" como contradição.
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache

PADRAO_NUMERO = re.compile(r"\d+")
PADRAO_SIGLA = re.compile(r"\b[A-ZÀ-Ú]{2,}\b")
PADRAO_NEGACAO = re.compile(r"\bnão\b")
PADRAO_FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+")

MODELO_NLI = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
# Ordem EXATA definida pelo próprio modelo (config id2label).
ROTULOS_NLI = ["entailment", "neutral", "contradiction"]


@dataclass
class Resultado:
    veredito: str  # "fiel", "alucinada" ou "incerta"
    motivos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Camada 1: regras determinísticas
# ---------------------------------------------------------------------------

def _numeros(texto: str) -> set[str]:
    return set(PADRAO_NUMERO.findall(texto))


def _siglas(texto: str) -> set[str]:
    return set(PADRAO_SIGLA.findall(texto))


def _contar_negacoes(texto: str) -> int:
    return len(PADRAO_NEGACAO.findall(texto.lower()))


def verificar_numeros(fonte: str, resposta: str) -> list[str]:
    """Alerta se a resposta traz um número que não existe na fonte."""
    novos = sorted(_numeros(resposta) - _numeros(fonte), key=int)
    if novos:
        return [f"número(s) {', '.join(novos)} não aparece(m) na fonte"]
    return []


def verificar_siglas(fonte: str, resposta: str) -> list[str]:
    """Alerta se a resposta traz uma sigla (CLT, RH...) que não existe na fonte."""
    novas = sorted(_siglas(resposta) - _siglas(fonte))
    if novas:
        return [f"sigla(s) {', '.join(novas)} não aparece(m) na fonte"]
    return []


def verificar_negacoes(fonte: str, resposta: str) -> list[str]:
    """Alerta se a quantidade de 'não' na resposta difere da fonte (heurística grosseira)."""
    na_fonte = _contar_negacoes(fonte)
    na_resposta = _contar_negacoes(resposta)
    if na_fonte != na_resposta:
        return [f"quantidade de 'não' diferente (fonte: {na_fonte}, resposta: {na_resposta})"]
    return []


def verificar_regras(fonte: str, resposta: str) -> Resultado:
    """Camada 1: roda todas as regras e junta os motivos."""
    motivos = (
        verificar_numeros(fonte, resposta)
        + verificar_siglas(fonte, resposta)
        + verificar_negacoes(fonte, resposta)
    )
    if motivos:
        return Resultado("alucinada", motivos)
    return Resultado("fiel")


# ---------------------------------------------------------------------------
# Camada 2: NLI (modelo de linguagem julga frase por frase)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _carregar_modelo():
    """Carrega o modelo uma única vez. Os imports pesados ficam aqui dentro de
    propósito: quem só usa a Camada 1 não precisa esperar o torch carregar."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODELO_NLI)
    modelo = AutoModelForSequenceClassification.from_pretrained(MODELO_NLI)
    return tokenizer, modelo


@lru_cache(maxsize=None)
def julgar_frase(fonte: str, frase: str) -> tuple[str, float]:
    """Pergunta ao modelo: a fonte sustenta esta frase? Devolve (rótulo, confiança).
    O cache evita rodar o modelo duas vezes para o mesmo par fonte+frase."""
    import torch

    tokenizer, modelo = _carregar_modelo()
    entrada = tokenizer(fonte, frase, truncation=True, return_tensors="pt")
    with torch.no_grad():
        logits = modelo(**entrada).logits[0]
    probabilidades = torch.softmax(logits, dim=-1).tolist()
    indice = probabilidades.index(max(probabilidades))
    return ROTULOS_NLI[indice], probabilidades[indice]


def dividir_frases(resposta: str) -> list[str]:
    """Separa a resposta em frases (cada frase vira uma afirmação a verificar)."""
    return [f.strip() for f in PADRAO_FIM_DE_FRASE.split(resposta) if f.strip()]


def verificar_nli(fonte: str, resposta: str) -> Resultado:
    """Camada 2: julga cada frase da resposta contra a fonte.
    Qualquer contradição => alucinada. Sem contradição, mas com frase que a
    fonte não confirma (neutral) => incerta. Tudo confirmado => fiel."""
    contradicoes: list[str] = []
    duvidas: list[str] = []
    for frase in dividir_frases(resposta):
        rotulo, confianca = julgar_frase(fonte, frase)
        if rotulo == "contradiction":
            contradicoes.append(f"contradiz a fonte ({confianca:.0%}): '{frase}'")
        elif rotulo == "neutral":
            duvidas.append(f"não confirmada pela fonte ({confianca:.0%}): '{frase}'")

    if contradicoes:
        return Resultado("alucinada", contradicoes + duvidas)
    if duvidas:
        return Resultado("incerta", duvidas)
    return Resultado("fiel")


# ---------------------------------------------------------------------------
# Pipeline: camadas em sequência
# ---------------------------------------------------------------------------

def detectar(fonte: str, resposta: str) -> Resultado:
    """Regras primeiro (rápidas e baratas). O NLI só roda se as regras não
    acharem problema."""
    resultado_regras = verificar_regras(fonte, resposta)
    if resultado_regras.veredito == "alucinada":
        return resultado_regras
    return verificar_nli(fonte, resposta)