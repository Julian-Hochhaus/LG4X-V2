import os
import pandas as pd
from mendeleev.fetch import fetch_table


def generate_elements_csv(xps):
    """
    Generate a CSV file of element properties based on a pandas dataframe containing XPS data.

    Parameters:
        xps (pandas.DataFrame): A pandas dataframe containing XPS data for each element. The dataframe should have
                                columns 'symbol', 'alka.trans', 'alka.be', 'alka.rsf', 'aes.trans', 'aes.ke',
                                and 'aes.rsf'.

    Returns:
        None: This function generates a CSV file of element properties, but does not return anything.

    Raises:
        IndexError: If the symbol for an element in the XPS data is not found in the Mendeleev table.

    """
    mendeleev_pt = fetch_table('elements')
    mendeleev_series = fetch_table('series')

    df = pd.DataFrame(columns=['symbol', 'period', 'group_id', 'series_id', 'alka', 'aes', 'atomic_number', 'cpk_color', 'jmol_color', 'series_name', 'series_color'])

    for _, elem in xps.iterrows():
        index = mendeleev_pt.index[mendeleev_pt['symbol'] == elem.symbol].tolist()[0]
        mendeleev_pt_copy = mendeleev_pt.copy()
        mendeleev_pt_copy.loc[mendeleev_pt_copy['group_id'].isna(), 'group_id'] = 100
        row = pd.Series([elem.symbol, mendeleev_pt['period'][index], mendeleev_pt_copy['group_id'][index], mendeleev_pt['series_id'][index], {'trans': elem['alka.trans'], 'be': elem['alka.be'], 'rsf': elem['alka.rsf']}, {'trans': elem['aes.trans'], 'ke': elem['aes.ke'], 'rsf': elem['aes.rsf']}, mendeleev_pt['atomic_number'][index], mendeleev_pt['cpk_color'][index], mendeleev_pt['jmol_color'][index], mendeleev_series['name'].values[mendeleev_pt['series_id'][index]-1], mendeleev_series['color'].values[mendeleev_pt['series_id'][index]-1]], index=df.columns)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    # Save CSV file relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, '../Databases/elements.csv')
    df.to_csv(csv_path, index=False)


if __name__ == '__main__':
    # Read CSV file relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, '../Databases/xps_data.csv')
    xps = pd.read_csv(csv_path)
    generate_elements_csv(xps)
