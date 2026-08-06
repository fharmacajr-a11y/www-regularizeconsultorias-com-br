import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
DATA_DIR = ROOT / "data" / "farmacia-popular"
RECORDS_PATH = DATA_DIR / "vagas-2026-07-28.json"
METADATA_PATH = DATA_DIR / "metadados.json"
TOTAL_FIELDS = ("vagas_totais", "vagas_preenchidas", "vagas_disponiveis")


def test_integridade_da_base_atual_e_consistencia_dos_metadados():
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert isinstance(records, list)
    assert len(records) == 1082
    assert len({record["uf"] for record in records}) == 26

    codes = [record["codigo_ibge"] for record in records]
    assert all(isinstance(code, str) and len(code) == 7 and code.isdigit() for code in codes)
    assert len(codes) == len(set(codes))

    for record in records:
        assert all(type(record[field]) is int and record[field] >= 0 for field in TOTAL_FIELDS)
        assert record["vagas_preenchidas"] + record["vagas_disponiveis"] == record["vagas_totais"]

    calculated = {field: sum(record[field] for record in records) for field in TOTAL_FIELDS}
    assert calculated == {
        "vagas_totais": 1644,
        "vagas_preenchidas": 0,
        "vagas_disponiveis": 1644,
    }
    assert metadata["quantidade_registros"] == len(records)
    assert metadata["quantidade_ufs"] == len({record["uf"] for record in records})
    assert metadata["totais_vagas"] == calculated
