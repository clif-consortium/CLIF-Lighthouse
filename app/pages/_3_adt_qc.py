import streamlit as st
import pandas as pd
import os
import logging
import time
from common_qc import read_data, check_required_variables, check_time_overlap, fix_overlaps
from common_qc import validate_and_convert_dtypes, name_category_mapping
from logging_config import setup_logging
from common_features import set_bg_hack_url

def show_adt_qc():
    '''
    '''
    set_bg_hack_url()

    #Initialize logger
    setup_logging()
    logger = logging.getLogger(__name__)

    # Page title
    TABLE = "ADT"
    st.title(f"{TABLE} Quality Check")

    logger.info(f"!!! Starting QC for {TABLE}.")

    # Main
    qc_summary = []
    qc_recommendations = []


    if 'root_location' in st.session_state and 'filetype' in st.session_state:
        root_location = st.session_state['root_location']
        filetype = st.session_state['filetype']
        filepath = os.path.join(root_location, f'clif_adt.{filetype}')

        logger.info(f"Filepath set to {filepath}")

        if os.path.exists(filepath):
            progress_bar = st.progress(0, text="Quality check in progress. Please wait...")
            logger.info(f"File {filepath} exists.")

            # Start time
            start_time = time.time()

            progress_bar.progress(5, text='File found...')

            progress_bar.progress(10, text='Starting QC...')
    
            with st.expander("Expand to view", expanded=False):
                # Load the file
                with st.spinner("Loading data..."):
                    progress_bar.progress(15, text='Loading data...')
                    logger.info("~~~ Loading data ~~~")
                    data = read_data(filepath, filetype)
                    logger.info("Data loaded successfully.")


                # Display the data
                logger.info("~~~ Displaying data ~~~")
                st.write(f"## {TABLE} Data Preview")
                with st.spinner("Loading data preview..."):
                    progress_bar.progress(20, text='Loading data preview...')
                    total_counts = data.shape[0]
                    ttl_unique_encounters = data['hospitalization_id'].nunique()
                    duplicate_count = data.duplicated().sum()
                    st.write(f"Total records: {total_counts}")
                    st.write(f"Total unique hospital encounters: {ttl_unique_encounters}")
                    if duplicate_count > 0:
                        st.write(f"Duplicate records: {duplicate_count}")
                        qc_summary.append(f"{duplicate_count} duplicate(s) found in the data.")
                        qc_recommendations.append("Duplicate records found. Please review and remove duplicates.")
                    else:
                        st.write("No duplicate records found.")
                    st.write(data.head())
                    logger.info("Data displayed.")

                
                # Validate and convert data types
                st.write("## Data Type Validation")
                with st.spinner("Validating data types..."):
                    progress_bar.progress(30, text='Validating data types...')
                    logger.info("~~~ Validating data types ~~~")
                    data, validation_results = validate_and_convert_dtypes(TABLE, data)
                    validation_df = pd.DataFrame(validation_results, columns=['Column', 'Actual', 'Expected', 'Status'])
                    mismatch_columns = [row[0] for row in validation_results if row[1] != row[2]]
                    if mismatch_columns:
                        qc_summary.append("Some columns have mismatched data types.")
                        qc_recommendations.append("Some columns have mismatched data types. Please review and convert to the expected data types.")
                    st.write(validation_df)
                    logger.info("Data type validation completed.")

                
                # Display missingness for each column
                st.write(f"## Missingness")
                with st.spinner("Checking for missing values..."):
                    progress_bar.progress(40, text='Checking for missing values...')
                    logger.info("~~~ Checking for missing values ~~~")
                    missing_counts = data.isnull().sum()
                    if missing_counts.any():
                        missing_percentages = (missing_counts / total_counts) * 100
                        missing_info = pd.DataFrame({
                            'Missing Count': missing_counts,
                            'Missing Percentage': missing_percentages.map('{:.2f}%'.format)
                        })
                        missing_info_sorted = missing_info.sort_values(by='Missing Count', ascending=False)
                        st.write(missing_info_sorted)
                        qc_summary.append("Missing values found in columns - " + ', '.join(missing_info[missing_info['Missing Count'] > 0].index.tolist()))
                    else:
                        st.write("No missing values found in all required columns.")
                    logger.info("Checked for missing values.")

            
                # Check for required columns    
                logger.info("~~~ Checking for required columns ~~~")  
                st.write(f"## {TABLE} Required Columns")
                with st.spinner("Checking for required columns..."):
                    progress_bar.progress(60, text='Checking for required columns...')
                    required_cols_check = check_required_variables(TABLE, data)
                    st.write(required_cols_check)
                    qc_summary.append(required_cols_check)
                    if required_cols_check != f"All required columns present for '{TABLE}'.":
                        qc_recommendations.append("Some required columns are missing. Please ensure all required columns are present.")  
                        logger.warning("Some required columns are missing.")
                    logger.info("Checked for required columns.")


                # Check for presence of all location categories
                logger.info("~~~ Checking for presence of all location categories ~~~")
                st.write('## Presence of All Location Categories')
                with st.spinner("Checking for presence of all location categories..."):
                    progress_bar.progress(80, text='Checking for presence of all location categories...')
                    reqd_categories = pd.DataFrame(["ER", "OR", "ICU", "Ward", "Other"], 
                                        columns=['location_category'])
                    categories = data['location_category'].unique()
                    if reqd_categories['location_category'].tolist().sort() == categories.tolist().sort():
                        st.write("All location categories are present.")
                        qc_summary.append("All location categories are present.")
                        logger.info("All location categories are present.")
                    else:
                        st.write("Some location categories are missing.")
                        missing_cats = []
                        for cat in reqd_categories['location_category']:
                            if cat not in categories:
                                st.write(f"{cat} is missing.")
                                missing_cats.append(cat)
                        with st.container(border=True):
                            cols = st.columns(3)  
                            for i, missing in enumerate(missing_cats):  
                                col = cols[i % 3]  
                                col.markdown(f"{i + 1}. {missing}")
                        qc_summary.append("Some location categories are missing.")
                        qc_recommendations.append("Some location categories are missing. Please ensure all location categories are present.")
                        logger.warning("Some location categories are missing.")
                    logger.info("Checked for presence of all location categories.")
                
                # Name to Category Mappings
                logger.info("~~~ Mapping ~~~")
                st.write('## Name to Category Mapping')
                with st.spinner("Displaying Name to Category Mapping..."):
                    progress_bar.progress(85, text='Displaying Name to Category Mapping...')
                    mappings = name_category_mapping(data)
                    n = 1
                    for i, mapping in enumerate(mappings):
                        mapping_name = mapping.columns[0]
                        mapping_cat = mapping.columns[1]
                        st.write(f"{n}. Mapping `{mapping_name}` to `{mapping_cat}`")
                        st.write(mapping.reset_index().drop("index", axis = 1))
                        n += 1
                    
                # Check for Concurrent Admissions
                logger.info("~~~ Checking for Overlapping Admissions ~~~")
                st.write('## Checking for Overlapping Admissions')
                with st.spinner("Checking for Overlapping Admissions..."):
                    progress_bar.progress(85, text='Checking for Overlapping Admissions...')
                    overlaps = check_time_overlap(data, root_location, filetype)
                    if len(overlaps) > 0:
                        overlaps = pd.DataFrame(overlaps)
                        st.write(overlaps)
                        qc_summary.append("There appears to be overlapping admissions to different locations.")
                        qc_recommendations.append("Please revise patient out_dttms to reflect appropraitely.")
                    else:
                        st.write("No overlapping admissions found.")
                        qc_summary("No overlapping admissions found.")

                progress_bar.progress(100, text='Quality check completed. Displaying results...')
             

            # End time
            end_time = time.time()
            elapsed_time = end_time - start_time
            st.success(f"Quality check completed. Time taken to run summary: {elapsed_time:.2f} seconds", icon="✅")
            logger.info(f"Time taken to run summary: {elapsed_time:.2f} seconds")
            
            # Display QC Summary and Recommendations
            st.write("# QC Summary and Recommendations")
            logger.info("Displaying QC Summary and Recommendations.")

            with st.expander("Expand to view", expanded=False):
                st.write("## Summary")
                for i, point in enumerate(qc_summary):
                    st.markdown(f"{i + 1}. {point}")

                st.write("## Recommendations")
                for i, recommendation in enumerate(qc_recommendations):
                    st.markdown(f"{i + 1}. {recommendation}")

            logger.info("QC Summary and Recommendations displayed.")

        else:
            st.write(f"File not found. Please provide the correct root location and file type to proceed.")

    else:
        st.write("Please provide the root location and file type to proceed.")
        logger.warning("Root location and/or file type not provided.")

    logger.info(f"!!! Completed QC for {TABLE}.")       

