import streamlit as st
import pandas as pd
import os
import logging
import time
from common_qc import read_data, check_required_variables
from common_qc import replace_outliers_with_na_wide, plot_histograms_by_device_category
from common_qc import validate_and_convert_dtypes, name_category_mapping
from logging_config import setup_logging
from common_features import set_bg_hack_url

def show_respiratory_support_qc():
    '''
    '''
    set_bg_hack_url()

    #Initialize logger
    setup_logging()
    logger = logging.getLogger(__name__)

    # Page title
    TABLE = 'Respiratory_Support'
    st.title(f"Respiratory Support Quality Check")

    logger.info(f"!!! Starting QC for {TABLE}.")

    # Main 
    qc_summary = []
    qc_recommendations = []

    if 'root_location' in st.session_state and 'filetype' in st.session_state:
        root_location = st.session_state['root_location']
        filetype = st.session_state['filetype']
        filepath = os.path.join(root_location, f'clif_respiratory_support.{filetype}')

        logger.info(f"Filepath set to {filepath}")

        if os.path.exists(filepath):
            progress_bar = st.progress(0, text="Quality check in progress. Please wait...")
            logger.info(f"File {filepath} exists.")

            # Start time
            start_time = time.time()

            progress_bar.progress(5, text='File found...')

            progress_bar.progress(10, text='Starting QC...')

            # 1. Respiratory Support Detailed QC 
            with st.expander("Expand to view", expanded=False):
                    # Load the file
                with st.spinner("Loading data..."):
                    progress_bar.progress(15, text='Loading data...')
                    logger.info("~~~ Loading data ~~~")
                    data = read_data(filepath, filetype)
                    df = data.copy()
                    logger.info("Data loaded successfully.")

                    
                # Display the data
                logger.info("~~~ Displaying data ~~~")
                st.write(f"## Respiratory Support Data Preview")
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
                    logger.info("Displayed data.")


                # Validate and convert data types
                st.write("## Data Type Validation")
                with st.spinner("Validating data types..."):
                    progress_bar.progress(30, text='Validating data types...')
                    logger.info("~~~ Validating data types ~~~")
                    data, validation_results = validate_and_convert_dtypes(TABLE, data)
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
                            'Missing Percentage': missing_percentages.map('{:.2f}%'.format)
                        })
                        missing_info_sorted = missing_info.sort_values(by='Missing Count', ascending=False)
                        st.write(missing_info_sorted)
                        qc_summary.append("Missing values found in columns - " + ', '.join(missing_info[missing_info['Missing Count'] > 0].index.tolist()))
                    else:
                        st.write("No missing values found in all required columns.")
                    logger.info("Checked for missing values.")


                # Display summary statistics
                st.write(f"## Respiratory Support Summary Statistics")
                with st.spinner("Displaying summary statistics..."):  
                    progress_bar.progress(50, text='Displaying summary statistics...')
                    logger.info("~~~ Displaying summary statistics ~~~")  
                    summary = data.describe()
                    st.write(summary)
                    logger.info("Displayed summary statistics.")

                
                # Check for required columns
                logger.info("~~~ Checking for required columns ~~~")    
                st.write(f"## Respiratory Support Required Columns")
                with st.spinner("Checking for required columns..."):
                    progress_bar.progress(60, text='Checking for required columns...')
                    required_cols_check = check_required_variables(TABLE, data)
                    st.write(required_cols_check)
                    qc_summary.append(required_cols_check)
                    if required_cols_check != f"All required columns present for '{TABLE}'.":
                        qc_recommendations.append("Some required columns are missing. Please ensure all required columns are present.")  
                        logger.warning("Some required columns are missing.")
                    logger.info("Checked for required columns.")

                # Check for outliers
                st.write("## Outliers")
                with st.spinner("Checking for outliers..."):
                    resp_outlier_thresholds_filepath = "thresholds/nejm_outlier_thresholds_respiratory_support.csv"
                    resp_outlier_thresholds = read_data(resp_outlier_thresholds_filepath, 'csv')
                    data, replaced_count, _, _ = replace_outliers_with_na_wide(data, resp_outlier_thresholds)
                    if replaced_count > 0:
                        qc_summary.append("Outliers found in the data.")
                        qc_recommendations.append("Outliers found. Please replace values with NA.")
                        st.write("Outliers found in the data.")

                st.write("## Device Category Summaries")
                st.write("###### * With Outliers")
                with st.spinner("Displaying summaries by device category..."):
                    st.info("The page will reload to display the summaries by device category. Please wait for the page to reload.")
                    progress_bar.progress(70, text='Displaying summaries by device category...')
                    logger.info("~~~ Diplaying summaries by device category ~~~")
                    categories = data['device_category'].dropna().unique()
                    categories.sort()
                    with st.form(key='device_mode_category_form'):
                        selected_category = st.selectbox('Select Device Category:', options = categories)
                        opt_mode_category = st.radio("Would you like to choose a mode category for the selected device category?", ['No', 'Yes'], horizontal=True, captions=['Ignore next dropdown if No', 'Select mode category below'])
                        modes = data['mode_category'].dropna().unique()
                        modes.sort()
                        selected_mode = st.selectbox('Select Mode Category:', options = modes)
                        st.session_state['selected_category'] = selected_category
                        st.session_state['selected_mode'] = selected_mode
                        submit_mode_opt = st.form_submit_button(label='Submit')
                        if submit_mode_opt and opt_mode_category == 'Yes':
                            filtered_df = df[(df['device_category'] == st.session_state['selected_category']) & (df['mode_category'] == st.session_state['selected_mode'])]
                            if filtered_df.empty:
                                st.warning(f"No data found for device category '{st.session_state['selected_category']}' and mode category '{st.session_state['selected_mode']}'.")
                            else:
                                st.write(f"### 1. Histograms for {st.session_state['selected_category']} with Mode Category {st.session_state['selected_mode']}")
                                cat_plot = plot_histograms_by_device_category(df, st.session_state['selected_category'], st.session_state['selected_mode'])
                                st.pyplot(cat_plot)

                                st.write(f"### 2. Summary for {st.session_state['selected_category']} with Mode Category {st.session_state['selected_mode']}")
                                cat_data = df[(df['device_category'] == st.session_state['selected_category']) & (df['mode_category'] == st.session_state['selected_mode'])]
                                cat_summary = cat_data.describe()
                                st.write(cat_summary)

                                i = 3
                                device_cat_count = cat_data.groupby(['device_category', 'device_name']).size().reset_index(name='count')
                                sorted_dev = device_cat_count.sort_values(by=['device_category', 'device_name'], ascending=[True, True])
                                if not sorted_dev.empty:
                                    st.write(f"### {i}. Device Name to Device Category Mapping for {st.session_state['selected_category']}")
                                    st.write(sorted_dev)
                                    i += 1

                                # st.write(f"### {i}. Mode Name to Mode Category Mapping for {st.session_state['selected_category']}")
                                mode_cat_count = cat_data.groupby(['mode_category', 'mode_name']).size().reset_index(name='count')
                                sorted_mode = mode_cat_count.sort_values(by=['mode_category', 'mode_name'], ascending=[True, True])
                                if not sorted_mode.empty:
                                    st.write(f"### {i}. Mode Name to Mode Category Mapping for {st.session_state['selected_category']}")

                                    st.write(sorted_mode)
                                    i += 1

                                encounters_w_vent = df.loc[df['device_category'] == 'IMV', 'hospitalization_id'].unique()
                                vent_resp_tables = df[df['hospitalization_id'].isin(encounters_w_vent)]
                                vent_resp_tables['min_time'] = vent_resp_tables.groupby('hospitalization_id')['recorded_dttm'].transform('min')
                                vent_resp_tables['time'] = (vent_resp_tables['recorded_dttm'] - vent_resp_tables['min_time']).dt.total_seconds() / 3600
                                vent_resp_tables = vent_resp_tables.drop(columns=['recorded_dttm', 'min_time'])
                                
                                if st.session_state['selected_category'] == 'IMV':
                                    st.write(f"#### {i}. Initial Mode Choice for Mechanical Ventilation")
                                    initial_mode_choice = (
                                    vent_resp_tables
                                    .dropna(subset=['mode_category'])  
                                    .groupby('hospitalization_id')           
                                    .apply(lambda x: x.iloc[0])                    
                                    .groupby('mode_category')          
                                    .size()
                                    .rename('count')                            
                                    )
                                    st.write(initial_mode_choice)
                        if submit_mode_opt and opt_mode_category == 'No':
                            filtered_df = df[df['device_category'] == st.session_state['selected_category']]
                            if filtered_df.empty:
                                st.warning(f"No data found for device category '{st.session_state['selected_category']}'.")
                            else:
                                st.write(f"### 1. Histograms for {st.session_state['selected_category']}")
                                cat_plot = plot_histograms_by_device_category(data, st.session_state['selected_category'])
                                st.pyplot(cat_plot)

                                st.write(f"### 2. Summary for {st.session_state['selected_category']}")
                                cat_data = df[df['device_category'] == st.session_state['selected_category']]
                                cat_summary = cat_data.describe()
                                st.write(cat_summary)

                                i = 3
                                device_cat_count = cat_data.groupby(['device_category', 'device_name']).size().reset_index(name='count')
                                # filtered_dev = device_cat_count[device_cat_count['count'] > 100]
                                sorted_dev = device_cat_count.sort_values(by=['device_category', 'device_name'], ascending=[True, True])
                                if not sorted_dev.empty:
                                    st.write(f"### {i}. Device Name to Device Category Mapping for {st.session_state['selected_category']}")
                                    # st.write("*for counts > 100")
                                    st.write(sorted_dev)
                                    i += 1

                                mode_cat_count = cat_data.groupby(['mode_category', 'mode_name']).size().reset_index(name='count')
                                # filtered_mode = mode_cat_count[mode_cat_count['count'] > 100]
                                sorted_mode = mode_cat_count.sort_values(by=['mode_category', 'mode_name'], ascending=[True, True])
                                if not sorted_mode.empty:
                                    st.write(f"### {i}. Mode Name to Mode Category Mapping for {st.session_state['selected_category']}")
                                    # st.write("*for counts > 100")
                                    st.write(sorted_mode)
                                    i += 1

                                encounters_w_vent = df.loc[df['device_category'] == 'IMV', 'hospitalization_id'].unique()
                                vent_resp_tables = df[df['hospitalization_id'].isin(encounters_w_vent)]
                                vent_resp_tables['min_time'] = vent_resp_tables.groupby('hospitalization_id')['recorded_dttm'].transform('min')
                                vent_resp_tables['time'] = (vent_resp_tables['recorded_dttm'] - vent_resp_tables['min_time']).dt.total_seconds() / 3600
                                vent_resp_tables = vent_resp_tables.drop(columns=['recorded_dttm', 'min_time'])
                                
                                if st.session_state['selected_category'] == 'IMV':
                                    st.write(f"#### {i}. Initial Mode Choice for Mechanical Ventilation")
                                    initial_mode_choice = (
                                    vent_resp_tables
                                    .dropna(subset=['mode_category'])  
                                    .groupby('hospitalization_id')           
                                    .apply(lambda x: x.iloc[0])                    
                                    .groupby('mode_category')          
                                    .size()
                                    .rename('count')                            
                                    )
                                    st.write(initial_mode_choice)
                
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




