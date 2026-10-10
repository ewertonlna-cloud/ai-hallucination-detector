"""
src/kb_loader.py

Lê os documentos da base de conhecimento (arquivos .md) e divide cada um em
seções. Cada seção é um "trecho-fonte": é contra ele que o detector vai
verificar se uma resposta de IA está sustentada ou não.
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Secao:
    documento: str  # nome do arquivo, ex: "politica_ferias.md"
    titulo: str     # título da seção, ex: "Fracionamento"
    texto: str      # conteúdo da seção, em uma linha só, sem o título


def _juntar_linhas(linhas: list[str]) -> str:
    """Junta as linhas de uma seção em um único texto corrido."""
    return " ".join(linha.strip() for linha in linhas if linha.strip())


def carregar_secoes(caminho_arquivo: str) -> list[Secao]:
    """Lê um arquivo .md e devolve uma lista de seções (uma por '## título')."""
    arquivo = Path(caminho_arquivo)
    secoes: list[Secao] = []
    titulo_atual = None
    linhas_atuais: list[str] = []

    def fechar_secao_atual():
        if titulo_atual is None:
            return
        texto = _juntar_linhas(linhas_atuais)
        if texto:
            secoes.append(Secao(arquivo.name, titulo_atual, texto))

    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        if linha.startswith("## "):
            fechar_secao_atual()
            titulo_atual = linha[3:].strip()
            linhas_atuais = []
        elif linha.startswith("# "):
            continue  # título do documento, não é uma seção
        else:
            linhas_atuais.append(linha)

    fechar_secao_atual()
    return secoes


def carregar_base(pasta: str = "data/knowledge_base") -> list[Secao]:
    """Lê todos os arquivos .md de uma pasta e junta todas as seções."""
    todas: list[Secao] = []
    for arquivo in sorted(Path(pasta).glob("*.md")):
        todas.extend(carregar_secoes(str(arquivo)))
    return todas


if __name__ == "__main__":
    secoes = carregar_base()
    print(f"{len(secoes)} seções carregadas.\n")
    for i, s in enumerate(secoes, start=1):
        print(f"[{i}] {s.documento} > {s.titulo}")
        print(f"    {s.texto}\n")