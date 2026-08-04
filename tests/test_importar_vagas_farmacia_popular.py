import importlib.util
import gzip
import json
import sys
from pathlib import Path

import openpyxl
import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "importar-vagas-farmacia-popular.py"
SPEC = importlib.util.spec_from_file_location("importador_vagas", SCRIPT)
IMPORTADOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["importador_vagas"] = IMPORTADOR
SPEC.loader.exec_module(IMPORTADOR)


CASOS_NOMINAIS = [
    ("MG", 314780, "PASSA VINTE", "Passa Vinte", 1),
    ("MT", 510700, "POXOREO", "Poxoréu", 2),
    ("PA", 150295, "ELDORADO DOS CARAJAS", "Eldorado do Carajás", 2),
    ("RR", 140060, "SAO LUIZ DO ANAUA", "São Luiz do Anauá", 2),
    ("SP", 355000, "SAO LUIS DO PARAITINGA", "São Luiz do Paraitinga", 1),
    ("TO", 170825, "TABOCAO", "Tabocão", 1),
]


def referencia_nominal():
    return [
        {"id": 3147808, "nome": "Passa Vinte", "uf": {"sigla": "MG"}},
        {"id": 5107008, "nome": "Poxoréu", "uf": {"sigla": "MT"}},
        {"id": 1502954, "nome": "Eldorado do Carajás", "uf": {"sigla": "PA"}},
        {"id": 1400605, "nome": "São Luiz do Anauá", "uf": {"sigla": "RR"}},
        {"id": 3550001, "nome": "São Luiz do Paraitinga", "uf": {"sigla": "SP"}},
        {"id": 1708254, "nome": "Tabocão", "uf": {"sigla": "TO"}},
    ]


def criar_xlsx(caminho, rows, headers=None, sheet="Planilha2"):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = sheet
    worksheet.append(["Anexo de teste"])
    worksheet.append(headers or IMPORTADOR.COLUNAS_OBRIGATORIAS)
    for row in rows:
        worksheet.append(row)
    workbook.save(caminho)


def linha(codigo=314780, uf="MG", nome="PASSA VINTE", total=1, preenchidas=0, disponiveis=1):
    return ["SUDESTE", uf, codigo, nome, total, preenchidas, disponiveis]


def esperados(registros=1, ufs=1, totais=1, preenchidas=0, disponiveis=1):
    return IMPORTADOR.TotaisEsperados(registros, ufs, totais, preenchidas, disponiveis)


def importar(tmp_path, rows, referencia=None, esperado=None, headers=None, sheet="Planilha2"):
    xlsx = tmp_path / "entrada.xlsx"
    criar_xlsx(xlsx, rows, headers=headers, sheet=sheet)
    return IMPORTADOR.importar_registros(
        xlsx,
        IMPORTADOR._carregar_referencia(referencia or referencia_nominal()),
        esperado or esperados(),
    )


def test_leitura_valida_e_nomes_ibge(tmp_path):
    registros, divergentes = importar(tmp_path, [linha()])

    assert registros == [
        {
            "codigo_ibge": "3147808",
            "regiao": "Sudeste",
            "uf": "MG",
            "municipio_fonte_ms": "PASSA VINTE",
            "municipio_exibicao": "Passa Vinte",
            "vagas_totais": 1,
            "vagas_preenchidas": 0,
            "vagas_disponiveis": 1,
        }
    ]
    assert divergentes == {
        "quantidade_nomes_com_diferenca_literal": 1,
        "quantidade_nomes_equivalentes_apos_normalizacao": 1,
        "quantidade_divergencias_nominais_relevantes": 0,
        "divergencias_nominais_relevantes": [],
    }


def test_referencia_ibge_aceita_uf_em_regiao_intermediaria():
    referencia = IMPORTADOR._carregar_referencia(
        [{
            "id": 5101837,
            "nome": "Boa Esperança do Norte",
            "microrregiao": None,
            "regiao-imediata": {
                "regiao-intermediaria": {"UF": {"sigla": "MT"}}
            },
        }]
    )

    assert referencia["5101837"] == {
        "nome": "Boa Esperança do Norte",
        "uf": "MT",
    }


