"""
src/mitigacao.py

Mitigação simples. O projeto NÃO tenta corrigir a resposta errada (corrigir
texto automaticamente é arriscado e complexo). A regra é outra: se o detector
não consegue confirmar a resposta, ela não chega ao usuário. No lugar dela vai
um aviso honesto, e o caso fica na fila para uma pessoa revisar.

  fiel       -> liberada  (o usuário vê a resposta normal)
  alucinada  -> bloqueada (o usuário vê o aviso; revisão de prioridade ALTA)
  incerta    -> bloqueada (o usuário vê o aviso; revisão de prioridade MÉDIA)
"""
from dataclasses import dataclass

from src.detector import Resultado

AVISO = (
    "Não consegui confirmar essa informação na base de conhecimento. "
    "Vou encaminhar a sua dúvida para um atendente."
)


@dataclass
class Decisao:
    acao: str                       # "liberada" ou "bloqueada"
    texto_final: str                # o que o usuário realmente vê
    prioridade_revisao: str | None  # None, "media" ou "alta"


def decidir(resposta: str, resultado: Resultado) -> Decisao:
    """Transforma o veredito do detector em uma ação concreta."""
    if resultado.veredito == "fiel":
        return Decisao("liberada", resposta, None)
    if resultado.veredito == "alucinada":
        return Decisao("bloqueada", AVISO, "alta")
    return Decisao("bloqueada", AVISO, "media")