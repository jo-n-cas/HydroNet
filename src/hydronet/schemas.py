"""Column contract for the processed outputs (instructions Section 5).

The pipeline writes these files; the UI reads them. Fixtures in
tests/fixtures/processed follow the same contract (checked by a test), so switching
``ui.data_dir`` to data/processed fails loudly if the schemas diverge.
"""

from __future__ import annotations

import pandas as pd

SCHEMAS: dict[str, list[str]] = {
    "stations.parquet": ["station_id", "is_chem", "is_bio", "has_raw_bio", "n_chem_obs", "n_bio_obs",
                         "n_parameters", "krw_watertype", "eag", "krw_waterbody", "geometry"],
    # `category` = dictionary P_categorie; needed to assign parameter groups (config/parameter_groups.yaml).
    "coverage.parquet": ["station_id", "source", "parameter", "n_observations", "NAME", "UNIT", "GROUP",
                         "category"],
    "bio_values.parquet": ["station_id", "sample_id", "datetime", "parameter", "taxon", "taxon_group", "value",
                           "unit", "limit_flag", "quality_code", "qa_flag"],
    "hydrology.parquet": ["sensor_id", "site", "date", "quantity", "value", "qa_flag"],
    "rwzi_effluent.parquet": ["installation", "installation_name", "measurement_point", "date", "product",
                              "quantity", "parameter", "unit", "value"],
    "amstel_stations.parquet": ["station_id", "is_chem", "is_bio", "distance_to_river_m", "chainage_m",
                                "beyond_river_end"],
    "rejected_values.parquet": ["source_file", "station_id", "parameter", "value", "reason"],
}


def missing_columns(name: str, df: pd.DataFrame) -> list[str]:
    """Contract columns absent from ``df`` (empty list = conforms)."""
    return [c for c in SCHEMAS[name] if c not in df.columns]
