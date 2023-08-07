import streamlit as st
import pandas as pd
import numpy as np

from io import StringIO
from io import BytesIO
from zipfile import ZipFile
from streamlit.components.v1 import html


st.set_page_config(
    page_title='SWBSA | Billing Engine',
    page_icon='🏖️'
)


with st.sidebar:
    st.subheader('Helpful links')
    st.write('[PDF Invoice Generator](https://docs.google.com/spreadsheets/d/1CfQOeo0zu0CzKz82enqDYb5Q8nZqKWjUQce5Lv1us3s/edit?usp=sharing)')
    st.write('[Vendor Change Requests](https://docs.google.com/spreadsheets/d/1x3WQ4YGpgHL2lCgy2x6RIBA2G9dgRH0DswLMoaqysbQ/edit?usp=sharing)')
    st.write('[Vendor Submissions](https://swbsa-rental.integrasoft.net/Login.aspx)')
    st.write('[Walkup Orders](https://manage.beachyapp.com/login/)')


st.caption('SOUTH WALTON BEACH SERVICE ASSOSICATION')
st.title('Billing Engine')
st.info('A tool to calculate monthly metrics and invoices.')
st.warning('It is recommended to wait until a month has concluded before billing on it.')

st.divider()

firstDayofPriorMonth = (pd.to_datetime('today') - pd.Timedelta(days=32)).replace(day=1)
lastDayofPriorMonth =pd.to_datetime('today').replace(day=1) - pd.Timedelta(days=1)

st.header('Billing Period')
left, right = st.columns(2)
start = left.date_input('Start of period',firstDayofPriorMonth)
end = right.date_input('End of period',lastDayofPriorMonth)

start = pd.to_datetime(start)
end = pd.to_datetime(end)

st.divider()

st.header('Required Reports')
st.write('Rentals by Day')
with st.expander('How to pull the report'):
    st.write('[integraRental | Vendor Submissions](https://swbsa-rental.integrasoft.net/Login.aspx)')
    st.info('Pull from January 1 through December 31.')
    st.video('https://youtu.be/2BMCv0ygLbg')

st.write('Items Sold by Boardwalk')
with st.expander('How to pull the report'):
    st.write('[Beachy | Walkup Orders](https://manage.beachyapp.com/login/)')
    st.info('Pull for the same dates as the billing period.')
    st.video('https://youtu.be/9_ThbDwzceo')

left, right = st.columns(2)
file_rentalsByDay = left.file_uploader('Export_ExportRentalsByDay.csv | integraRental','csv')
if file_rentalsByDay is not None:
    data_rentalsByDay = pd.read_csv(file_rentalsByDay, index_col=False)

file_itemsSoldByBoardwalk = right.file_uploader('Items Sold by Boardwalk.csv | Beachy','csv')
if file_itemsSoldByBoardwalk is not None:
    data_itemsSoldByBoardwalk = pd.read_csv(file_itemsSoldByBoardwalk, index_col=False)


