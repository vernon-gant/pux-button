import csv
import logging.config
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import List, Dict

import mysql
import mysql.connector
import pendulum as pendulum
import prestashop_orders_client.exceptions
from decouple import AutoConfig
from prestashop_orders_client import PrestaShopOrderClient
from prestashop_orders_client.exceptions import PrestaShopConnectionError
from prestashop_orders_client.utils import Order

from log_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger("pux-button")

config = AutoConfig(search_path="resources/.env")

OFFICE_EMAIL = config('OFFICE_EMAIL', default='')
OFFICE_PASSWORD = config('OFFICE_PASSWORD', default='')
PUX_EMAIL = config('PUX_EMAIL', default='')
SUBJECT = config('SUBJECT', default='')
LEVUS_INFO_EMAIL = config('LEVUS_INFO_EMAIL', default='')

PRESTA_API_KEY = config('PRESTA_API_KEY', default='')

DB_USER = config('DB_USER', default='')
DB_PASSWD = config('DB_PASSWD', default='')
DB_SCHEMA = config('DB_SCHEMA', default='')

PAID = ("Payment accepted", "On backorder (paid)", "Paid with Bitcoin", "Remote payment accepted")


def fetch_new_orders(orders_client: PrestaShopOrderClient) -> List or List[Order]:
    try:
        last_order = int(open("resources/last_order.txt").readline())
        if orders_client.orders_amount > last_order:
            new_orders = [orders_client.get_order(i) for i in range(last_order + 1, orders_client.orders_amount + 1)]
            logger.info(f'Found {len(new_orders)} new order(s): {new_orders}')
            update_last_order(orders_client.orders_amount)
            return list(filter(lambda order: three_box_order(order), new_orders))
        logger.info(f'No new orders found')
        return list()
    except PrestaShopConnectionError:
        logger.exception("Connection error! Check server status")
        return list()


def three_box_order(order: Order) -> bool:
    return order.total_paid > 1500


def update_last_order(last_order_value: int):
    with open("resources/last_order.txt", mode="w+") as last_order:
        last_order.write(str(last_order_value))
        logger.info(f"Updated last order to {last_order_value}")


def group_orders(new_orders_list: List[Order]) -> Dict[Order, List[tuple]]:
    logger.info("Started grouping new order(s)")
    orders_to_send = list(filter(lambda order: order.order_state in PAID, new_orders_list))
    pending_orders = list(
        filter(lambda order: order.order_state not in [*PAID, "Canceled", "Shipped"], new_orders_list))
    if pending_orders:
        with open("resources/pending_orders.csv", "a+", encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=get_orders_fields())
            writer.writerows([order._asdict() for order in pending_orders])
            logger.info(f"Added {pending_orders} to pending_orders.csv")
    return orders_with_weights(orders_to_send)


def orders_with_weights(orders: List[Order]) -> Dict[Order, List[tuple]]:
    # Connect to MySQL database
    conn = mysql.connector.connect(
        host="localhost",
        user=DB_USER,
        password=DB_PASSWD,
        database=DB_SCHEMA
    )

    # Prepare the query
    query = """
            SELECT subquery.reference, SUBSTRING_INDEX(lvscategory_lang.name, '-', 1) as box, SUM(subquery.total_weight) as total_weight
            FROM lvscategory_lang
            JOIN (
                SELECT lvsorders.reference, lvscategory_lang.id_category, lvsproduct.weight * SUM(lvspack.quantity) as total_weight
                FROM lvsorders 
                JOIN lvsorder_detail USING(id_order) 
                JOIN lvspack on lvsorder_detail.product_id = lvspack.id_product_pack 
                JOIN lvsproduct_lang on lvspack.id_product_item = lvsproduct_lang.id_product 
                JOIN lvsproduct on lvspack.id_product_item = lvsproduct.id_product 
                JOIN lvscategory_product on lvspack.id_product_item = lvscategory_product.id_product 
                JOIN lvscategory_lang on lvscategory_product.id_category = lvscategory_lang.id_category
                WHERE lvsorders.reference = %s 
                AND lvsproduct_lang.id_lang = 1 
                AND lvscategory_lang.id_category in (14,16,17) 
                AND lvscategory_lang.id_lang = 1
                GROUP BY lvspack.id_product_item
            ) as subquery ON lvscategory_lang.id_category = subquery.id_category
            WHERE lvscategory_lang.id_category in (14,16,17) AND lvscategory_lang.id_lang = 1
            GROUP BY box
        """

    # Create a cursor
    cursor = conn.cursor()

    # Execute a query for each order,fetch its weight and add it order and weight to a dictionary
    results = {}
    for order in orders:
        cursor.execute(query, (order.reference,))
        results.__setitem__(order, cursor.fetchall())

    return results


