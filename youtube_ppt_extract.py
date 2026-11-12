import os
import re
import glob
import pandas as pd


def read_csv_with_fallback(path, nrows=None, dtype=None):
    """
    Attempts to load a CSV file using semicolon (;) first, then falling back to comma (,).
    """
    for separator in [';', ',']:
        try:
            df = pd.read_csv(
                path,
                sep=separator,
                engine='python',
                nrows=nrows,
                dtype=dtype,
                on_bad_lines='skip'
            )
            if len(df.columns) > 1:
                return df
        except Exception:
            continue

    return pd.read_csv(path, sep=None, engine='python', nrows=nrows, dtype=dtype, on_bad_lines='skip')


def parse_year_range(year_range_str):
    """
    Parses a string like '2015-2026' into (2015, 2026).
    Also accepts a single year like '2020' -> (2020, 2020).
    """
    year_range_str = year_range_str.strip()
    match = re.match(r'^\s*(\d{4})\s*-\s*(\d{4})\s*$', year_range_str)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            start, end = end, start
        return start, end

    match = re.match(r'^\s*(\d{4})\s*$', year_range_str)
    if match:
        year = int(match.group(1))
        return year, year

    raise ValueError(f"Could not parse year range from '{year_range_str}'. Use format like 2015-2026.")


def extract_year_from_filename(filename):
    """
    Looks for a 4-digit year (19xx or 20xx) anywhere in the filename.
    Returns the year as int, or None if the filename has no such year.
    If a year IS found here, that file is parsed only when the year
    falls inside the requested range (checked by the caller).
    """
    match = re.search(r'(?:19|20)\d{2}', filename)
    if match:
        return int(match.group(0))
    return None


# Common column names that might hold a date or year value
YEAR_LIKE_COLUMN_HINTS = ['year', 'anno', 'data', 'date', 'fecha', 'jahr']


def find_year_like_column(columns):
    """
    Returns the first column name that looks like it could hold a year/date, or None.
    """
    cleaned = [str(c).strip().lower() for c in columns]
    for hint in YEAR_LIKE_COLUMN_HINTS:
        for original, clean in zip(columns, cleaned):
            if hint in clean:
                return original
    return None


def extract_year_from_value(value):
    """
    Given a cell value (could be a full date, or just a year), extract a 4-digit year if present.
    """
    if pd.isna(value):
        return None
    match = re.search(r'(19|20)\d{2}', str(value))
    if match:
        return int(match.group(0))
    return None