if (file_rentalsByDay != None and file_itemsSoldByBoardwalk != None):

    st.divider()
    st.header('Billing Metrics')

    st.write(start.date(), ' - ', end.date())

    rbd         = data_rentalsByDay
    rbd.columns = ['description','order','access','comment','quantity','remove','customer','vendor','agent_name','agent_email','start','end','duration','set_days']
    rbd         = rbd.drop(columns=['remove'])
    rbd.start   = pd.to_datetime(rbd.start).dt.normalize()
    rbd.end     = pd.to_datetime(rbd.end).dt.normalize()

    rbd = rbd[
        ((rbd.start >= start) & (rbd.start <= end)) |
        ((rbd.end >= start) & (rbd.end <= end)) |
        ((rbd.start < start) & (rbd.end > end))
    ]

    def AdjustDateToPeriodStart(date):
        if date < start: return start
        else: return date
    
    def AdjustDateToPeriodEnd(date):
        if date > end: return end
        else: return date

    rbd.start    = rbd.start.apply(AdjustDateToPeriodStart)
    rbd.end      = rbd.end.apply(AdjustDateToPeriodEnd)
    rbd.duration = (rbd.end - rbd.start).dt.days + 1
    rbd.set_days = rbd.quantity * rbd.duration

    ba = pd.read_csv('settings/accesses.csv', index_col=False)
    me = pd.read_csv('settings/members.csv',  index_col=False)
    ra = pd.read_csv('settings/rates.csv',    index_col=False)

    bill = rbd.pivot_table(values='set_days',index='vendor',aggfunc=np.sum)
    bill = bill.merge(me, left_on='vendor', right_on='vendor', how='left')
    bill.columns = ['vendor','set_days','vendor_email','isTaxExempt']
    bill['cost'] = bill.set_days * ra.cost_per_set[0]
    bill['cost_per_set'] = ra.cost_per_set[0]

    def GetTax(isTaxExempt, cost):
        if isTaxExempt == True: return 0
        else: return cost * ra.tax_rate[0]

    bill['tax']  = bill.apply(lambda row: GetTax(row.isTaxExempt,row.cost), axis=1)
    bill['total'] = bill.cost + bill.tax

    bill = bill[['vendor','vendor_email','set_days','cost_per_set','cost','isTaxExempt','tax','total']]

    vendors = bill.vendor.unique()

    isbb = data_itemsSoldByBoardwalk
    isbb.columns = ['remove 1','access','remove 2','asset','quantity']
    isbb = isbb.drop(columns=['remove 1', 'remove 2'])
    isbb = isbb[(isbb.asset == 'Beach Set') | (isbb.asset == 'Beach Umbrella')]

    isbb_pivot = isbb.pivot_table(values='quantity',index='access',aggfunc=np.sum)
    rbd_pivot = rbd.pivot_table(values='set_days',index='access',aggfunc=np.sum)

    mvp = pd.merge(ba,rbd_pivot,how='left',left_on='integraRental',right_on='access')
    mvp = pd.merge(mvp, isbb_pivot,how='left',left_on='beachy',right_on='access')
    mvp = mvp.drop(columns='beachy')
    mvp.columns = ['access','sets_orders','sets_walkups']
    mvp['county_orders'] = mvp.sets_orders * ra.county_fee_per_set[0]
    mvp['county_walkups'] = mvp.sets_walkups * ra.county_fee_per_set[0]
    mvp = mvp.fillna(0)
    mvp = mvp[['access','sets_orders','county_orders','sets_walkups','county_walkups']]
    mvp_accesses = mvp


    mvp_due = pd.DataFrame()
    mvp_due['type']   = ['orders','walkups']
    mvp_due['sets']   = [np.sum(mvp.sets_orders),np.sum(mvp.sets_walkups)]
    mvp_due['county'] = [np.sum(mvp.county_orders),np.sum(mvp.county_walkups)]


    def GetVendorPercentage(sets):
        return round(sets / np.sum(mvp_accesses.sets_orders) * 100, 2)
    
    mvp_vendors = rbd.pivot_table(values='set_days',index='vendor',aggfunc=np.sum)
    mvp_vendors['month'] = start.month_name()
    mvp_vendors['percentage'] = mvp_vendors.set_days.apply(lambda x: GetVendorPercentage(x))
    mvp_vendors = mvp_vendors.drop(columns='set_days')

    left, middle, right = st.columns(3) 
    left.metric('Vendors', round(len(vendors)))
    middle.metric('Beaches', round(mvp_accesses.access.nunique()))
    right.metric('Due from Vendors', round(np.sum(bill.total),2))

    left, middle, right = st.columns(3) 
    left.metric('Vendor Sets', round(np.sum(mvp.sets_orders)))
    middle.metric('Walkup Sets', round(np.sum(mvp.sets_walkups)))
    right.metric('Due to County', round(np.sum(mvp_due.county)))

    st.write('#')

    primer = pd.merge(rbd,me,'left',on='vendor')
    primer['cost_per_set'] = ra.cost_per_set[0]
    primer['tax_rate']     = ra.tax_rate[0]


    with st.container():
        left, right = st.columns(2)
        left.download_button('Download Billing Summary',bill.to_csv(index=False),'billing_summary.csv',use_container_width=True,)
        right.caption('Summary of Due from Vendors')

    with st.container():
        left, right = st.columns(2)
        left.download_button('Download MVP Report','','mvp_report.csv',use_container_width=True)
        right.caption('[Under Dev] Summary of Due to County')

    with st.container():
        left, right = st.columns(2)
        left.download_button('Download Invoice Primer',primer.to_csv(index=False),'invoices_primer.csv',use_container_width=True)
        right.caption('Data for PDF Invoice Generator')

        with st.expander('How to use the Invoice Primer'):
            st.write('[PDF Invoice Generator](https://docs.google.com/spreadsheets/d/1CfQOeo0zu0CzKz82enqDYb5Q8nZqKWjUQce5Lv1us3s/edit?usp=sharing)')
            st.video('https://youtu.be/xgDyIc86YFo')
    
    # st.download_button('Download MVP Accesses',mvp_accesses.to_csv(index=False),'mvp_accesses.csv',use_container_width=True)
    # st.download_button('Download MVP Vendors',mvp_vendors.to_csv(),'mvp_vendors.csv',use_container_width=True)
    # st.download_button('Download MVP Due',mvp_due.to_csv(index=False),'mvp_due.csv',use_container_width=True)

    st.divider()

    st.header('Invoice Previews')

    csv_io = BytesIO()
    with ZipFile(csv_io,'w') as zip:
        for vendor in vendors:
            file = vendor.replace('/','_')
            sio  = StringIO()
            df   = rbd[rbd.vendor == vendor].to_csv(sio, index=False)
            zip.writestr(file + '.csv', sio.getvalue())

    st.download_button('Download Invoice CSVs',csv_io,'invoices_csv.zip',use_container_width=True)

    for vendor in vendors:
        st.write('#')
        st.subheader(vendor)
        st.dataframe(rbd[rbd.vendor == vendor],use_container_width=True)
        st.download_button('Download ' + vendor + '.csv',rbd[rbd.vendor == vendor].to_csv(index=False),vendor+'.csv',use_container_width=True)