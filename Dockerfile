FROM ubuntu:16.04

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get autoremove -y && \
    apt-get install -y python python-dev python-pip python-setuptools --no-install-recommends && \
    pip install wheel && \
    rm -rf /var/lib/apt/lists/*

ENV user=notify
ENV group=notify
ENV uid=1000
ENV gid=1000
ENV home=/opt/notify

RUN groupadd -r $group -g $gid && \
    useradd -u $uid -r -g $group -m -d $home -s /sbin/nologin $user && \
    chmod 755 $home

WORKDIR $home
COPY ./requirements.txt $home
RUN pip install -r requirements.txt

COPY ./logging.conf $home
COPY ./notify.py $home
RUN chown -R $user:$group .

USER $user
CMD ["python", "-u", "notify.py"]
