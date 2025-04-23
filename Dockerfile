FROM apache/airflow:2.6.3

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем DAGs и плагины
COPY dags/ /opt/airflow/dags/
COPY plugins/ /opt/airflow/plugins/

# Копируем конфигурационные файлы
COPY config/airflow.cfg /opt/airflow/airflow.cfg
