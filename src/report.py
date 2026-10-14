"""
src/report.py

Gera o relatório em HTML do pipeline: um arquivo único, sem dependências
externas, que pode ser aberto direto no navegador.

Todo texto que vem do dataset passa por escape() antes de entrar no HTML, para
que uma resposta com "<" ou ">" nunca quebre (ou injete código em) a página.
"""
from datetime import datetime
from html import escape
from pathlib import Path

LIMITACOES = [
    "Dataset pequeno (30 itens) criado pelo próprio projeto: os números ilustram "
    "o comportamento do detector, mas não provam desempenho com respostas reais de IA.",
    "O NLI pode errar em paráfrases muito reescritas em português e em pequenas trocas "
    "de termo dentro de frases longas (exemplo: \"CLT\" trocada por \"regimento interno\").",
    "Informação inventada sem número, sigla ou negação costuma ficar como \"incerta\": "
    "o NLI só diz que a fonte não menciona o trecho, e isso mistura invenção, conversa "
    "social e fato verdadeiro fora da base.",
    "As regras da Camada 1 são heurísticas simples (números, siglas e negações) e "
    "não entendem o sentido da frase.",
]

CSS = """
body { font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #1c1e21; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { margin: 0 0 4px; font-size: 1.6rem; }
h2 { margin: 32px 0 12px; font-size: 1.15rem; }
.sub { color: #5b6068; margin: 0 0 24px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.card { background: #fff; border: 1px solid #dde0e5; border-radius: 10px; padding: 14px 16px; }
.card .n { font-size: 1.8rem; font-weight: 700; }
.card .t { color: #5b6068; font-size: 0.85rem; }
.tabela { overflow-x: auto; background: #fff; border: 1px solid #dde0e5; border-radius: 10px; }
table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eceef1; vertical-align: top; }
th { background: #eef0f3; position: sticky; top: 0; }
tr.liberada td:first-child { border-left: 4px solid #2e9e57; }
tr.alta td:first-child { border-left: 4px solid #d6403a; }
tr.media td:first-child { border-left: 4px solid #e0a020; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 0.75rem; background: #eef0f3; }
.tag.ruim { background: #fde4e2; color: #9c2620; }
.tag.bom { background: #e0f4e8; color: #1d6b3b; }
.tag.aviso { background: #fff1d6; color: #8a5a00; }
ul.lim li { margin-bottom: 6px; }
"""


def situacao(item: dict) -> tuple[str, str]:
    """Compara o veredito do detector com o gabarito. Devolve (texto, classe CSS)."""
    rotulo, veredito = item["rotulo"], item["veredito"]
    if rotulo == "fiel":
        if veredito == "fiel":
            return "acerto", "bom"
        return "falso alarme", "ruim"
    if veredito == "alucinada":
        return "acerto", "bom"
    if veredito == "incerta":
        return "escalada para revisão", "aviso"
    return "passou despercebida", "ruim"


def calcular_resumo(resultados: list[dict]) -> dict:
    fieis = [r for r in resultados if r["rotulo"] == "fiel"]
    alucinadas = [r for r in resultados if r["rotulo"] == "alucinada"]
    return {
        "total": len(resultados),
        "liberadas": sum(r["acao"] == "liberada" for r in resultados),
        "bloqueadas_alta": sum(r["prioridade_revisao"] == "alta" for r in resultados),
        "bloqueadas_media": sum(r["prioridade_revisao"] == "media" for r in resultados),
        "fieis_ok": sum(r["veredito"] == "fiel" for r in fieis),
        "total_fieis": len(fieis),
        "falsos_alarmes": sum(r["veredito"] != "fiel" for r in fieis),
        "alucinacoes_pegas": sum(r["veredito"] == "alucinada" for r in alucinadas),
        "alucinacoes_escaladas": sum(r["veredito"] == "incerta" for r in alucinadas),
        "alucinacoes_perdidas": sum(r["veredito"] == "fiel" for r in alucinadas),
        "total_alucinadas": len(alucinadas),
    }


def _card(numero: str, titulo: str) -> str:
    return f'<div class="card"><div class="n">{escape(numero)}</div><div class="t">{escape(titulo)}</div></div>'


def _linha(item: dict) -> str:
    texto_situacao, classe_situacao = situacao(item)
    classe_linha = item["prioridade_revisao"] or "liberada"
    motivos = "<br>".join(escape(m) for m in item["motivos"]) or "&mdash;"
    return (
        f'<tr class="{escape(classe_linha)}">'
        f'<td>{escape(item["id"])}</td>'
        f'<td>{escape(item["tipo"])}</td>'
        f'<td>{escape(item["rotulo"])}</td>'
        f'<td>{escape(item["veredito"])}</td>'
        f'<td><span class="tag {classe_situacao}">{escape(texto_situacao)}</span></td>'
        f'<td>{escape(item["resposta"])}</td>'
        f'<td>{escape(item["texto_final"])}</td>'
        f'<td>{motivos}</td>'
        "</tr>"
    )


def gerar_relatorio_html(resultados: list[dict], caminho_saida: str) -> str:
    """Monta o HTML, salva em caminho_saida e devolve o caminho."""
    r = calcular_resumo(resultados)
    cartoes = "".join([
        _card(str(r["total"]), "respostas analisadas"),
        _card(str(r["liberadas"]), "liberadas ao usuário"),
        _card(str(r["bloqueadas_alta"]), "bloqueadas, revisão alta"),
        _card(str(r["bloqueadas_media"]), "bloqueadas, revisão média"),
        _card(f'{r["fieis_ok"]}/{r["total_fieis"]}', "fiéis reconhecidas como fiéis"),
        _card(str(r["falsos_alarmes"]), "falsos alarmes"),
        _card(f'{r["alucinacoes_pegas"]}/{r["total_alucinadas"]}', "alucinações pegas"),
        _card(str(r["alucinacoes_escaladas"]), "alucinações escaladas p/ revisão"),
        _card(str(r["alucinacoes_perdidas"]), "alucinações que passaram"),
    ])
    linhas = "".join(_linha(item) for item in resultados)
    limitacoes = "".join(f"<li>{escape(texto)}</li>" for texto in LIMITACOES)
    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")

    html = (
        '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Relatório do detector de alucinações</title>"
        f"<style>{CSS}</style></head><body><main>"
        "<h1>Relatório do detector de alucinações</h1>"
        f'<p class="sub">Gerado em {escape(gerado_em)}. Camada 1 (regras) + Camada 2 (NLI) + mitigação.</p>'
        f'<div class="cards">{cartoes}</div>'
        "<h2>Resposta por resposta</h2>"
        '<div class="tabela"><table><thead><tr>'
        "<th>id</th><th>tipo</th><th>gabarito</th><th>veredito</th><th>resultado</th>"
        "<th>resposta da IA</th><th>o que o usuário vê</th><th>motivos</th>"
        f"</tr></thead><tbody>{linhas}</tbody></table></div>"
        "<h2>Limitações conhecidas</h2>"
        f'<ul class="lim">{limitacoes}</ul>'
        "</main></body></html>"
    )
    destino = Path(caminho_saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return str(destino)