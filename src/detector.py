"""
src/detector.py

Motor de detecção de alucinações. Recebe a FONTE (o trecho do documento) e uma
RESPOSTA, e devolve um veredito:
  - "fiel"       a resposta parece sustentada pela fonte
  - "alucinada"  a resposta parece conter algo que a fonte não sustenta
  - "incerta"    o detector não consegue decidir (usado nas camadas seguintes)

Camada 1 (esta versão): regras determinísticas. Não usa IA, roda na hora e é
100% explicável: todo alerta vem com o motivo escrito, o que permite auditoria.

Limitação conhecida (documentar no README): são regras simples. Elas pegam
números, siglas e negações que aparecem do nada, mas não entendem o SENTIDO
da frase. Trocar "gestor direto" por "diretor financeiro", por exemplo, passa
batido. É para casos assim que existem as camadas seguintes.
"""
import re
from dataclasses import dataclass, field

PADRAO_NUMERO = re.compile(r"\d+")
PADRAO_SIGLA = re.compile(r"\b[A-ZÀ-Ú]{2,}\b")
PADRAO_NEGACAO = re.compile(r"\bnão\b")


@dataclass
class Resultado:
    veredito: str  # "fiel", "alucinada" ou "incerta"
    motivos: list[str] = field(default_factory=list)


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