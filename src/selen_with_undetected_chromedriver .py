import asyncio
import logging
import random
import re

import aiohttp
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

import undetected_chromedriver as uc

class Selen:
    drivers_list: dict = {}
    actions_list: dict = {}

    def __init__(self, user_list):
        """
        Создается драйвер для бота, который будет использоваться для проверки цен на товары, а также выполняется
        генерация драйверов под каждого добавленного пользователя после перезапуска бота.
        """
        self.service = Service(ChromeDriverManager().install())
        self.user_list = user_list
        self.create_drivers("wb")
        # self.create_drivers("ozon")
        self.create_drivers_ozon()

    def create_drivers_ozon(self):
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={UserAgent().random}")
        DRIVER = uc.Chrome(options=options)
        actions = ActionChains(DRIVER)
        self.drivers_list['ozon'] = DRIVER
        self.actions_list['ozon'] = actions

    def create_drivers(self, source: str):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={UserAgent().random}")
        service = self.service
        DRIVER = webdriver.Chrome(options=options, service=service)
        actions = ActionChains(DRIVER)
        self.drivers_list[source] = DRIVER
        self.actions_list[source] = actions

    # ============================================ OZON ====================================================================
    async def ozon_search_tovar(self, articul, user_id):
        """
        Функция поиска товаров. Вызывается отдельно каждым пользователем бота.
        Использует индивидуальный Driver каждого пользователя из drivers_list
        :param articul: артикул товара, который ищем
        :param user_id: идентификатор пользователя для выбора драйвера
        :return:
        """
        # Беру существующий драйвер, либо запускаю новый
        DRIVER = self.drivers_list.get(user_id)
        if DRIVER is None:
            # options = await self.get_options()
            # DRIVER = webdriver.Chrome(options=options, service=self.service)
            options = uc.ChromeOptions()
            # options.add_argument('--headless')
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-gpu")
            options.add_argument(f"user-agent={UserAgent().random}")
            DRIVER = uc.Chrome(options=options)
            self.drivers_list[user_id] = DRIVER

        url = f"https://www.ozon.ru/product/{articul}/?oos_search=false"
        product = {}
        try:
            DRIVER.get(url)
            # await asyncio.sleep(random.randint(1, 3))
        except Exception as e:
            logging.error(f"OZON: Исключение при открытии страницы: {e} --- {url}")
            return None

        # Ожидание загрузки страницы
        try:
            await asyncio.create_task(
                self.wait_fing_element(
                    DRIVER, 20, (By.CSS_SELECTOR, 'div[data-widget="stickyContainer"]')
                )
            )
        except Exception as e:
            logging.error(f"{e}")
            try:
                error_404 = WebDriverWait(DRIVER, 20).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@data-widget="error"]')
                    )
                )
                logging.error(
                    f"OZON: Ошибка при ожидании (stickyContainer) артикула {articul}. Он отсутствует на сайте."
                )
                await self.clear_driver(DRIVER=DRIVER)
                return None
            except Exception as e:
                logging.error(
                    f"ЧТО-ТО СТРАННОЕ OZON: Ошибка при ожидании (div[@data-widget='error']) артикула {articul}"
                )
                logging.error(f"{e}")
                await self.clear_driver(DRIVER=DRIVER)
                return None

        # НАИМЕНОВАНИЕ ТОВАРА
        name_element = DRIVER.find_element(
            By.CSS_SELECTOR, 'div[data-widget="webProductHeading"]'
        )
        product_title = name_element.text
        product["name"] = product_title

        # ИЗОБРАЖЕНИЕ
        gallery_element = await asyncio.create_task(
            self.wait_fing_element(
                DRIVER, 20, (By.CSS_SELECTOR, 'div[data-widget="webGallery"]')
            )
        )
        image_element = gallery_element.find_element(By.TAG_NAME, "img")
        image_url = image_element.get_attribute("src")
        product["img"] = await self.download_image(image_url)

        try:
            price_element = DRIVER.find_element(
                By.CSS_SELECTOR, 'div[data-widget="webOutOfStock"]'
            )
            price_card = False
        except:
            price_element = DRIVER.find_element(
                By.CSS_SELECTOR, 'div[data-widget="webPrice"]'
            )
            price = str(price_element.text)
            price = re.sub(r"[^a-zA-Zа-яА-Я0-9\s]+", "", price)
            price = re.findall(r"\d+[^\S\n]*\d*", price)
            price = [re.sub(r"[^\S\n]", "", num) for num in price]
            price_card = price[0]


        product["price"] = price_card
        await self.clear_driver(DRIVER=DRIVER)
        return product

    async def ozon_check_price(self, articul):
        """
        Функция обращения к WB и получения новой цены.
        :return:
        """
        DRIVER = self.drivers_list.get("ozon")
        url = f"https://www.ozon.ru/product/{articul}/?oos_search=false"
        try:
            DRIVER.get(url)
            # await asyncio.sleep(random.randint(1, 3))
        except Exception as e:
            logging.error(f"OZON: Исключение при открытии страницы: {e} --- {url}")
            return None

        # Ожидание загрузки страницы
        try:
            await asyncio.create_task(
                self.wait_fing_element(
                    DRIVER, 20, (By.CSS_SELECTOR, 'div[data-widget="stickyContainer"]')
                )
            )
        except Exception as e:
            logging.error(f'{e}')
            try:
                error_404 = WebDriverWait(DRIVER, 20).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@data-widget="error"]')
                    )
                )
                logging.error(
                    f"OZON: Ошибка при ожидании (stickyContainer) артикула {articul}. Он отсутствует на сайте."
                )
                DRIVER.delete_all_cookies()
                return None
            except Exception as e:
                logging.error(
                    f"ЧТО-ТО СТРАННОЕ OZON: Ошибка при ожидании (div[@data-widget='error']) артикула {articul}"
                )
                logging.error(f'{e}')
                DRIVER.delete_all_cookies()
                return None

        # ========== МАСКИРОВКА ===============
        await self.ozon_masking(DRIVER)

        # ОБРАБОТКА ЦЕННИКА
        try:
            price_element = DRIVER.find_element(
                By.CSS_SELECTOR, 'div[data-widget="webOutOfStock"]'
            )
            DRIVER.delete_all_cookies()
            return False
        except:
            price_element = DRIVER.find_element(
                By.CSS_SELECTOR, 'div[data-widget="webPrice"]'
            )
            price = str(price_element.text)
            price = re.sub(r"[^a-zA-Zа-яА-Я0-9\s]+", "", price)
            price = re.findall(r"\d+[^\S\n]*\d*", price)
            price = [re.sub(r"[^\S\n]", "", num) for num in price]
            price_card = price[0]
            DRIVER.delete_all_cookies()
            return int(price_card)
        # try:
        #     price_element = DRIVER.find_element(
        #         By.CSS_SELECTOR, 'div[data-widget="webPrice"]'
        #     )
        #     price = str(price_element.text)
        #     price = re.sub(r"[^a-zA-Zа-яА-Я0-9\s]+", "", price)
        #     price = re.findall(r"\d+[^\S\n]*\d*", price)
        #     price = [re.sub(r"[^\S\n]", "", num) for num in price]
        #     price_card = price[0]
        #     DRIVER.delete_all_cookies()
        #     return int(price_card)
        # except:
        #     DRIVER.delete_all_cookies()
        #     return False

    async def ozon_masking(self, DRIVER):
        # жду пока прогрузится контент
        await asyncio.create_task(
            self.wait_fing_element(
                DRIVER, 20, (By.CSS_SELECTOR, 'div[data-widget="stickyContainer"]')
            )
        )
        # получаю высоту страницы
        page_height = DRIVER.execute_script("return document.body.scrollHeight")
        BODY = await asyncio.create_task(
            self.wait_fing_element(DRIVER, 20, (By.XPATH, "//body"))
        )
        actions = self.actions_list.get("ozon")
        actions.move_to_element(BODY).perform()
        for _ in range(3):  # Выполняем 3 случайных скролла
            # Генерируем случайную позицию для скролла
            scroll_position = random.randint(0, page_height)
            # Выполняем скролл
            DRIVER.execute_script(f"window.scrollTo(0, {scroll_position});")
            # Задержка перед следующим действием
            await asyncio.sleep(random.uniform(2, 4))

    # ============================================ OZON ====================================================================
    async def wb_search_tovar(self, articul, user_id):
        """
        Функция поиска товаров. Вызывается отдельно каждым пользователем бота.
        Использует индивидуальный Driver каждого пользователя из drivers_list
        :param articul: артикул товара, который ищем
        :param user_id: идентификатор пользователя для выбора драйвера
        :return:
        """
        # Беру существующий драйвер, либо запускаю новый
        DRIVER = self.drivers_list.get(user_id)
        if DRIVER is None:
            options = await self.get_options()
            DRIVER = webdriver.Chrome(options=options, service=self.service)
            self.drivers_list[user_id] = DRIVER

        url = f"https://www.wildberries.ru/catalog/{articul}/detail.aspx"
        product = {}
        try:
            DRIVER.get(url)
            await asyncio.sleep(random.randint(1, 3))
        except Exception as e:
            logging.error(f"WB: Исключение при открытии страницы: {e} --- {url}")
            return None

        # Ожидание загрузки страницы
        try:
            await asyncio.create_task(
                self.wait_fing_element(
                    DRIVER,
                    20,
                    (
                        By.XPATH,
                        '//section[@class="product-page__details-section details-section"]',
                    ),
                )
            )
        except:
            error_404 = WebDriverWait(DRIVER, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h1[@class='content404__title']")
                )
            )
            await self.clear_driver(DRIVER=DRIVER)
            return None

        # НАИМЕНОВАНИЕ ТОВАРА
        name_element = DRIVER.find_element(
            By.CSS_SELECTOR, 'div[class="product-page__header"]'
        )
        product_title = name_element.text
        product["name"] = product_title.replace("\n", " ")

        # ИЗОБРАЖЕНИЕ
        image_element = await asyncio.create_task(
            self.wait_fing_element(
                DRIVER, 20, (By.CSS_SELECTOR, 'div[class="zoom-image-container')
            )
        )
        image = image_element.find_element(By.TAG_NAME, "img")
        image_url = image.get_attribute("src")
        product["img"] = await self.download_image(image_url)

        try:
            price_element = DRIVER.find_element(
                By.XPATH, ".//ins[@class='price-block__final-price']"
            )
            price = price_element.get_attribute("textContent")
            price = "".join(char for char in price if char.isdigit())
        except Exception as exc:
            sold_out_element = DRIVER.find_element(
                By.XPATH, ".//p[@class='sold-out-product']"
            )
            price = False

        product["price"] = price
        await self.clear_driver(DRIVER=DRIVER)
        return product

    async def wb_masking(self, DRIVER):
        # жду пока прогрузится контент
        await asyncio.create_task(
            self.wait_fing_element(
                DRIVER, 20, (By.XPATH, "//div[@class='product-page__header']")
            )
        )
        # получаю высоту страницы
        page_height = DRIVER.execute_script("return document.body.scrollHeight")
        BODY = await asyncio.create_task(
            self.wait_fing_element(DRIVER, 20, (By.XPATH, "//body"))
        )
        actions = self.actions_list.get("wb")
        actions.move_to_element(BODY).perform()
        for _ in range(3):  # Выполняем 3 случайных скролла
            # Генерируем случайную позицию для скролла
            scroll_position = random.randint(0, page_height)
            # Выполняем скролл
            DRIVER.execute_script(f"window.scrollTo(0, {scroll_position});")
            # Задержка перед следующим действием
            await asyncio.sleep(random.uniform(2, 4))

    async def wb_check_price(self, articul):
        """
        Функция обращения к WB и получения новой цены.
        :return:
        """
        DRIVER = self.drivers_list.get("wb")
        url = f"https://www.wildberries.ru/catalog/{articul}/detail.aspx"
        try:
            DRIVER.get(url)
            await asyncio.sleep(random.randint(1, 3))
        except Exception as e:
            logging.error(f"WB: Исключение при открытии страницы: {e} --- {url}")
            return None

        # Ожидание загрузки страницы
        try:
            await asyncio.create_task(
                self.wait_fing_element(
                    DRIVER,
                    20,
                    (
                        By.XPATH,
                        "//section[@class='product-page__details-section details-section']",
                    ),
                )
            )
        except:
            logging.error(
                f"WB: Ошибка при ожидании (product-page__details-section details-section) артикула {articul}"
            )
            try:
                error_404 = WebDriverWait(DRIVER, 20).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//h1[@class='content404__title']")
                    )
                )
                DRIVER.delete_all_cookies()
                return None
            except:
                logging.error(
                    f"WB: Ошибка при ожидании (content404__title) артикула {articul}"
                )
                DRIVER.delete_all_cookies()
                return None

        # ========== МАСКИРОВКА ===============
        await self.wb_masking(DRIVER)

        # ОБРАБОТКА ЦЕННИКА
        try:
            price_element = DRIVER.find_element(
                By.XPATH, ".//ins[@class='price-block__final-price']"
            )
            new_price = price_element.get_attribute("textContent")
            new_price = "".join(char for char in new_price if char.isdigit())
            DRIVER.delete_all_cookies()
            return int(new_price)
        except:
            sold_out_element = DRIVER.find_element(
                By.XPATH, ".//p[@class='sold-out-product']"
            )
            DRIVER.delete_all_cookies()
            return False

    # ====================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ АСИНХРОННОГО ОЖИДАНИЯ ЭЛЕМЕНТОВ СТРАНИЦЫ ===========================
    async def wait_fing_element(self, driver, timeout, locator):
        """Асинхронное ожидание элемента"""
        await asyncio.sleep(0)  # Allow other tasks to run
        element = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(locator)
            ),
        )
        return element

    async def download_image(self, url):
        """Асинхронная загрузка картинки"""
        async with aiohttp.ClientSession() as session:
            retry_count = 3
            for i in range(retry_count):
                try:
                    async with session.get(url) as response:
                        image_data = await response.read()
                        # Закрытие сенаса
                        await self.close_session(session=session)
                        return image_data
                except aiohttp.ClientOSError as e:
                    logging.error(
                        f"Ошибка подключения: {e}. Повторная попытка ({i + 1}/{retry_count})..."
                    )
                    await asyncio.sleep(1)  # Пауза перед повторной попыткой
                    continue
            else:
                logging.error(
                    f"Ошибка подключения: {e} --- {url} --- Превышено количество попыток."
                )
                await self.close_session(session=session)
                return b""

    async def close_session(self, session):
        if session:
            await session.close()

    async def get_options(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={UserAgent().random}")

        return options

    async def clear_driver(self, DRIVER):
        DRIVER.delete_all_cookies()
