import time
from selenium import webdriver

driver = webdriver.Chrome()
driver.get('https://getsubs.cc/https://vt.tiktok.com/ZSAT3mVPu')
time.sleep(5)
search_box = driver.find_element_by_name('q')
search_box.send_keys('ChromeDriver')
search_box.submit()
time.sleep(5)
driver.quit()