def test_consulta_ibge_descomprime_resposta_gzip(monkeypatch):
    class Resposta:
        headers = {"Content-Encoding": "gzip"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return gzip.compress(json.dumps(referencia_nominal()).encode("utf-8"))

    monkeypatch.setattr(IMPORTADOR, "urlopen", lambda *_args, **_kwargs: Resposta())

    referencia = IMPORTADOR.consultar_referencia_ibge("https://example.test/ibge")

    assert referencia["5107008"]["nome"] == "Poxoréu"


def test_seis_casos_nominais_sao_resolvidos_por_codigo(tmp_path):
    rows = [linha(codigo, uf, nome, total, 0, total) for uf, codigo, nome, _, total in CASOS_NOMINAIS]
    rows[0][4] = 1
    referencia = referencia_nominal()
    registros, divergentes = importar(
        tmp_path,
        rows,
        referencia=referencia,
        esperado=esperados(registros=6, ufs=6, totais=9, disponiveis=9),
    )

    por_codigo = {registro["codigo_ibge"]: registro for registro in registros}
    assert {registro["municipio_exibicao"] for registro in registros} == {
        caso[3] for caso in CASOS_NOMINAIS
    }
    codigos_ibge = {
        314780: "3147808",
        510700: "5107008",
        150295: "1502954",
        140060: "1400605",
        355000: "3550001",
        170825: "1708254",
    }
    for _, codigo, nome_fonte, nome_exibicao, _ in CASOS_NOMINAIS:
        registro = por_codigo[codigos_ibge[codigo]]
        assert registro["municipio_fonte_ms"] == nome_fonte
        assert registro["municipio_exibicao"] == nome_exibicao
    assert divergentes["quantidade_nomes_com_diferenca_literal"] == 6
    assert divergentes["quantidade_nomes_equivalentes_apos_normalizacao"] == 3
    assert divergentes["quantidade_divergencias_nominais_relevantes"] == 3
    assert {item["codigo_ibge"] for item in divergentes["divergencias_nominais_relevantes"]} == {
        "5107008", "1502954", "3550001"
    }


@pytest.mark.parametrize(
    ("nome_ms", "nome_ibge", "equivalentes"),
    [
        ("PASSA VINTE", "Passa Vinte", True),
        ("POXOREO", "Poxor" + chr(0x00E9) + "u", False),
        ("ELDORADO DOS CARAJAS", "Eldorado do Caraj" + chr(0x00E1) + "s", False),
        ("SAO LUIZ DO ANAUA", "S" + chr(0x00E3) + "o Luiz do Anau" + chr(0x00E1), True),
        ("SAO LUIS DO PARAITINGA", "S" + chr(0x00E3) + "o Luiz do Paraitinga", False),
        ("TABOCAO", "Taboc" + chr(0x00E3) + "o", True),
        ("MUNICIPIO", "municipio", True),
        ("Sao Tome", "S" + chr(0x00E3) + "o Tom" + chr(0x00E9), True),
        ("Santa-Cruz", "Santa Cruz", True),
        ("D" + chr(0x2019) + "ALVARES", "D'Alvares", True),
        ("Sao Pedro", "Sao Paulo", False),
    ],
)
def test_comparacao_nominal_normaliza_apenas_equivalencias(nome_ms, nome_ibge, equivalentes):
    assert IMPORTADOR.comparar_nomes_municipio(nome_ms, nome_ibge) is equivalentes


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([linha(314780, "MG", "PASSA VINTE"), linha(314780, "MG", "PASSA VINTE")], "duplicado"),
        ([linha(999999, "MG", "DESCONHECIDO")], "nao encontrado"),
        ([linha(314780, "SP")], "UF incompatível"),
        ([linha(total=-1, disponiveis=-1)], "negativo"),
        ([linha(total=1, disponiveis=1.5)], "nao inteiro"),
        ([linha(total=2, disponiveis=0)], "inconsistente"),
        ([linha(nome="")], "incompleto"),
    ],
)
def test_validacoes_interrompem_importacao(tmp_path, rows, message):
    with pytest.raises(IMPORTADOR.ImportacaoError, match=message):
        importar(tmp_path, rows)