def compute_email(orders_to_send: Dict[Order, List[tuple]]) -> str:
    if orders_to_send:
        logger.info(f"Found new paid orders {orders_to_send} -> start computing email")
        email_text = "Hallo Herr Pux / Herr Böhm,\n\nBitte um um günstige Optionen für folgende(n)" \
                     " Kunden:\n\n\t#Standard 3 Set(s):\n\n"
        for order, boxes_weights in orders_to_send.items():
            company_name = "-------" if order.company_name is None else order.company_name
            state = "" if order.state is None else order.state
            phone = "No phone number entered" if order.phone is None else order.phone
            order_data = f'{order.email}\n{order.first_name + " " + order.last_name}\n{company_name}\n' \
                         f'{order.address}\n{order.city + " " + order.post_code + " " + state}\n' \
                         f'{order.country}\n{phone}\n\n' \
                         f'{format_boxes_weights(boxes_weights)}\n' \
                         f'{"-" * 21}\n\n'
            email_text += order_data
        email_text += f'Buchen Sie bitte die Abholung für Freitag {pendulum.now().next(pendulum.FRIDAY).strftime("%d.%m")} von 13:00-15:00.' \
                      f' Danke Vielmals!\n\nMit freundlichen Grüßen,\n\nAleksandr Zakharov'
        logger.info(f"Email computed")
        return email_text
    return ""


def format_boxes_weights(boxes_weights: List[tuple]) -> str:
    weights_as_string = ""
    for box in boxes_weights:
        weights_as_string += f'{box[0]} - {box[1]} - {round(box[2], 3)} kg.\n'
    return weights_as_string


def send_email(message: str):
    if message:
        try:
            logger.info("Sending an email...")
            em = EmailMessage()
            em['From'], em['To'], em['CC'], em['Subject'] = OFFICE_EMAIL, PUX_EMAIL, LEVUS_INFO_EMAIL, SUBJECT
            em.set_content(message)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
                smtp.login(OFFICE_EMAIL, OFFICE_PASSWORD)
                smtp.sendmail(OFFICE_EMAIL, [PUX_EMAIL, LEVUS_INFO_EMAIL], em.as_string())
            logger.info("Email was successfully sent!")
        except smtplib.SMTPException:
            logger.exception("Failed to send the email")
    else:
        logger.info("Found 0 paid orders -> email not sent,")


def check_pending_updates(orders_client: PrestaShopOrderClient) -> List or List[Order]:
    logger.info("Started checking pending orders")
    if os.path.exists("resources/pending_orders.csv"):
        updated, remaining = proceed_pending_orders(orders_client)
        if updated:
            logger.info(f"Found updated order(s) {updated} and saved them in orders_to_send.csv")
            if len(remaining) == 0:
                os.remove("resources/pending_orders.csv")
                logger.info("Deleted pending_orders.csv")
            else:
                with open('resources/pending_orders.csv', "w+", encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=get_orders_fields())
                    writer.writerows(remaining)
                    logger.info(f"Rewrote old pending orders {remaining} to pending_orders.csv")
        return updated
    else:
        logger.info("No updated pending orders found")
        return list()


def proceed_pending_orders(orders_client: PrestaShopOrderClient) -> List or List[Order]:
    updated, remaining = [], []
    with open("resources/pending_orders.csv", "r", encoding='utf-8') as f:
        reader = csv.DictReader(f, fieldnames=get_orders_fields())
        for old_state_order in reader:
            try:
                new_state_order = orders_client.get_order(int(Order(**old_state_order).id))
            except prestashop_orders_client.exceptions.PrestaShopConnectionError:
                logger.exception("Authentication failed")
            if new_state_order.order_state in PAID:
                updated.append(new_state_order)
            else:
                remaining.append(old_state_order)
    return updated, remaining


def get_orders_fields() -> List[str]:
    return list(Order._fields)


if __name__ == '__main__':
    logger.info("New orders' checking lifecycle started")
    orders_client = PrestaShopOrderClient('shop.levus.co/LVS', PRESTA_API_KEY)
    new_orders = fetch_new_orders(orders_client)
    updated_pending = check_pending_updates(orders_client)
    if new_orders or updated_pending:
        orders_to_send = group_orders(new_orders + updated_pending)
        email = compute_email(orders_to_send)
        send_email(email)
    logger.info("New orders' checking lifecycle ended")
