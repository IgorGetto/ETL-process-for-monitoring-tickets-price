from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import json
from kafka import KafkaProducer
from clickhouse_driver import Client
from airflow.utils.log.logging_mixin import LoggingMixin
LoggingMixin().log.info("DAG configuration loaded")

default_args = {
    'owner': 'airflow',
    'retries': 3,
}

with open('/opt/airflow/dags/config.json') as f:
    config = json.load(f)

API_TOKEN = config['aviasales']['token']

def fetch_aviasales_data():
    params = {
        "origin": "OVB",  # Новосибирск
        "destination": "MOW", # Москва
        "depart_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m"),
        "currency": "rub",
        "token": API_TOKEN
    }

    response = requests.get(
        "https://api.travelpayouts.com/aviasales/v3/prices_for_dates",
        params=params
    )
    return response.json()["data"]


def send_to_kafka(ti):
    data = ti.xcom_pull(task_ids='fetch_data')
    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    for ticket in data:
        producer.send('aviasales_tickets', ticket)
    producer.flush()


def load_to_clickhouse(ti):
    ch_client = Client(
        host='clickhouse',
        user='default',
        password='',
        database='default'
    )

    ch_client.execute("""
    CREATE TABLE IF NOT EXISTS aviasales_tickets (
        departure_at DateTime64(3, 'Asia/Novosibirsk'),
        price Float32,
        airline String,
        flight_number String,
        route String,
        link String
    ) ENGINE = MergeTree()
    ORDER BY (departure_at, price)
    """)

    data = ti.xcom_pull(task_ids='fetch_data')
    for ticket in data:
        ch_client.execute(
            "INSERT INTO aviasales_tickets VALUES",
            [(
                datetime.fromisoformat(ticket['departure_at']),
                ticket['price'],
                ticket['airline'],
                ticket['flight_number'],
                f"{ticket['origin']}-{ticket['destination']}",
                f"https://www.aviasales.ru{ticket.get('link', '/')}"
            )]
        )




with DAG(
        'aviasales_pipeline',
        default_args=default_args,
        schedule_interval='@daily',
        start_date=datetime(2025, 1, 1)
) as dag:
    fetch_task = PythonOperator(
        task_id='fetch_data',
        python_callable=fetch_aviasales_data
    )

    kafka_task = PythonOperator(
        task_id='send_to_kafka',
        python_callable=send_to_kafka
    )

    clickhouse_task = PythonOperator(
        task_id='load_to_clickhouse',
        python_callable=load_to_clickhouse
    )

    fetch_task >> kafka_task >> clickhouse_task
