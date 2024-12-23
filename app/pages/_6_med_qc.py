import streamlit as st
import pandas as pd
import os
import logging
import time
from common_qc import read_data, check_required_variables, generate_summary_stats
from common_qc import validate_and_convert_dtypes, name_category_mapping
from logging_config import setup_logging
from common_features import set_bg_hack_url

def show_meds_qc():
    '''
    '''
    set_bg_hack_url()

    #Initialize logger
    setup_logging()
    logger = logging.getLogger(__name__)

    # Page title
    TABLE = "Medications Adminstered Continuously"
    table = "Medication_admin_continuous"
    st.title(f"{TABLE} Quality Check")

    logger.info(f"!!! Starting QC for {TABLE}.")

    # Main 
    qc_summary = []
    qc_recommendations = []

    if 'root_location' in st.session_state and 'filetype' in st.session_state:
        root_location = st.session_state['root_location']
        filetype = st.session_state['filetype']
        filepath = os.path.join(root_location, f'clif_medication_admin_continuous.{filetype}')

        logger.info(f"Filepath set to {filepath}")

        if os.path.exists(filepath):
            progress_bar = st.progress(0, text="Quality check in progress. Please wait...")
            logger.info(f"File {filepath} exists.")

            # Start time
            start_time = time.time()

            progress_bar.progress(5, text='File found...')

            progress_bar.progress(10, text='Starting QC...')

            # 1. Medications Administered Continuously Detailed QC 
            with st.expander("Expand to view", expanded=False):
                # Load the file
                with st.spinner("Loading data..."):
                    progress_bar.progress(20, text='Loading data...')
                    logger.info("~~~ Loading data ~~~")
                    data = read_data(filepath, filetype)
                    logger.info("Data loaded successfully.")
                    

                # Display the data
                logger.info("~~~ Displaying data ~~~")
                st.write(f"## {TABLE} Data Review")
                with st.spinner("Loading data preview..."):
                    progress_bar.progress(25, text='Loading data preview...')
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
                    logger.info("Displayed data.")


                # Validate and convert data types
                logger.info("~~~ Validating data types ~~~")
                st.write("## Data Type Validation")
                with st.spinner("Validating data types..."):
                    progress_bar.progress(30, text='Validating data types...')
                    data, validation_results = validate_and_convert_dtypes(table, data)
                    validation_df = pd.DataFrame(validation_results, columns=['Column', 'Actual', 'Expected', 'Status'])
                    mismatch_columns = [row[0] for row in validation_results if row[1] != row[2]]
                    convert_dtypes = False
                    if mismatch_columns:
                        convert_dtypes = True
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
                            'Missing (%)': missing_percentages.map('{:.2f}%'.format)
                        })
                        missing_info_sorted = missing_info.sort_values(by='Missing Count', ascending=False)
                        st.write(missing_info_sorted)
                        qc_summary.append("Missing values found in columns - " + ', '.join(missing_info[missing_info['Missing Count'] > 0].index.tolist()))
                    else:
                        st.write("No missing values found in all required columns.")
                    logger.info("Checked for missing values.")

                
                # # Display summary statistics  
                # st.write(f"## {TABLE} Summary Statistics")
                # with st.spinner("Displaying summary statistics..."):
                #     progress_bar.progress(50, text='Displaying summary statistics...')
                #     logger.info("~~~ Displaying summary statistics ~~~")  
                #     summary = data.describe()
                #     st.write(summary)
                #     logger.info("Displayed summary statistics.")

                
                # Check for required columns
                logger.info("~~~ Checking for required columns ~~~")    
                st.write(f"## {TABLE} Required Columns")
                with st.spinner("Checking for required columns..."):
                    progress_bar.progress(60, text='Checking for required columns...')
                    required_cols_check = check_required_variables(table, data)
                    st.write(required_cols_check)
                    qc_summary.append(required_cols_check)
                    if required_cols_check != f"All required columns present for '{TABLE}'.":
                        qc_recommendations.append("Some required columns are missing. Please ensure all required columns are present.")  
                        logger.warning("Some required columns are missing.")
                    logger.info("Checked for required columns.")
                
                # Medication Category Summary Statistics
                st.write("## Medication Dose Summary Statistics")
                with st.spinner("Summarizing medication doses by categories..."):
                    progress_bar.progress(75, text='Summarizing medication doses by categories...')
                    logger.info("~~~ Summarizing medication doses by categories ~~~")  
                    med_summary_stats = generate_summary_stats(data, 'med_category', 'med_dose')
                    st.write(med_summary_stats)
                    logger.info("Generated medication dose by category summary statistics.")

                # Name to Category mappings
                logger.info("~~~ Mapping ~~~")
                st.write('## Name to Category Mapping')
                with st.spinner("Displaying Name to Category Mapping..."):
                    progress_bar.progress(90, text='Displaying Name to Category Mapping...')
                    mappings = name_category_mapping(data)
                    n = 1
                    for i, mapping in enumerate(mappings):
                        mapping_name = mapping.columns[0]
                        mapping_cat = mapping.columns[1]
                        st.write(f"{n}. Mapping `{mapping_name}` to `{mapping_cat}`")
                        st.write(mapping.reset_index().drop("index", axis = 1))
                        n += 1

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
                # if st.session_state:
                    st.write("## Summary")
                    for i, point in enumerate(qc_summary):
                        st.markdown(f"{i + 1}. {point}")

                    st.write("## Recommendations")
                    for i, recommendation in enumerate(qc_recommendations):
                        st.markdown(f"{i + 1}. {recommendation}")
            
            logger.info("Displayed QC Summary and Recommendations.")

        else:
            st.write(f"File not found. Please provide the correct root location and/or file type to proceed.")

    else:
        st.write("Please provide the root location and file type to proceed.")
        logger.warning("Root location and/or file type not provided.")

