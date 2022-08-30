mkdir victim-models
mkdir --parents training/emcts1-v2/cp127-vis512-warmstart-vis32
wget --directory-prefix=victim-models/ https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz
sudo usermod -aG docker $USER
sudo service docker start
