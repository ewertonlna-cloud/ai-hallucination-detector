"""
tests/test_detector.py

Testes automáticos do detector. Nenhum deles baixa ou roda o modelo de IA:
as regras da Camada 1 são testadas direto, e a lógica de decisão da Camada 2
é testada trocando o modelo por uma versão falsa (monkeypatch).

Como rodar (na pasta raiz do projeto):
    python3 -m pytest
"""
from src import detector
from src.detector import dividir_frases, verificar_nli, verificar_regras

FONTE = "O funcionário tem direito a 30 dias de férias, conforme a CLT. O RH aprova o pedido."


# ---------------------------------------------------------------------------
# Camada 1: regras
# ---------------------------------------------------------------------------

def test_resposta_igual_a_fonte_e_fiel():
    resultado = verificar_regras(FONTE, "O funcionário tem direito a 30 dias de férias, conforme a CLT.")
    assert resultado.veredito == "fiel"
    assert resultado.motivos == []


def test_numero_novo_vira_alucinada():
    resultado = verificar_regras(FONTE, "O funcionário tem direito a 45 dias de férias, conforme a CLT.")
    assert resultado.veredito == "alucinada"
    assert "45" in resultado.motivos[0]


def test_sigla_nova_vira_alucinada():
    resultado = verificar_regras(FONTE, "O TI aprova o pedido de 30 dias.")
    assert resultado.veredito == "alucinada"
    assert "TI" in resultado.motivos[0]


def test_negacao_a_mais_vira_alucinada():
    resultado = verificar_regras(FONTE, "O funcionário não tem direito a 30 dias de férias, conforme a CLT.")
    assert resultado.veredito == "alucinada"
    assert "não" in resultado.motivos[0]


def test_numero_da_fonte_com_zero_nao_e_ignorado():
    # Proteção contra um erro clássico: tratar o número 0 como se fosse "vazio".
    # (Esse bug já aconteceu no projeto 1.) Um 0 que NÃO existe na fonte precisa
    # ser detectado como número novo.
    resultado = verificar_regras("O prazo é de 5 dias.", "O prazo é de 0 dias.")
    assert resultado.veredito == "alucinada"


# ---------------------------------------------------------------------------
# Divisão em frases
# ---------------------------------------------------------------------------

def test_divide_resposta_em_duas_frases():
    frases = dividir_frases("Primeira frase. Segunda frase.")
    assert frases == ["Primeira frase.", "Segunda frase."]


def test_nao_quebra_valor_com_ponto_no_meio():
    # "R$ 1.500" tem um ponto, mas não é fim de frase.
    frases = dividir_frases("A empresa paga R$ 1.500 de auxílio. Outra frase.")
    assert len(frases) == 2
    assert "1.500" in frases[0]


# ---------------------------------------------------------------------------
# Camada 2: lógica de decisão (com o modelo trocado por uma versão falsa)
# ---------------------------------------------------------------------------

def _modelo_falso(respostas_por_frase):
    """Cria um 'julgar_frase' falso que devolve o rótulo combinado para cada frase."""
    def falso(fonte, frase):
        return respostas_por_frase[frase], 0.95
    return falso


def test_nli_todas_confirmadas_e_fiel(monkeypatch):
    monkeypatch.setattr(detector, "julgar_frase", _modelo_falso({"A.": "entailment", "B.": "entailment"}))
    assert verificar_nli(FONTE, "A. B.").veredito == "fiel"


def test_nli_frase_neutral_vira_incerta(monkeypatch):
    monkeypatch.setattr(detector, "julgar_frase", _modelo_falso({"A.": "entailment", "B.": "neutral"}))
    resultado = verificar_nli(FONTE, "A. B.")
    assert resultado.veredito == "incerta"
    assert "B." in resultado.motivos[0]


def test_nli_contradicao_vence_neutral(monkeypatch):
    monkeypatch.setattr(detector, "julgar_frase", _modelo_falso({"A.": "contradiction", "B.": "neutral"}))
    assert verificar_nli(FONTE, "A. B.").veredito == "alucinada"


# ---------------------------------------------------------------------------
# Pipeline: regras primeiro, NLI depois
# ---------------------------------------------------------------------------

def test_pipeline_nao_chama_o_nli_quando_as_regras_ja_acharam_problema(monkeypatch):
    def nao_deveria_ser_chamado(fonte, frase):
        raise AssertionError("o NLI não deveria rodar quando as regras já sinalizaram")

    monkeypatch.setattr(detector, "julgar_frase", nao_deveria_ser_chamado)
    resultado = detector.detectar(FONTE, "O funcionário tem direito a 45 dias de férias.")
    assert resultado.veredito == "alucinada"