import pandas as pd 
import requests 
import os 
from bs4 import BeautifulSoup
import re 
import time 

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

end_year = 2023
delay = 4