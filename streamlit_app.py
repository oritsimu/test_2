import streamlit as st
import base64
import io
import pandas as pd
import xlsxwriter
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
import time
from stqdm import stqdm
from model.Ads import Ads
from model.Excel import Excel
from model.Helpers import Helpers
from model.DataParser import DataParser
from view.DownloadButtonView import DownloadButtonView
from model.Network import Network


network = Network()
refresh_token = network.getRefreshTokenForGoogleAdsAPI()
client_secret = network.getClienSecret()
client_id = network.getClientID()
developer_token = network.getDeveloperToken()
login_customer_id = network.getLoginCustomerID()
Helpers.updateCredentials(refresh_token, client_secret, client_id, developer_token, login_customer_id)
__KEYWORD_LIMIT = network.getKeywordLimit()


st.set_page_config(layout="wide")
st.title("The Keyword Research Automator:snake::fire:")
text = st.text_area("Input your search term (one per line, max {}) and hit Get Keywords to get all the most relevant keywords for each search term. Once the report is ready, hit Download Results to get all related keywords by term in one excel with different tabs ⬇️".format(str(__KEYWORD_LIMIT)), height=150, key=1)


lines = text.split("\n")  # A list of lines
keywords = Helpers.removeRestrictedCharactersAndWhiteSpaces(lines)


data_parser = DataParser() #TODO save lists as binary to speed up the process
parent_locations = data_parser.get_parent_locations()
languages = data_parser.get_languages()


selected_countries = st.multiselect('Country', parent_locations, default=["United States"])
selected_language = st.selectbox('Language', languages)


location_ids = data_parser.get_parent_location_ids(selected_countries)
language_id = data_parser.get_language_id(selected_language)


start_execution = st.button("Get Keywords! 🤘")


if start_execution:

    if len(keywords) == 0:

        st.warning("Please enter at least 1 keyword.")

    elif len(keywords) > __KEYWORD_LIMIT:

        st.warning("Please enter at most {} keywords.".format(str(__KEYWORD_LIMIT)))

    else:
        
        none_keywords = []
        none_keyword_counter = 0

        error_flag = False #If there is an unexpected error with the API, the rest of the code won't be processed and a warning message will appear.

        columns = []
        rows = []
        
        ads = Ads(location_ids = location_ids, language_id = language_id)
        
        saved_time = 0

        for i in stqdm(range(len(keywords))):

            keyword = [keywords[i]]
            
            current_time = time.time()
            diff_time = current_time - saved_time
            sleep_time = 1 - diff_time
            if sleep_time > 0:
                time.sleep(sleep_time) #API Limitations https://developers.google.com/google-ads/api/docs/best-practices/quotas
            saved_time = time.time()

            try:

                ideas = ads.run(keyword)

                row = []

                for j in range(len(ideas)):

                    try:
                        len_of_row = int(len(rows[j]))
                        num_of_nones = 2*i - len_of_row
                        none_list = [None]*num_of_nones
                        rows[j] += none_list + [ideas[j].text, ideas[j].keyword_idea_metrics.avg_monthly_searches]
                    except IndexError:
                        num_of_nones = 2*i
                        none_list = [None]*num_of_nones
                        row = none_list + [ideas[j].text, ideas[j].keyword_idea_metrics.avg_monthly_searches]
                        rows.append(row)

                #columns += ["Keyword", "Avg. Monthly Searches"]

            except Exception as e:
                pass
                #st.warning("Error: {}".format(e))
            finally:
                columns += ["Keyword", "Avg. Monthly Searches"]
                none_keywords.append(keyword[0])


        #if not error_flag:

        dataframe = pd.DataFrame(rows, columns = columns)

        st.write(dataframe) #Table creation
        
        
        rows_all = []
        for row in rows:
            rows_all += row
        st.warning("Rows all: {}".format(str(rows_all[:3])))
        rows_all = sorted(rows_all, key=lambda x: x[1], reverse=True)
        dataframe_all = pd.DataFrame(rows_all, columns = ["Keyword", "Avg. Monthly Searches"])
        

        towrite = io.BytesIO()
        writer = pd.ExcelWriter(towrite, engine='xlsxwriter')

        downloaded_file = dataframe_all.to_excel(writer, sheet_name="All Keywords", encoding='utf-8', header=True, index=False)

        for i in range(0, (len(columns))//2):
            current_row = [[e[2*i], e[2*i+1]] for e in rows if len(e) >= 2*i+2]
            dataframe = pd.DataFrame(current_row, columns = columns[:2])
            try:
                downloaded_file = dataframe.to_excel(writer, sheet_name=current_row[0][0], encoding='utf-8', header=True, index=False)
            except:
                downloaded_file = dataframe.to_excel(writer, sheet_name=none_keywords[none_keyword_counter], encoding='utf-8', header=True, index=False)
                none_keyword_counter+=1


        writer.save()
        towrite.seek(0)  # reset pointer
        b64 = base64.b64encode(towrite.read()).decode()  # some strings
        custom_css, button_id = DownloadButtonView.getCustomCSS()
        linko = custom_css + f'<a id="{button_id}" href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="results.xlsx">Download KWs Excel</a>'

        st.markdown(linko, unsafe_allow_html=True)

        st.write("#")
