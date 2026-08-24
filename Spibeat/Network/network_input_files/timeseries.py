import pandas as pd
import os
def generate_dt_timeseries(start_date,end_date):
    """
    Auto-generate DT-wise timeseries and return:
    - output file path
    - filtered dataframe (React-friendly)
    """
    # ============================================================
    # INTERNAL PATHS (NO NEED FROM FRONTEND)
    # ============================================================
    mapping_file = r"C:\RaviNamdev\India Database for Building simulator\reidential_sub_div5\DT_Wise_Buildings.csv"

    base_path = r"C:\RaviNamdev\India Database for Building simulator\Load_all_use_types"

    output_file = r"C:\RaviNamdev\FinalSpibeat\ShapeFile_to_pypsa_Input\shape_to_pypsa_formate_output\timeseries_input.csv"

    # dt_output_folder = r"C:\RaviNamdeyv\India Database for Building simulator\Load_all_use_types\DT_Wise_Load"

    # ============================================================
    # FILE MAP
    # ============================================================
    use_type_file_map = {
        'Residential': os.path.join(base_path, 'CH_Prototype_Residential', 'PEAK_BUILDING_LOAD_FULL_YEAR', 'Total_load_Residential_FULL_YEAR_2023.csv'),
        'School': os.path.join(base_path, 'CH_Prototype_School', 'PEAK_BUILDING_LOAD_FULL_YEAR', 'Total_Load_school_FULL_YEAR_2023.csv'),
        'Commercial': os.path.join(base_path, 'CH_Prototype_Commercial', 'PEAK_BUILDING_LOAD_FULL_YEAR', 'Total_load_Commercial_FULL_YEAR_2023.csv'),
        'Industrial': os.path.join(base_path, 'CH_Prototype_Industrial', 'PEAK_BUILDING_LOAD_FULL_YEAR', 'Total_load_Industrial_FULL_YEAR_2023.csv'),
        'Retail': os.path.join(base_path, 'CH_Prototype_Retail', 'PEAK_BUILDING_LOAD_FULL_YEAR', 'Total_load_Retail_FULL_YEAR_2023.csv'),
        'University': os.path.join(base_path, 'CH_Prototype_University', 'PEAK_BUILDING_LOAD_FULL_YEAR', 'Total_load_University_FULL_YEAR_2023.csv'),
        'Mixed': os.path.join(base_path, 'CH_Prototype_Mixed', 'PEAK_BUILDING_LOAD_FULL_YEAR', 'Total_load_Mixed_FULL_YEAR_2023.csv')
    }

    # ============================================================
    # LOAD MAPPING
    # ============================================================
    if not os.path.exists(mapping_file):
        raise FileNotFoundError(f"Mapping file not found: {mapping_file}")

    mapping_df = pd.read_csv(mapping_file)
    mapping_df.columns = mapping_df.columns.str.strip()

    # ============================================================
    # LOAD USE TYPE DATA
    # ============================================================
    use_type_data = {}

    for use_type, file_path in use_type_file_map.items():
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.strip()
            use_type_data[use_type] = df
        else:
            print(f"WARNING: Missing file for {use_type}: {file_path}")

    # ============================================================
    # BUILD DT TIMESERIES
    # ============================================================
    final_df = None

    for _, row in mapping_df.iterrows():
        try:
            building_name = str(row.get("Name", "")).strip()
            use_type = str(row.get("Use_type", "")).strip()
            assigned_dt = f"DT{str(row.get('Assigned_DT', '')).strip()}"

            if use_type not in use_type_data:
                continue

            load_df = use_type_data[use_type]

            if building_name not in load_df.columns:
                continue

            if final_df is None:
                final_df = pd.DataFrame()
                final_df["timestamp"] = load_df.iloc[:, 0]

            if assigned_dt not in final_df.columns:
                final_df[assigned_dt] = 0

            final_df[assigned_dt] += load_df[building_name]

        except Exception as e:
            print(f"ERROR processing row: {e}")
            continue

    # ============================================================
    # 🚨 SAFETY CHECK (MOST IMPORTANT FIX)
    # ============================================================
    if final_df is None or final_df.empty:
        raise ValueError("No data generated. Check mapping file or input CSVs.")

    # ============================================================
    # SORT DT COLUMNS
    # ============================================================
    dt_cols = [c for c in final_df.columns if c != "timestamp"]
    dt_cols_sorted = sorted(dt_cols, key=lambda x: int(x.replace("DT", "")))
    final_df = final_df[["timestamp"] + dt_cols_sorted]

    # ============================================================
    # FILTER DATE RANGE
    # ============================================================
    if start_date and end_date:
        final_df["timestamp"] = pd.to_datetime(final_df["timestamp"], errors="coerce")

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) + pd.Timedelta(days=1)

        final_df = final_df[
            (final_df["timestamp"] >= start) &
            (final_df["timestamp"] < end)
        ]

    # ============================================================
    # CONVERT kW → MW
    # ============================================================
    mw_df = final_df.copy()
    dt_columns = [c for c in mw_df.columns if c != "timestamp"]
    mw_df[dt_columns] = mw_df[dt_columns] / 1000

    # ============================================================
    # SAVE FILE
    # ============================================================
    mw_df.to_csv(output_file, index=False)

    # ============================================================
    # RETURN FOR REACT
    # ============================================================
    return {
        "file_path": output_file,
        "columns": mw_df.columns.tolist(),
        "data": mw_df.to_dict(orient="records")
    }