def test_codigo_de_seis_digitos_ambiguo_interrompe_importacao(tmp_path):
    referencia = referencia_nominal() + [
        {"id": 3147809, "nome": "Outro Municipio", "uf": {"sigla": "MG"}},
    ]

    with pytest.raises(IMPORTADOR.ImportacaoError, match="nao encontrado ou ambiguo"):
        importar(tmp_path, [linha()], referencia=referencia)


def test_colunas_ausentes(tmp_path):
    headers = list(IMPORTADOR.COLUNAS_OBRIGATORIAS)
    headers[-1] = "Disponibilidade"
    with pytest.raises(IMPORTADOR.ImportacaoError, match="ausentes ou renomeadas"):
        importar(tmp_path, [linha()], headers=headers)


def test_aba_esperada_ausente(tmp_path):
    with pytest.raises(IMPORTADOR.ImportacaoError, match="aba esperada ausente"):
        importar(tmp_path, [linha()], sheet="OutraAba")


def test_quantidade_inesperada(tmp_path):
    with pytest.raises(IMPORTADOR.ImportacaoError, match="registros inesperado"):
        importar(tmp_path, [linha()], esperado=esperados(registros=2, totais=2, disponiveis=2))


def test_saida_deterministica(tmp_path):
    rows = [linha(), linha(510700, "MT", "POXOREO", 2, 0, 2)]
    referencia = IMPORTADOR._carregar_referencia(referencia_nominal())
    xlsx = tmp_path / "entrada.xlsx"
    criar_xlsx(xlsx, rows)
    registros, comparacao = IMPORTADOR.importar_registros(
        xlsx, referencia, esperados(registros=2, ufs=2, totais=3, disponiveis=3)
    )
    referencia_json = tmp_path / "referencia.json"
    referencia_json.write_text(json.dumps(referencia_nominal()), encoding="utf-8")
    primeiro = tmp_path / "a.json"
    segundo = tmp_path / "b.json"
    primeiro_metadados = tmp_path / "a-metadados.json"
    segundo_metadados = tmp_path / "b-metadados.json"
    metadados = IMPORTADOR.criar_metadados(
        xlsx,
        referencia_json,
        registros,
        comparacao,
        "2026-08-04",
        "referencia de teste",
        "2026-08-04",
    )
    IMPORTADOR.escrever_json(primeiro, registros)
    IMPORTADOR.escrever_json(segundo, registros)
    IMPORTADOR.escrever_json(primeiro_metadados, metadados)
    IMPORTADOR.escrever_json(segundo_metadados, metadados)
    assert primeiro.read_bytes() == segundo.read_bytes()
    assert primeiro_metadados.read_bytes() == segundo_metadados.read_bytes()


def test_nao_gera_saida_diante_de_erro(tmp_path):
    xlsx = tmp_path / "entrada.xlsx"
    saida = tmp_path / "saida.json"
    metadados = tmp_path / "metadados.json"
    referencia = tmp_path / "referencia.json"
    criar_xlsx(xlsx, [linha(999999, "MG", "DESCONHECIDO")])
    referencia.write_text(json.dumps(referencia_nominal()), encoding="utf-8")

    resultado = IMPORTADOR.main([
        "--xlsx", str(xlsx),
        "--ibge-json", str(referencia),
        "--ibge-versao", "2026-08-04",
        "--data-importacao", "2026-08-04",
        "--saida", str(saida),
        "--metadados", str(metadados),
    ])

    assert resultado == 1
    assert not saida.exists()
    assert not metadados.exists()


