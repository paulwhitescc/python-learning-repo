import pandas as pd
from config_903 import DateCols, EthnicSubcatgories
from dateutil.relativedelta import relativedelta

import numpy as np

def format_dates(column):
    column.replace(r"^\s*$", pd.NaT, regex = True)
    column = column.fillna(pd.NaT)
    try:
        column = pd.to_datetime(column,format = "%d/%m/%Y")
        return column
    except:
        raise ValueError(f"Unknown date format in {column.name}, expected dd/mm/yyyy")
    
def calculate_age_bands(age):
    if age < 1:
        return "a) Under 1"
    elif age < 5:
        return "b) 1-4"
    elif age < 10:
        return "c) 5-9"
    elif age < 16:
        return "d) 10-15"
    elif age >= 16:
        return "e) 16+"
    else:
        return "f) age error"
    
def clean_903_table(df: pd.DataFrame, collection_end: pd.Timestamp) -> pd.DataFrame:
    '''
    Takes tables from the 903 as DataFrames and outputs cleaned tables    
    '''
    clean_df = df.copy()

    # remove index column
    if "index" in df.columns:
     clean_df.drop("index", axis=1, inplace=True)
    
    # format columns as dates
    for column in clean_df.columns:
     if column in DateCols.cols.value:
      clean_df[f"{column}_dt"] = format_dates(clean_df[column])

    # make ethic main group column
    if "ETHNIC" in clean_df.columns:
     clean_df["ETHNICITY"] = clean_df["ETHNIC"].apply(
      lambda ethnicity: EthnicSubcatgories[ethnicity].value
     )

    # make age column and age buckets column
    if "DOB_dt" in clean_df.columns:
     clean_df["AGE"] = clean_df["DOB_dt"].apply(
      lambda dob: relativedelta(dt1=collection_end, dt2=dob).normalized().years
     )
     clean_df["AGE_BUCKETS"] = clean_df["AGE"].apply(calculate_age_bands)

    return clean_df

def group_calculation(df, column, measure_name):
    '''
    A function to group a df by input coloumn, output with count
    and percentage to a dataframe with renamed columns. 
    '''
    grouped = df.groupby(column).size()
    grouped = grouped.to_frame(f'{measure_name} - Count').reset_index()
    grouped = grouped.rename(columns={column:'Ethnicity'})

    grouped[f'{measure_name} - Percentage'] = (grouped[f'{measure_name} - Count'] / 
                                                    grouped[f'{measure_name} - Count'].sum()) * 100
    
    return grouped
    
def time_difference(start_col, end_col, business_days=False):
    '''
    Takes two date columns and returns difference in time, 
    can also be used to find difference in business days
    '''
    if business_days:
        #np.busday_count can only use datetime64(D) type data, so we need to convert the objects
        time_diff = np.busday_count(
           start_col.values.astype("datetime64[D]"),
           end_col.values.astype("datetime64[D]")
        )
    else:
        time_diff = end_col - start_col
        time_diff = time_diff / pd.Timedelta(days=1)

    return time_diff.astype("int")


def multiples_same_event(df, event_name):
   df = df.copy()

   multiples = df.groupby(["CHILD"]).size().to_frame("Number of events").reset_index()

   multiples = multiples.groupby(["Number of events"]).size().to_frame("Children with number of events").reset_index()

   multiples['Event Type'] = "Number of episodes"

   multiples = multiples[["Event Type","Number of events","Children with number of events"]]

   return multiples

def group_calculation_year(df, year_col, col_to_group, measure_name):
    #pass
    df = df.copy()

    grouped = df.groupby([year_col, col_to_group]).size()
    grouped = grouped.to_frame("Count").reset_index()
    grouped = grouped.rename(columns={col_to_group:"Value"})

    grouped["Percentage by year"] = grouped.apply(
       lambda x: x["Count"] / grouped.loc[grouped[year_col] == x[year_col]].Count.sum()
       * 100,
       axis=1)
    
    grouped["Measure"] = measure_name

    grouped=grouped[[year_col,"Measure", "Value", "Count", "Percentage by year"]]

    return grouped

def appears_on_both(df1,df2,measure_name):
   df1 = df1.drop_duplicates(subset=["CHILD"]).copy()
   df2 = df2.drop_duplicates(subset=["CHILD"]).copy()

   merged_df = df1.merge(df2, how="inner", on=["CHILD"])

   merged_df["on_both"] = "Yes"

   df = df1.merge(merged_df[["CHILD", "on_both"]], how="left", on="CHILD")

   df.fillna({"on_both":"No"}, inplace=True)

   output = group_calculation(df, "on_both", measure_name) 

   return output