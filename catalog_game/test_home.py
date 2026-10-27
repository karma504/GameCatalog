import pytest
import pytest_check as check
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_URL = 'http://127.0.0.1:8000/'
CATALOG_URL = BASE_URL + 'games/'
SITE_NAME = 'хмарна полиця'
SEARCH_QUERY = 'Minecraft'
SEARCH_INPUT = "input[name='q'], input[type='search']"



@pytest.fixture
def driver():

    browser = webdriver.Chrome()
    browser.maximize_window()
    yield browser

    browser.quit()


def test_home_page(driver):

    wait = WebDriverWait(driver, 10)

    driver.get(BASE_URL)
    heading = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'h1'))
    )

    assert heading.is_displayed()
    assert SITE_NAME in driver.page_source.lower()

    check.is_true(heading.text.strip() != '')
    check.is_in('127.0.0.1:8000', driver.current_url)
    check.is_in(SITE_NAME, driver.title.lower())


def test_search_game(driver):
    wait = WebDriverWait(driver, 10)

    driver.get(CATALOG_URL)
    search_field = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, SEARCH_INPUT))
    )
    search_field.clear()
    search_field.send_keys(SEARCH_QUERY)
    search_field.send_keys(Keys.ENTER)

    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             f"//*[self::a or self::h2 or self::h3 or self::h4]"
             f"[contains(normalize-space(.), '{SEARCH_QUERY}')]")
        )
    )

    assert SEARCH_QUERY in driver.page_source

    check.is_in('q=', driver.current_url)
    check.is_true(len(driver.find_elements(
        By.XPATH, f"//a[contains(normalize-space(.), '{SEARCH_QUERY}')]"
    )) > 0)

if __name__ == '__main__':
    test_search_game(BASE_URL)
    test_home_page(BASE_URL)


