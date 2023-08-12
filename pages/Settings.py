import streamlit as st
import pandas as pd


st.set_page_config(
    page_title='SWBSA | Settings',
    page_icon='⚙️'
)


st.caption('SOUTH WALTON BEACH SERVICE ASSOCIATION')
st.title('Settings')
st.info('Make adjustments to: members, beach accesses, and rates.')


st.header('Members')
members = st.data_editor(data=pd.read_csv('settings/members.csv',index_col=False),num_rows='dynamic',use_container_width=True)
if st.button('Save Member Changes',use_container_width=True):
    members.to_csv('settings/members.csv', index=False)
    st.experimental_rerun()

st.write('&nbsp;')

st.header('Beach Accesses')
accesses = st.data_editor(data=pd.read_csv('settings/accesses.csv',index_col=False),num_rows='dynamic',use_container_width=True)
if st.button('Save Beach Access Changes',use_container_width=True):
    accesses.to_csv('settings/accesses.csv', index=False)
    st.experimental_rerun()

st.write('&nbsp;')

st.header('Rates')
rates = st.data_editor(data=pd.read_csv('settings/rates.csv',index_col=False),num_rows='dynamic',use_container_width=True)
if st.button('Save Rate Changes',use_container_width=True):
    rates.to_csv('settings/rates.csv', index=False)
    st.experimental_rerun()