@pytest.mark.parametrize("codigo", ["", "314780.5", "ABCDEF", "31478"])
def test_codigo_ms_invalido_interrompe_sem_gerar_saida(tmp_path, capsys, codigo):
    xlsx = tmp_path / "entrada.xlsx"
    saida = tmp_path / "saida.json"
    metadados = tmp_path / "metadados.json"
    referencia = tmp_path / "referencia.json"
    criar_xlsx(xlsx, [linha(codigo=codigo)])
    referencia.write_text(json.dumps(referencia_nominal()), encoding="utf-8")

    resultado = IMPORTADOR.main([
        "--xlsx", str(xlsx),
        "--ibge-json", str(referencia),
        "--ibge-versao", "2026-08-04",
        "--data-importacao", "2026-08-04",
        "--saida", str(saida),
        "--metadados", str(metadados),
    ])

    assert resultado == 1
    assert "codigo IBGE invalido" in capsys.readouterr().err
    assert not saida.exists()
    assert not metadados.exists()


def test_metadados_contem_exatamente_divergencias_relevantes_e_validacao_pdf():
    caminho = Path(__file__).parents[1] / "data" / "farmacia-popular" / "metadados.json"
    metadados = json.loads(caminho.read_text(encoding="utf-8"))
    esperado = [
        {
            "codigo_ibge": "2922250",
            "uf": "BA",
            "municipio_fonte_ms": "MUQUEM DE SAO FRANCISCO",
            "municipio_exibicao": "Muquém do São Francisco",
        },
        {
            "codigo_ibge": "5107008",
            "uf": "MT",
            "municipio_fonte_ms": "POXOREO",
            "municipio_exibicao": "Poxoréu",
        },
        {
            "codigo_ibge": "1502954",
            "uf": "PA",
            "municipio_fonte_ms": "ELDORADO DOS CARAJAS",
            "municipio_exibicao": "Eldorado do Carajás",
        },
        {
            "codigo_ibge": "2800100",
            "uf": "SE",
            "municipio_fonte_ms": "AMPARO DE SAO FRANCISCO",
            "municipio_exibicao": "Amparo do São Francisco",
        },
        {
            "codigo_ibge": "3550001",
            "uf": "SP",
            "municipio_fonte_ms": "SAO LUIS DO PARAITINGA",
            "municipio_exibicao": "São Luiz do Paraitinga",
        },
    ]

    assert metadados["divergencias_nominais_relevantes"] == esperado
    assert metadados["divergencias_nominais_relevantes"] == sorted(
        esperado,
        key=lambda registro: (
            registro["uf"],
            registro["municipio_exibicao"],
            registro["codigo_ibge"],
        ),
    )
    assert metadados["validacao_pdf"]["nomes_a_revisar"] == [
        "Passa-Vinte -> Passa Vinte",
        "São Luiz -> São Luiz do Anauá",
        "Fortaleza do Tabocão -> Tabocão",
    ]


def test_base_28_07_tem_totais_e_ordem():
    base = Path(__file__).parents[1] / "data" / "farmacia-popular" / "vagas-2026-07-28.json"
    registros = json.loads(base.read_text(encoding="utf-8"))
    assert len(registros) == 1082
    assert len({registro["uf"] for registro in registros}) == 26
    assert sum(registro["vagas_totais"] for registro in registros) == 1644
    assert sum(registro["vagas_preenchidas"] for registro in registros) == 0
    assert sum(registro["vagas_disponiveis"] for registro in registros) == 1644
    assert all(
        isinstance(registro["codigo_ibge"], str)
        and len(registro["codigo_ibge"]) == 7
        and registro["codigo_ibge"].isdigit()
        for registro in registros
    )
    assert len({registro["codigo_ibge"] for registro in registros}) == len(registros)
    assert registros == sorted(
        registros,
        key=lambda registro: (registro["uf"], registro["municipio_exibicao"], registro["codigo_ibge"]),
    )
