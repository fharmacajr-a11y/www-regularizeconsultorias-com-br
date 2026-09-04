import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[1]
DATA_DIR = ROOT / "data" / "farmacia-popular"
RECORDS_PATH = DATA_DIR / "vagas-2026-09-03.json"
HISTORICAL_PATHS = (DATA_DIR / "vagas-2026-08-20.json", DATA_DIR / "vagas-2026-07-28.json")
METADATA_PATH = DATA_DIR / "metadados.json"
TOTAL_FIELDS = ("vagas_totais", "vagas_preenchidas", "vagas_disponiveis")


def test_integridade_da_base_atual_e_consistencia_dos_metadados():
    assert RECORDS_PATH.is_file(), "Arquivo da base 2026-09-03 deve existir."
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert isinstance(records, list)
    assert len(records) == 1541
    assert len({record["uf"] for record in records}) == 26

    codes = [record["codigo_ibge"] for record in records]
    assert all(isinstance(code, str) and len(code) == 7 and code.isdigit() for code in codes)
    assert len(codes) == len(set(codes))

    sorted_records = sorted(
        records,
        key=lambda r: (r["uf"], r["municipio_exibicao"], r["codigo_ibge"]),
    )
    assert records == sorted_records, "Registros devem estar ordenados deterministicamente por UF, nome e código."

    for record in records:
        assert isinstance(record["codigo_ibge"], str) and len(record["codigo_ibge"]) == 7
        assert isinstance(record["regiao"], str) and record["regiao"] in {
            "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"
        }
        assert isinstance(record["uf"], str) and len(record["uf"]) == 2 and record["uf"].isupper()
        assert isinstance(record["municipio_fonte_ms"], str) and record["municipio_fonte_ms"].strip()
        assert isinstance(record["municipio_exibicao"], str) and record["municipio_exibicao"].strip()
        assert "situacao" not in record
        assert all(type(record[field]) is int and record[field] >= 0 for field in TOTAL_FIELDS)
        assert record["vagas_preenchidas"] + record["vagas_disponiveis"] == record["vagas_totais"]

    calculated = {field: sum(record[field] for record in records) for field in TOTAL_FIELDS}
    assert calculated == {
        "vagas_totais": 3082,
        "vagas_preenchidas": 963,
        "vagas_disponiveis": 2119,
    }
    assert metadata["quantidade_registros"] == len(records)
    assert metadata["quantidade_ufs"] == len({record["uf"] for record in records})
    assert metadata["totais_vagas"] == calculated
    assert metadata["data_oficial"] == "2026-09-03"


def test_bases_historicas_continuam_integras():
    """As bases anteriores permanecem no repositório como registro histórico."""
    esperado = {
        "vagas-2026-08-20.json": (1206, {"vagas_totais": 1780, "vagas_preenchidas": 10, "vagas_disponiveis": 1770}),
        "vagas-2026-07-28.json": (1082, {"vagas_totais": 1644, "vagas_preenchidas": 0, "vagas_disponiveis": 1644}),
    }
    for path in HISTORICAL_PATHS:
        assert path.is_file(), f"Base histórica {path.name} deve ser preservada."
        records = json.loads(path.read_text(encoding="utf-8"))
        quantidade, totais = esperado[path.name]

        assert isinstance(records, list)
        assert len(records) == quantidade
        assert len({record["uf"] for record in records}) == 26

        calculated = {field: sum(record[field] for record in records) for field in TOTAL_FIELDS}
        assert calculated == totais


def test_contagens_reais_por_situacao_na_base_vigente():
    """Protege as contagens que alimentam os filtros da consulta.

    A soma de vagas preenchidas (963) coincide com o número de municípios
    preenchidos porque toda ocupação da base de 03/09 é de exatamente uma
    vaga por município. A igualdade é verificada, não presumida.
    """
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))

    com_preenchidas = [r for r in records if r["vagas_preenchidas"] > 0]
    com_disponiveis = [r for r in records if r["vagas_disponiveis"] > 0]
    sem_disponiveis = [r for r in records if r["vagas_disponiveis"] == 0]

    assert len(com_preenchidas) == 963
    assert len(com_disponiveis) == 1541
    assert len(sem_disponiveis) == 0
    assert all(r["vagas_preenchidas"] == 1 for r in com_preenchidas)
    assert sum(r["vagas_preenchidas"] for r in com_preenchidas) == len(com_preenchidas)

    combinacoes = Counter(
        (r["vagas_totais"], r["vagas_preenchidas"], r["vagas_disponiveis"]) for r in records
    )
    assert combinacoes == {(2, 1, 1): 963, (2, 0, 2): 578}
