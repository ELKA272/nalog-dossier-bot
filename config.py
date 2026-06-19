import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OMNI_ROUTE_API_KEY = os.getenv("OMNI_ROUTE_API_KEY", "")
FSSP_API_KEY = os.getenv("FSSP_API_KEY", "")
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", "")
PARSER_FSSP_BASE_URL = os.getenv("PARSER_FSSP_BASE_URL", "https://parser-api.com/parser/fssp_api")
PARSER_API_KEY = os.getenv("PARSER_API_KEY", "d117c8b0e4d8bd9cb9f80dcfc612cd3d")

MODEL_ANALYST = "deepseek/deepseek-chat"
MODEL_WRITER = "deepseek/deepseek-chat"
OMNI_ROUTE_BASE_URL = "https://omni.route/v1"

FSSP_API_URL = "https://api.fssp.gov.ru/ip"
FNS_TRANSPARENT_URL = "https://pb.nalog.ru/api/search"
EGRUL_URL = "https://egrul.nalog.ru/"
ARBITR_URL = "https://kad.arbitr.ru/SearchInstances"
FEDRESURS_URL = "https://fedresurs.ru/api/companies"
RUSPROFILE_URL = "https://www.rusprofile.ru/search"
BANKRUPT_URL = "https://bankrot.fedresurs.ru/DebitorList.aspx"
DISQUAL_URL = "https://service.nalog.ru/disfind.do"
NDP_URL = "https://rnp.fas.gov.ru/"
INSPECTIONS_URL = "https://proverki.gov.ru/portal/public/inspection"

REQUEST_DELAY_MIN = 2.0
REQUEST_DELAY_MAX = 5.0
REQUEST_TIMEOUT = 30
CACHE_TTL = 86400
REPORTS_DIR = "data/reports"
CACHE_DIR = "data/cache"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
