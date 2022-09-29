# To build, navigate to the *root* of this repo and run:
# docker build . -f compose/plots/Dockerfile -t humancompatibleai/goattack:plots
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install utilities
RUN apt-get update -q \
  && apt-get install -y \
  # latex
  texlive-latex-extra \
  texlive-fonts-recommended \
  dvipng \
  cm-super \
  # others
  curl \
  git \
  sudo \
  vim \
  uuid-runtime \
  wget \
  # Clean up
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Create virtualenv and 'activate' it by adjusting PATH.
# See https://pythonspeed.com/articles/activate-virtualenv-dockerfile/.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV --system-site-packages
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install pip requirements
RUN pip install --no-cache-dir --upgrade pip setuptools
COPY ./compose/plots/requirements.txt /downloads/requirements.txt
RUN pip install --no-cache-dir -r /downloads/requirements.txt
