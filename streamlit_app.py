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
from google_auth_oauthlib.flow import Flow


network = Network()
st.set_page_config(layout="wide")


scopes = ["https://www.googleapis.com/auth/adwords"]

secrets = {"installed":{"client_id":st.secrets["client_id"],"project_id":st.secrets["project_id"],"auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":st.secrets["client_secret"],"redirect_uris":["urn:ietf:wg:oauth:2.0:oob","http://localhost"]}}

flow = Flow.from_client_config(
    secrets, scopes=scopes, redirect_uri='urn:ietf:wg:oauth:2.0:oob'
)

auth_url, _ = flow.authorization_url(prompt='consent')

st.text('Please go to this URL if the token is expired:\n{}'.format(auth_url))

authorization_code = st.text_input('Enter the authorization code: ')

st.text(authorization_code)


enter_auth_code = st.button("Refresh Token")

if enter_auth_code:

    token = flow.fetch_token(code=authorization_code)
    
    refresh_token = token["refresh_token"]

    st.text("Refresh token: {}".format(str(refresh_token)))
    st.text("Refreshing token ...")
    
    network.setRefreshTokenForGoogleAdsAPI(refresh_token)

    st.text("Token has been refreshed!")



refresh_token = network.getRefreshTokenForGoogleAdsAPI()
client_secret = network.getClienSecret()
client_id = network.getClientID()
developer_token = network.getDeveloperToken()
login_customer_id = network.getLoginCustomerID()
Helpers.updateCredentials(refresh_token, client_secret, client_id, developer_token, login_customer_id)
__KEYWORD_LIMIT = network.getKeywordLimit()



st.title("The Keyword Research Automator:snake::fire:")
text = st.text_area("Input your search term (one per line, max {}) and hit Get Keywords to get all the most relevant keywords for each search term. Once the report is ready, hit Download Results to get all related keywords by term in one excel with different tabs ⬇️".format(str(__KEYWORD_LIMIT)), height=150, key=1)


lines = text.split("\n")  # A list of lines
keywords = Helpers.removeRestrictedCharactersAndWhiteSpaces(lines)

st.text('You have {} KWs out of the max {} KWs'.format(str(len(keywords)), str(__KEYWORD_LIMIT)))

data_parser = DataParser() 
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
        
        
        saved_time = 0

        for i in stqdm(range(len(keywords))):

            keyword = keywords[i]
            
            current_time = time.time()
            diff_time = current_time - saved_time
            sleep_time = 1 - diff_time
            if sleep_time > 0:
                time.sleep(sleep_time) #API Limitations https://developers.google.com/google-ads/api/docs/best-practices/quotas
            saved_time = time.time()
            
            geo_identifier = ""	
            if "-" in keyword:	
                splitted = keyword.split("-")	
                keyword = [splitted[0]]	
                geo_identifier_text = splitted[1]	
                	
                if geo_identifier_text == "UK":	
                    geo_identifier_text = "GB"	
                	
                loc_id = data_parser.get_location_id_by_code(geo_identifier_text)	
                	
                if loc_id is None:	
                    st.warning(geo_identifier_text + " does not exist.")	
                    continue	
                        	
                ads = Ads(location_ids = [loc_id], language_id = language_id)	
                	
            else:	
                	
                keyword = [keyword]	
                	
                for e in location_ids:	
                    loc_code = data_parser.get_code_by_location_id(e)	
                    geo_identifier += loc_code + "-"	
                geo_identifier_text = geo_identifier[:-1]	
                ads = Ads(location_ids = location_ids, language_id = language_id)

                
            try:

                ideas = ads.run(keyword)

                row = []
                
                
                if len(ideas) > 1:

                    for j in range(len(ideas)):
                        
                        if geo_identifier_text == "GB":	
                            geo_identifier_text = "UK"	
                            

                        try:
                            len_of_row = int(len(rows[j]))
                            num_of_nones = 3*i - len_of_row
                            none_list = [None]*num_of_nones
                            
                            #DEBUG
                            print("ideas[j].text: {}, ideas[j].keyword_idea_metrics.avg_monthly_searches: {}, geo_identifier_text: {}".format(str(len(ideas[j].text)), str(len(ideas[j].keyword_idea_metrics.avg_monthly_searches)), str(len(geo_identifier_text))))
                            #DEBUG
                            
                            
                            rows[j] += none_list + [geo_identifier_text, ideas[j].text, ideas[j].keyword_idea_metrics.avg_monthly_searches]
                            
                            
                        except IndexError:
                            num_of_nones = 3*i
                            none_list = [None]*num_of_nones
                            
                            #DEBUG
                            print("ideas[j].text: {}, ideas[j].keyword_idea_metrics.avg_monthly_searches: {}, geo_identifier_text: {}".format(str(len(ideas[j].text)), str(len(ideas[j].keyword_idea_metrics.avg_monthly_searches)), str(len(geo_identifier_text))))
                            #DEBUG
                            
                            
                            row = none_list + [geo_identifier_text, ideas[j].text, ideas[j].keyword_idea_metrics.avg_monthly_searches]
                            rows.append(row)
                else:
                    none_keywords.append(keyword[0])

                #columns += ["Location", "Keyword", "Avg. Monthly Searches"]

            except Exception as e:
                pass
                #st.warning("Error: {}".format(e))
            finally:
                columns += ["Location", "Keyword", "Avg. Monthly Searches"]
                


        #if not error_flag:

        dataframe = pd.DataFrame(rows, columns = columns)

        st.write(dataframe) #Table creation
        
        
        rows_all = []
        for row in rows:
            rows_all += row
        rows_all_edited = []
        for i in range(0, len(rows_all), 3):
            rows_all_edited.append([rows_all[i], rows_all[i+1], rows_all[i+2]])
            
        rows_all = sorted(rows_all_edited, key=lambda x: x[2] if x[2] is not None else 0, reverse=True)
        dataframe_all = pd.DataFrame(rows_all, columns = ["Location", "Keyword", "Avg. Monthly Searches"])
        dataframe_all.drop_duplicates(subset = ["Location", "Keyword", "Avg. Monthly Searches"], keep = 'first', inplace = True)

        towrite = io.BytesIO()
        writer = pd.ExcelWriter(towrite, engine='xlsxwriter')

        downloaded_file = dataframe_all.to_excel(writer, sheet_name="All Keywords", encoding='utf-8', header=True, index=False)

        for i in range(0, (len(columns))//3):
            current_row = [[e[3*i], e[3*i+1], e[3*i+2]] for e in rows if len(e) >= 3*i+3]
            dataframe = pd.DataFrame(current_row, columns = columns[:3])
            try:
                downloaded_file = dataframe.to_excel(writer, sheet_name=current_row[0][0][:31], encoding='utf-8', header=True, index=False)
            except:
                downloaded_file = dataframe.to_excel(writer, sheet_name=none_keywords[none_keyword_counter][:31], encoding='utf-8', header=True, index=False)
                none_keyword_counter+=1


        writer.save()
        towrite.seek(0)  # reset pointer
        b64 = base64.b64encode(towrite.read()).decode()  # some strings
        custom_css, button_id = DownloadButtonView.getCustomCSS()
        linko = custom_css + f'<a id="{button_id}" href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="results.xlsx">Download KWs Excel</a>'

        st.markdown(linko, unsafe_allow_html=True)

        st.write("#")
