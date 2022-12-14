# To build, navigate to the *root* of this repo and first run:
# docker build . -f compose/cpp/Dockerfile -t humancompatibleai/goattack:cpp
# And then:
# docker build . -f compose/cpp-kgs/Dockerfile -t humancompatibleai/goattack:cpp-kgs

FROM humancompatibleai/goattack:cpp

# Install Java
RUN apt-get update -q \
  && apt-get install -y \
  openjdk-11-jre-headless \
    # Clean up
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Download and set up KGS bot client
RUN wget http://files.gokgs.com/javaBin/kgsGtp-3.5.23.zip
RUN unzip kgsGtp-3.5.23.zip
COPY ./engines/kgs-bot/ /go_attack/engines/kgs-bot
RUN mv ./kgsGtp-3.5.23/kgsGtp.jar /go_attack/engines/kgs-bot/kgsGtp.jar

# Adversary model: adv505h-s349284096-d87808728.bin.gz
# From https://drive.google.com/drive/folders/1-bGX-NQOh6MuRPoXJgYHb9-jWRJvviSg
RUN mkdir /go_attack/adversary_models
RUN wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate $URL -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1Qktfjfr6YwplF50T-LMXkFK_qG1UXeiy" -O /go_attack/adversary_models/adversary_model.bin.gz && rm -rf /tmp/cookies.txt

# Victim model
RUN mkdir /go_attack/victim_models
RUN wget https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz -O /go_attack/victim_models/victim_model.bin.gz
