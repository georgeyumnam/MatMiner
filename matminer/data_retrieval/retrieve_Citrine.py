"""
This package requires downloading an installing the citrination client:
https://github.com/CitrineInformatics/python-citrination-client

"""
from citrination_client import CitrinationClient
import os
import time
import pandas as pd
from tqdm import tqdm
from pandas.io.json import json_normalize

__author__ = 'Saurabh Bajaj <sbajaj@lbl.gov>'


class CitrineDataRetrieval:
    def __init__(self, api_key=None):
        """
        Args:
            api_key: (str) Your Citrine API key, or None if you've set the CITRINE_KEY environment variable

        Returns: None
        """
        api_key = api_key if api_key else os.environ['CITRINE_KEY']
        self.client = CitrinationClient(api_key, 'http://citrination.com')

    def get_dataframe(self, term=None, formula=None, property=None, contributor=None, reference=None,
                      min_measurement=None, max_measurement=None, from_record=None, data_set_id=None, max_results=None,
                      show_columns=None):
        """
        Gets data from MP in a dataframe format.
        See client docs at http://citrineinformatics.github.io/api-documentation/ for more details on these parameters.

        Args:
            term: (str) general search string; this is searched against all fields
            formula: (str) filter for the chemical formula field; only those results that have chemical formulas that
                contain this string will be returned
            property: (str) name of the property to search for
            contributor: (str) filter for the contributor field; only those results that have contributors that
                contain this string will be returned
            reference: (str) filter for the reference field; only those results that have contributors that
                contain this string will be returned
            min_measurement: (str/num) minimum of the property value range
            max_measurement: (str/num) maximum of the property value range
            from_record: (int) index of the first record to return (indexed from 0)
            data_set_id: (int) id of the particular data set to search on
            max_results: (int) number of records to limit the results to

        Returns: (object) Pandas dataframe object containing the results
        """

        json_data = []
        start = from_record if from_record else 0
        per_page = 100
        refresh_time = 3  # seconds to wait between search calls

        while True:
            if max_results and max_results < per_page:   # use per_page=max_results, eg: in case of max_results=68 < 100
                data = self.client.search(term=term, formula=formula, property=property,
                                          contributor=contributor, reference=reference,
                                          min_measurement=min_measurement, max_measurement=max_measurement,
                                          from_record=start, per_page=max_results, data_set_id=data_set_id)
            else:
                data = self.client.search(term=term, formula=formula, property=property,
                                          contributor=contributor, reference=reference,
                                          min_measurement=min_measurement, max_measurement=max_measurement,
                                          from_record=start, per_page=per_page, data_set_id=data_set_id)
            size = len(data.json()['results'])
            start += size
            json_data.append(data.json()['results'])
            if max_results and len(json_data)*per_page > max_results:   # check if limit is reached
                json_data = json_data[:(max_results / per_page)]          # get first multiple of 100 records
                json_data.append(data.json()['results'][:max_results % per_page])    # get remaining records
                break
            if size < per_page:  # break out of last loop of results
                break
            time.sleep(refresh_time)

        non_meas_df = pd.DataFrame()  # df w/o measurement column
        meas_df = pd.DataFrame()  # df containing only measurement column

        counter = 0  # variable to keep count of sample hit and set indexes

        for page in json_data:
            # df = pd.concat((json_normalize(hit) for hit in set))   # Useful tool for the future
            for hit in tqdm(page):
                counter += 1
                if 'sample' in hit.keys():
                    sample_value = hit['sample']
                    sample_normdf = json_normalize(sample_value)
                    # Make a DF of all non-'measurement' fields
                    non_meas_cols = [cols for cols in sample_normdf.columns if "measurement" not in cols]
                    non_meas_row = pd.DataFrame()
                    for col in non_meas_cols:
                        non_meas_row[col] = sample_normdf[col]
                    non_meas_row.index = [counter] * len(sample_normdf)
                    non_meas_df = non_meas_df.append(non_meas_row)
                    # Make a DF of the 'measurement' array
                    if 'measurement' in sample_value:
                        meas_normdf = json_normalize(sample_value['measurement'])
                        # Extract numbers of properties
                        if 'property.scalar' in meas_normdf.columns:
                            for row, col in enumerate(meas_normdf['property.scalar']):
                                for item in col:
                                    if 'value' in item:
                                        meas_normdf.xs(row)['property.scalar'] = item['value']
                                    # TODO: ask Anubhav how to deal with these and rest of formats
                                    elif 'minimum' in item and 'maximum' in item:
                                        meas_normdf.xs(row)['property.scalar'] = 'Minimum = ' + item[
                                            'minimum'] + ', ' + 'Maximum = ' + item['maximum']
                        # Take all property rows and convert them into columns
                        prop_df = pd.DataFrame()
                        prop_cols = [cols for cols in meas_normdf.columns if "property" in cols]
                        for col in prop_cols:
                            prop_df[col] = meas_normdf[col]
                        prop_df.index = [counter] * len(meas_normdf)
                        prop_df = prop_df.drop_duplicates(['property.name'])
                        if 'property.scalar' in meas_normdf.columns:
                            prop_df = prop_df.pivot(columns='property.name', values='property.scalar')
                        elif 'property.matrix' in meas_normdf.columns:
                            prop_df = prop_df.pivot(columns='property.name', values='property.matrix')
                        prop_df = prop_df.convert_objects(convert_numeric=True)  # Convert columns from object to num
                        # Making a single row DF of non-'measurement.property' columns
                        non_prop_df = pd.DataFrame()
                        non_prop_cols = [cols for cols in meas_normdf.columns if "property" not in cols]
                        for col in non_prop_cols:
                            non_prop_df['measurement.' + col] = meas_normdf[col]
                        if len(non_prop_df) > 0:  # Do not index empty DF (non-'measuremenet.property' columns absent)
                            non_prop_df.index = [counter] * len(meas_normdf)
                        non_prop_df = non_prop_df[:1]  # Take only first row - does not collect non-unique rows
                        units_df = pd.DataFrame()    # Get property unit and insert it as a dict
                        if 'property.units' in meas_normdf.columns:
                            curr_units = dict(zip(meas_normdf['property.name'], meas_normdf['property.units']))
                            units_df['property.units'] = [curr_units]
                            units_df.index = [counter] * len(meas_normdf)
                        meas_df = meas_df.append(pd.concat([prop_df, non_prop_df, units_df], axis=1))

        df = pd.concat([non_meas_df, meas_df], axis=1)
        df.index.name = 'sample'
        if show_columns:
            for column in df.columns:
                if column not in show_columns:
                    df.drop(column, axis=1, inplace=True)
        return df
        df.append
