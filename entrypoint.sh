#!/bin/bash

# Установка прав доступа для директорий
chown -R airflow:airflow /opt/airflow

# Установка прав доступа для конфигурационных файлов
chown airflow:airflow /opt/airflow/airflow.cfg
chmod 777 /opt/airflow/airflow.cfg

# Запуск Airflow
exec "$@"
