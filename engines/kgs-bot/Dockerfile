# To build, navigate to the *root* of this repo and first run:
# docker build . -f compose/cpp/Dockerfile -t humancompatibleai/goattack:cpp
# And then:
# docker build . -f engines/kgs-bot/Dockerfile -t humancompatibleai/goattack:cpp-kgs

FROM humancompatibleai/goattack:cpp

# Install Java
RUN  apt-get update -q \
  && apt-get install -y openjdk-11-jre-headless \
  # Clean up \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Download and set up KGS bot client
RUN wget http://files.gokgs.com/javaBin/kgsGtp-3.5.23.zip \
 && mkdir -p /go_attack/engines/kgs-bot/ \
 && unzip -j kgsGtp-3.5.23.zip kgsGtp-3.5.23/kgsGtp.jar -d /go_attack/engines/kgs-bot/ \
 && rm kgsGtp-3.5.23.zip

RUN pip install gdown
RUN mkdir /go_attack/models

# ViT model: vitp2b16c384-s650025472-d167043571-fp16.pt
# Link: https://drive.google.com/file/d/1D_Ifj3hFICxF37Yuoblde1JizOn5OhG7/view?usp=sharing
# Download method from https://stackoverflow.com/a/50670037/1337463.
RUN gdown 1D_Ifj3hFICxF37Yuoblde1JizOn5OhG7
RUN mv vitp2b16c384-s650025472-d167043571-fp16.pt /go_attack/models/vit-model-fp16.pt
    
# Run this last so we can update configs and other settings without invalidating cache
COPY ./engines/kgs-bot/ /go_attack/engines/kgs-bot

WORKDIR /go_attack/engines/kgs-bot/
ENTRYPOINT ["/usr/bin/java", "-jar", "kgsGtp.jar", "config.txt"]