def combine_colab_csvs_by_year_client_text(
    folder_path,
    year_start,
    year_end,
    client_column,
    client_number,
    search_column,
    search_values,
):
    """
    Finds all CSV files in a Google Drive folder from Colab, keeps only files/rows
    that fall within [year_start, year_end], filters rows to the given client_number
    inside client_column, then keeps only rows where search_column contains ANY of
    the given search_values (case-insensitive, partial match).
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.exists(folder_path):
        print(f"\n[ERROR] The directory '{folder_path}' cannot be found.")
        print("Please verify the path in DRIVE_FOLDER.")
        return pd.DataFrame()

    # --- Automatically delete any old consolidated file first ---
    output_path = os.path.join(folder_path, "consolidated_results_multi_year.csv")
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
            print("[INFO] Deleted old 'consolidated_results_multi_year.csv' to ensure a completely fresh run.")
        except Exception as e:
            print(f"[WARNING] Could not delete old consolidated file: {e}")

    # Find all CSV files (.csv and .CSV)
    csv_patterns = [os.path.join(folder_path, "*.csv"), os.path.join(folder_path, "*.CSV")]
    raw_paths = []
    for pattern in csv_patterns:
        raw_paths.extend(glob.glob(pattern))

    # Remove duplicates and filter out the results file name to be safe
    file_paths = list(set(os.path.abspath(p) for p in raw_paths))
    file_paths = [p for p in file_paths if "consolidated_results_multi_year" not in os.path.basename(p)]

    total_files = len(file_paths)
    if total_files == 0:
        print(f"\n[WARNING] Found 0 CSV files in the folder: {folder_path}")
        return pd.DataFrame()

    print(f"\nFound {total_files} unique CSV file(s) to process in Google Drive.")
    print(f"Year range filter: {year_start}-{year_end}")
    print(f"Client column: '{client_column}' | Client number: '{client_number}'")
    print(f"Search column: '{search_column}' | Values to search: {search_values}")
    filtered_dfs = []

    client_col_cleaned = str(client_column).strip().lower()
    search_col_cleaned = str(search_column).strip().lower()
    client_number_cleaned = str(client_number).strip()
    search_values_cleaned = [str(v).strip() for v in search_values if str(v).strip()]

    for idx, path in enumerate(file_paths, 1):
        file_name = os.path.basename(path)
        try:
            # 1. Try to determine the file's year from its filename first
            file_year = extract_year_from_filename(file_name)

            if file_year is not None:
                if not (year_start <= file_year <= year_end):
                    print(f"[{idx}/{total_files}] Skipping {file_name}: file year {file_year} outside range.")
                    continue

            # 2. Read just the headers to validate required columns are present
            first_look = read_csv_with_fallback(path, nrows=0)
            cleaned_headers = [str(col).strip().lower() for col in first_look.columns]

            if client_col_cleaned not in cleaned_headers:
                print(f"[{idx}/{total_files}] Skipping {file_name}: client column '{client_column}' is missing.")
                continue
            if search_col_cleaned not in cleaned_headers:
                print(f"[{idx}/{total_files}] Skipping {file_name}: search column '{search_column}' is missing.")
                continue

            original_client_col = first_look.columns[cleaned_headers.index(client_col_cleaned)]
            original_search_col = first_look.columns[cleaned_headers.index(search_col_cleaned)]

            # 3. Read the entire file
            df = read_csv_with_fallback(path, dtype=str)
            df.columns = df.columns.str.strip()

            # 4. If filename had no year, try to filter rows using a year/date-like column
            if file_year is None:
                year_col = find_year_like_column(df.columns)
                if year_col is not None:
                    row_years = df[year_col].apply(extract_year_from_value)
                    in_range_mask = row_years.apply(
                        lambda y: (y is not None) and (year_start <= y <= year_end)
                    )
                    if in_range_mask.any():
                        df = df[in_range_mask]
                    else:
                        print(f"[{idx}/{total_files}] Skipping {file_name}: no rows within year range "
                              f"(using column '{year_col}').")
                        continue
                else:
                    print(f"[{idx}/{total_files}] [WARNING] No year found in filename or columns for "
                          f"{file_name}. Including all rows (year filter could not be applied).")

            # 5. Filter rows to the requested client number
            client_series = df[original_client_col].fillna("").astype(str)
            client_mask = client_series.str.contains(client_number_cleaned, case=False, na=False, regex=False)
            df_client = df[client_mask]

            if df_client.empty:
                print(f"[{idx}/{total_files}] Processed {file_name}: 0 rows for client '{client_number}'.")
                continue

            # 6. Within those rows, keep the ones where search_column matches ANY of the search values
            search_series = df_client[original_search_col].fillna("").astype(str)
            if search_values_cleaned:
                value_mask = pd.Series(False, index=df_client.index)
                for val in search_values_cleaned:
                    value_mask = value_mask | search_series.str.contains(val, case=False, na=False, regex=False)
                matching_rows = df_client[value_mask]
            else:
                matching_rows = df_client

            if not matching_rows.empty:
                matching_rows = matching_rows.copy()
                matching_rows.insert(0, "source_file", file_name)
                filtered_dfs.append(matching_rows)
                print(f"[{idx}/{total_files}] Processed {file_name}: Found {len(matching_rows)} matches.")
            else:
                print(f"[{idx}/{total_files}] Processed {file_name}: 0 matches.")

        except Exception as e:
            print(f"[{idx}/{total_files}] Error reading {file_name}: {e}")

    # Combine all filtered results
    if filtered_dfs:
        combined_df = pd.concat(filtered_dfs, ignore_index=True)
        print(f"\nSuccess! Processing completed. Total rows collected: {len(combined_df)}")
        return combined_df
    else:
        print("\nFinished processing. No matching data was found across any files.")
        return pd.DataFrame()


# =====================================================================
# CONFIGURATION FOR GOOGLE COLAB
# =====================================================================

# Your verified Google Drive folder path
DRIVE_FOLDER = "/content/drive/MyDrive/csv_files"

# Dynamic User Inputs
print("--- Script Configuration ---")
YEAR_RANGE_INPUT = input("Year (e.g. 2015-2026): ").strip()
CLIENT_COLUMN = input("Choose column name which contains client name: ").strip()
CLIENT_NUMBER = input("Choose client number: ").strip()
SEARCH_COLUMN = input("Choose column name to search text: ").strip()
VALUES_INPUT = input("Provide the value to search for (comma separated, example: COMUNE DI, FORLI', MILANESI): ").strip()
print("-" * 28)

try:
    START_YEAR, END_YEAR = parse_year_range(YEAR_RANGE_INPUT)
except ValueError as e:
    print(f"[ERROR] {e}")
    raise SystemExit(1)

SEARCH_VALUES = [v.strip() for v in VALUES_INPUT.split(",") if v.strip()]

# Execute the script with your custom inputs
final_dataframe = combine_colab_csvs_by_year_client_text(
    folder_path=DRIVE_FOLDER,
    year_start=START_YEAR,
    year_end=END_YEAR,
    client_column=CLIENT_COLUMN,
    client_number=CLIENT_NUMBER,
    search_column=SEARCH_COLUMN,
    search_values=SEARCH_VALUES,
)

# Preview and Save Results back to your Google Drive
if not final_dataframe.empty:
    print("\n--- Preview of the combined data (First 5 rows) ---")
    print(final_dataframe.head())

    # Save the consolidated CSV file directly back into your folder
    output_path = os.path.join(DRIVE_FOLDER, "consolidated_results_multi_year.csv")
    final_dataframe.to_csv(output_path, index=False, sep=";")
    print(f"\nSaved combined file directly to Google Drive: {output_path}")
