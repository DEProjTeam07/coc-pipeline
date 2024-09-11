FROM apache/airflow:2.10.0

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libsasl2-dev \
        procps && \
    apt-get autoremove -yqq --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

RUN pip install \
    apache-airflow-providers-apache-kafka \
    confluent-kafka==2.5.3 
    
RUN pip uninstall -y argparse
