import argparse
import sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from model.Network import Network


class Ads:


    # Location IDs are listed here:
    # https://developers.google.com/google-ads/api/reference/data/geotargets
    # and they can also be retrieved using the GeoTargetConstantService as shown
    # here: https://developers.google.com/google-ads/api/docs/targeting/location-targeting
    __DEFAULT_LOCATION_IDS = None
    # A language criterion ID. For example, specify 1000 for English. For more
    # information on determining this value, see the below link:
    # https://developers.google.com/google-ads/api/reference/data/codes-formats#expandable-7
    __DEFAULT_LANGUAGE_ID = None

    __CREDENTIALS_PATH = "auth/credentials.yaml"

    __CUSTOMER_ID = "hidden" # Test MCC Account

    __googleads_client = None

    # default location ID for New York
    # default language ID for English
    def __init__(self, location_ids = ["1023191"], language_id = "1000"):
        self.__googleads_client = GoogleAdsClient.load_from_storage(self.__CREDENTIALS_PATH)
        self.__DEFAULT_LOCATION_IDS = location_ids
        self.__DEFAULT_LANGUAGE_ID = language_id
        network = Network()
        self.__CUSTOMER_ID = network.getTestMCCID()


    def __map_locations_ids_to_resource_names(self, client, location_ids):
        build_resource_name = client.get_service(
            "GeoTargetConstantService"
        ).geo_target_constant_path
        return [build_resource_name(location_id) for location_id in location_ids]


    def run(self, keywords):

        try:

            keyword_plan_idea_service = self.__googleads_client.get_service("KeywordPlanIdeaService")
            keyword_plan_network = self.__googleads_client.get_type(
                "KeywordPlanNetworkEnum"
            ).KeywordPlanNetwork.GOOGLE_SEARCH_AND_PARTNERS
            location_rns = self.__map_locations_ids_to_resource_names(self.__googleads_client, self.__DEFAULT_LOCATION_IDS)
            language_rn = self.__googleads_client.get_service(
                "LanguageConstantService"
            ).language_constant_path(self.__DEFAULT_LANGUAGE_ID)


            request = self.__googleads_client.get_type("GenerateKeywordIdeasRequest")
            request.customer_id = self.__CUSTOMER_ID
            request.language = language_rn
            request.geo_target_constants = location_rns
            request.include_adult_keywords = False
            request.keyword_plan_network = keyword_plan_network
            request.keyword_seed.keywords.extend(keywords)


            keyword_ideas = keyword_plan_idea_service.generate_keyword_ideas(
                request=request
            )


            list_keywords = []
            for idea in keyword_ideas:
                competition_value = idea.keyword_idea_metrics.competition.name
                avg_monthly_searches = idea.keyword_idea_metrics.avg_monthly_searches
                text = idea.text
                list_keywords.append(idea)


            main_kw = list_keywords[0]
            del list_keywords[0]
            list_keywords = sorted(list_keywords, key=lambda x: int(x.keyword_idea_metrics.avg_monthly_searches), reverse=True)
            all_with_main_kw = [main_kw] + list_keywords
            return all_with_main_kw



        except GoogleAdsException as ex:
            print(
                f'Request with ID "{ex.request_id}" failed with status '
                f'"{ex.error.code().name}" and includes the following errors:'
            )
            print(f'\tError with message "{error.message}".')
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    print(f"\t\tOn field: {field_path_element.field_name}")
            return
