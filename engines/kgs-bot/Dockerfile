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

# Adversary model: cyclic-adv-s545065216-d136760487.bin.gz
# From https://drive.google.com/drive/folders/1-bGX-NQOh6MuRPoXJgYHb9-jWRJvviSg
RUN mkdir /go_attack/adversary_models
# Downloading the file directly is working for now, but sometimes Google requires
# interaction to confirm a download. If this starts breaking, try using workaround at
# https://stackoverflow.com/a/50573452/14507224
RUN wget "https://docs.google.com/uc?export=download&id=1gwD0nQsuE7aD92YJ66l82qtXR97A_lt1" -O /go_attack/adversary_models/adversary_model.bin.gz

# Victim model
RUN mkdir /go_attack/victim_models
RUN wget https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz -O /go_attack/victim_models/victim_model.bin.gz

# Run this last so we can update configs and other settings without invalidating cache
COPY ./engines/kgs-bot/ /go_attack/engines/kgs-bot

WORKDIR /go_attack/engines/kgs-bot/
ENTRYPOINT ["/usr/bin/java", "-jar", "kgsGtp.jar", "config.txt"]
