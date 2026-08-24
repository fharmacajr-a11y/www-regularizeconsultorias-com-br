import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
DATA_DIR = ROOT / "data" / "farmacia-popular"
RECORDS_PATH = DATA_DIR / "vagas-2026-08-20.json"
HISTORICAL_PATH = DATA_DIR / "vagas-2026-07-28.json"
METADATA_PATH = DATA_DIR / "metadados.json"
TOTAL_FIELDS = ("vagas_totais", "vagas_preenchidas", "vagas_disponiveis")


def test_integridade_da_base_atual_e_consistencia_dos_metadados():
    assert RECORDS_PATH.is_file(), "Arquivo da base 2026-08-20 deve existir."
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert isinstance(records, list)
    assert len(records) == 1206
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
        "vagas_totais": 1780,
        "vagas_preenchidas": 10,
        "vagas_disponiveis": 1770,
    }
    assert metadata["quantidade_registros"] == len(records)
    assert metadata["quantidade_ufs"] == len({record["uf"] for record in records})
    assert metadata["totais_vagas"] == calculated
    assert metadata["data_oficial"] == "2026-08-20"


def test_base_historica_28_07_continua_integra():
    assert HISTORICAL_PATH.is_file(), "Arquivo da base histórica 2026-07-28 deve ser preservado."
    records = json.loads(HISTORICAL_PATH.read_text(encoding="utf-8"))

    assert isinstance(records, list)
    assert len(records) == 1082
    assert len({record["uf"] for record in records}) == 26

    calculated = {field: sum(record[field] for record in records) for field in TOTAL_FIELDS}
    assert calculated == {
        "vagas_totais": 1644,
        "vagas_preenchidas": 0,
        "vagas_disponiveis": 1644,
    }
